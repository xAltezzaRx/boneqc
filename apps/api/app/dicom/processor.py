from dataclasses import dataclass
from io import BytesIO
from typing import Any

import numpy as np
import pydicom
from PIL import Image
from pydicom.errors import InvalidDicomError

from app.dicom.deidentifier import DicomDeidentifier


class DicomProcessingError(Exception):
    pass


class InvalidDicomFileError(DicomProcessingError):
    pass


class MissingPixelDataError(DicomProcessingError):
    pass


class PixelDecodeError(DicomProcessingError):
    pass


class UnsafePixelDataError(DicomProcessingError):
    pass


@dataclass(slots=True)
class DicomProcessingResult:
    metadata: dict[str, Any]
    preview_png: bytes
    deidentified_dicom: bytes
    deidentification: dict[str, Any]
    rows: int
    columns: int


class DicomProcessor:
    def process(self, data: bytes) -> DicomProcessingResult:
        if not data:
            raise InvalidDicomFileError("DICOM file is empty")

        dataset = self._read_dataset(data)

        pixel_privacy = (
            self._validate_pixel_privacy(
                dataset
            )
        )

        preview_png = self._create_preview(dataset)

        deidentifier = DicomDeidentifier()
        deidentified = deidentifier.deidentify(
            dataset
        )

        metadata = self._extract_metadata(
            dataset
        )

        return DicomProcessingResult(
            metadata=metadata,
            preview_png=preview_png,
            deidentified_dicom=deidentified.data,
            deidentification={
                "profile": "BoneQC privacy baseline 0.1",
                "patient_identity_removed": True,
                "private_tags_removed": True,
                "uids_remapped": deidentified.uid_count,
                "cleared_attributes": (
                    deidentified.cleared_attribute_count
                ),
                "removed_private_tags": (
                    deidentified.removed_private_tag_count
                ),
                "pixel_privacy": (
                    pixel_privacy
                ),
            },
            rows=int(dataset.Rows),
            columns=int(dataset.Columns),
        )

    @staticmethod
    def _read_dataset(data: bytes) -> pydicom.Dataset:
        try:
            dataset = pydicom.dcmread(
                BytesIO(data),
                force=False,
            )
        except InvalidDicomError as exc:
            raise InvalidDicomFileError(
                "File is not a valid DICOM Part 10 file"
            ) from exc
        except Exception as exc:
            raise InvalidDicomFileError(
                "Unable to parse DICOM file"
            ) from exc

        required = (
            "Rows",
            "Columns",
            "PhotometricInterpretation",
        )

        missing = [
            field
            for field in required
            if not hasattr(dataset, field)
        ]

        if missing:
            raise InvalidDicomFileError(
                f"Missing required image attributes: {', '.join(missing)}"
            )

        if "PixelData" not in dataset:
            raise MissingPixelDataError(
                "DICOM object does not contain PixelData"
            )

        return dataset

    @staticmethod
    def _validate_pixel_privacy(
        dataset: pydicom.Dataset,
    ) -> str:
        burned_in = str(
            getattr(
                dataset,
                "BurnedInAnnotation",
                "",
            )
            or ""
        ).strip().upper()

        recognizable = str(
            getattr(
                dataset,
                "RecognizableVisualFeatures",
                "",
            )
            or ""
        ).strip().upper()

        patient_identity_removed = str(
            getattr(
                dataset,
                "PatientIdentityRemoved",
                "",
            )
            or ""
        ).strip().upper()

        if burned_in == "YES":
            raise UnsafePixelDataError(
                "DICOM declares BurnedInAnnotation=YES"
            )

        if recognizable == "YES":
            raise UnsafePixelDataError(
                "DICOM declares recognizable visual features"
            )

        if burned_in == "NO":
            return "BurnedInAnnotation=NO"

        if (
            not burned_in
            and patient_identity_removed == "YES"
        ):
            return (
                "BurnedInAnnotation=MISSING; "
                "PatientIdentityRemoved=YES"
            )

        if burned_in:
            raise UnsafePixelDataError(
                "DICOM contains unsupported "
                "BurnedInAnnotation value: "
                f"{burned_in}"
            )

        raise UnsafePixelDataError(
            "DICOM does not declare "
            "BurnedInAnnotation and does not "
            "declare PatientIdentityRemoved=YES"
        )

    @staticmethod
    def _extract_metadata(dataset: pydicom.Dataset) -> dict[str, Any]:
        file_meta = getattr(dataset, "file_meta", None)

        transfer_syntax_uid = None
        if file_meta is not None:
            value = getattr(file_meta, "TransferSyntaxUID", None)
            if value is not None:
                transfer_syntax_uid = str(value)

        pixel_spacing = getattr(dataset, "PixelSpacing", None)
        if pixel_spacing is not None:
            try:
                pixel_spacing = [float(value) for value in pixel_spacing]
            except (TypeError, ValueError):
                pixel_spacing = [str(value) for value in pixel_spacing]

        def string_value(name: str) -> str | None:
            value = getattr(dataset, name, None)
            return str(value) if value is not None else None

        def int_value(name: str) -> int | None:
            value = getattr(dataset, name, None)
            return int(value) if value is not None else None

        return {
            "sop_class_uid": string_value("SOPClassUID"),
            "sop_instance_uid": string_value("SOPInstanceUID"),
            "study_instance_uid": string_value("StudyInstanceUID"),
            "series_instance_uid": string_value("SeriesInstanceUID"),
            "modality": string_value("Modality"),
            "manufacturer": string_value("Manufacturer"),
            "manufacturer_model_name": string_value(
                "ManufacturerModelName"
            ),
            "rows": int_value("Rows"),
            "columns": int_value("Columns"),
            "bits_allocated": int_value("BitsAllocated"),
            "bits_stored": int_value("BitsStored"),
            "pixel_representation": int_value("PixelRepresentation"),
            "samples_per_pixel": int_value("SamplesPerPixel"),
            "photometric_interpretation": string_value(
                "PhotometricInterpretation"
            ),
            "pixel_spacing": pixel_spacing,
            "transfer_syntax_uid": transfer_syntax_uid,
        }

    @staticmethod
    def _create_preview(dataset: pydicom.Dataset) -> bytes:
        try:
            pixels = np.asarray(dataset.pixel_array)
        except Exception as exc:
            raise PixelDecodeError(
                "Unable to decode DICOM PixelData"
            ) from exc

        if pixels.size == 0:
            raise PixelDecodeError("Decoded PixelData is empty")

        # Multi-frame images: use the first frame for technical preview.
        if pixels.ndim >= 3 and pixels.shape[-1] not in (3, 4):
            pixels = pixels[0]

        # RGB/RGBA: keep RGB channels and normalize the array.
        if pixels.ndim == 3 and pixels.shape[-1] in (3, 4):
            pixels = pixels[..., :3]
            preview = DicomProcessor._normalize_color(pixels)
            image = Image.fromarray(preview, mode="RGB")
        else:
            pixels = np.squeeze(pixels)

            if pixels.ndim != 2:
                raise PixelDecodeError(
                    f"Unsupported pixel array shape: {pixels.shape}"
                )

            preview = DicomProcessor._normalize_grayscale(pixels)

            if (
                getattr(
                    dataset,
                    "PhotometricInterpretation",
                    None,
                )
                == "MONOCHROME1"
            ):
                preview = 255 - preview

            image = Image.fromarray(preview, mode="L")

        output = BytesIO()
        image.save(
            output,
            format="PNG",
            optimize=True,
        )

        return output.getvalue()

    @staticmethod
    def _normalize_grayscale(pixels: np.ndarray) -> np.ndarray:
        array = pixels.astype(np.float32, copy=False)

        finite = np.isfinite(array)
        if not finite.any():
            raise PixelDecodeError(
                "PixelData contains no finite values"
            )

        values = array[finite]

        low = float(np.percentile(values, 0.5))
        high = float(np.percentile(values, 99.5))

        if high <= low:
            low = float(values.min())
            high = float(values.max())

        if high <= low:
            return np.zeros(array.shape, dtype=np.uint8)

        array = np.nan_to_num(
            array,
            nan=low,
            posinf=high,
            neginf=low,
        )

        array = np.clip(array, low, high)
        array = (array - low) / (high - low)
        array = np.rint(array * 255.0)

        return array.astype(np.uint8)

    @staticmethod
    def _normalize_color(pixels: np.ndarray) -> np.ndarray:
        array = pixels.astype(np.float32, copy=False)

        finite = np.isfinite(array)
        if not finite.any():
            raise PixelDecodeError(
                "PixelData contains no finite values"
            )

        values = array[finite]
        low = float(values.min())
        high = float(values.max())

        if high <= low:
            return np.zeros(array.shape, dtype=np.uint8)

        array = np.nan_to_num(
            array,
            nan=low,
            posinf=high,
            neginf=low,
        )

        array = np.clip(array, low, high)
        array = (array - low) / (high - low)
        array = np.rint(array * 255.0)

        return array.astype(np.uint8)


dicom_processor = DicomProcessor()
