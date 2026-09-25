import unittest
from io import BytesIO

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import (
    ExplicitVRLittleEndian,
    SecondaryCaptureImageStorage,
    generate_uid,
)

from app.dicom.processor import (
    DicomProcessor,
    UnsafePixelDataError,
)


def build_dicom(
    *,
    burned_in_annotation: str | None = "NO",
    patient_identity_removed: str | None = None,
    recognizable_visual_features: str | None = None,
) -> tuple[bytes, dict[str, str], bytes]:
    sop_uid = generate_uid()
    study_uid = generate_uid()
    series_uid = generate_uid()
    referenced_uid = generate_uid()

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = (
        SecondaryCaptureImageStorage
    )
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = (
        ExplicitVRLittleEndian
    )
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.ImplementationVersionName = (
        "SOURCE_SYSTEM"
    )

    dataset = FileDataset(
        None,
        {},
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )

    dataset.SOPClassUID = (
        SecondaryCaptureImageStorage
    )
    dataset.SOPInstanceUID = sop_uid
    dataset.StudyInstanceUID = study_uid
    dataset.SeriesInstanceUID = series_uid

    dataset.Modality = "DX"
    dataset.Manufacturer = "BoneQC Test Scanner"
    dataset.ManufacturerModelName = "DXA Test"

    dataset.PatientName = "Sensitive^Patient"
    dataset.PatientID = "PATIENT-12345"
    dataset.PatientBirthDate = "19990101"
    dataset.PatientSex = "F"
    dataset.PatientAddress = "Secret Street 1"
    dataset.AccessionNumber = "ACC-SECRET"
    dataset.InstitutionName = "Secret Hospital"
    dataset.ReferringPhysicianName = "Doctor^Secret"
    dataset.StudyID = "STUDY-SECRET"
    dataset.StudyDate = "20260914"
    dataset.StudyTime = "120000"
    dataset.StudyDescription = (
        "Sensitive Patient DXA"
    )

    if burned_in_annotation is not None:
        dataset.BurnedInAnnotation = (
            burned_in_annotation
        )

    if patient_identity_removed is not None:
        dataset.PatientIdentityRemoved = (
            patient_identity_removed
        )

    if recognizable_visual_features is not None:
        dataset.RecognizableVisualFeatures = (
            recognizable_visual_features
        )

    nested = Dataset()
    nested.ReferringPhysicianName = (
        "Nested^Doctor"
    )
    nested.ReferencedSOPInstanceUID = (
        referenced_uid
    )

    dataset.RequestAttributesSequence = Sequence(
        [nested]
    )

    dataset.add_new(
        (0x0011, 0x0010),
        "LO",
        "PRIVATE_CREATOR",
    )
    dataset.add_new(
        (0x0011, 0x1010),
        "LO",
        "PRIVATE_SECRET_VALUE",
    )

    pixels = (
        np.arange(
            64 * 64,
            dtype=np.uint16,
        )
        % 4096
    ).reshape(64, 64)

    pixel_bytes = pixels.tobytes()

    dataset.Rows = 64
    dataset.Columns = 64
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = (
        "MONOCHROME2"
    )
    dataset.BitsAllocated = 16
    dataset.BitsStored = 12
    dataset.HighBit = 11
    dataset.PixelRepresentation = 0
    dataset.PixelData = pixel_bytes

    output = BytesIO()

    dataset.save_as(
        output,
        enforce_file_format=True,
    )

    return (
        output.getvalue(),
        {
            "sop_uid": sop_uid,
            "study_uid": study_uid,
            "series_uid": series_uid,
            "referenced_uid": referenced_uid,
        },
        pixel_bytes,
    )


class DicomDeidentificationTests(
    unittest.TestCase
):
    def test_deidentifies_before_storage(self):
        source, original, pixel_bytes = (
            build_dicom()
        )

        result = DicomProcessor().process(
            source
        )

        saved = pydicom.dcmread(
            BytesIO(
                result.deidentified_dicom
            )
        )

        self.assertEqual(
            str(saved.PatientName),
            "",
        )
        self.assertEqual(
            str(saved.PatientID),
            "",
        )
        self.assertEqual(
            str(saved.PatientBirthDate),
            "",
        )
        self.assertEqual(
            str(saved.PatientSex),
            "",
        )
        self.assertEqual(
            str(saved.AccessionNumber),
            "",
        )
        self.assertEqual(
            str(saved.InstitutionName),
            "",
        )
        self.assertEqual(
            str(saved.ReferringPhysicianName),
            "",
        )
        self.assertEqual(
            str(saved.StudyID),
            "",
        )

        self.assertEqual(
            str(saved.StudyDate),
            "",
        )
        self.assertEqual(
            str(saved.StudyTime),
            "",
        )

        self.assertEqual(
            saved.PatientIdentityRemoved,
            "YES",
        )

        self.assertIn(
            "BoneQC privacy baseline",
            str(saved.DeidentificationMethod),
        )

        self.assertNotIn(
            (0x0011, 0x0010),
            saved,
        )
        self.assertNotIn(
            (0x0011, 0x1010),
            saved,
        )

        self.assertNotEqual(
            str(saved.SOPInstanceUID),
            original["sop_uid"],
        )
        self.assertNotEqual(
            str(saved.StudyInstanceUID),
            original["study_uid"],
        )
        self.assertNotEqual(
            str(saved.SeriesInstanceUID),
            original["series_uid"],
        )

        self.assertEqual(
            str(
                saved.file_meta
                .MediaStorageSOPInstanceUID
            ),
            str(saved.SOPInstanceUID),
        )

        nested = (
            saved.RequestAttributesSequence[0]
        )

        self.assertEqual(
            str(
                nested.ReferringPhysicianName
            ),
            "",
        )

        self.assertNotEqual(
            str(
                nested.ReferencedSOPInstanceUID
            ),
            original["referenced_uid"],
        )

        self.assertEqual(
            saved.PixelData,
            pixel_bytes,
        )

        self.assertEqual(
            saved.Modality,
            "DX",
        )
        self.assertEqual(
            saved.Rows,
            64,
        )
        self.assertEqual(
            saved.Columns,
            64,
        )
        self.assertEqual(
            saved.Manufacturer,
            "BoneQC Test Scanner",
        )

        self.assertEqual(
            result.metadata["modality"],
            "DX",
        )

        self.assertNotEqual(
            result.metadata[
                "study_instance_uid"
            ],
            original["study_uid"],
        )

        self.assertGreater(
            len(result.preview_png),
            0,
        )

        self.assertTrue(
            result.deidentification[
                "patient_identity_removed"
            ]
        )

    def test_rejects_burned_in_annotation(self):
        source, _, _ = build_dicom(
            burned_in_annotation="YES"
        )

        with self.assertRaises(
            UnsafePixelDataError
        ):
            DicomProcessor().process(source)

    def test_accepts_missing_burned_in_marker_for_declared_deidentified_source(
        self,
    ):
        source, _, _ = build_dicom(
            burned_in_annotation=None,
            patient_identity_removed="YES",
        )

        result = DicomProcessor().process(
            source
        )

        self.assertEqual(
            result.deidentification[
                "pixel_privacy"
            ],
            (
                "BurnedInAnnotation=MISSING; "
                "PatientIdentityRemoved=YES"
            ),
        )

    def test_rejects_missing_pixel_privacy_marker_without_deidentification_declaration(
        self,
    ):
        source, _, _ = build_dicom(
            burned_in_annotation=None,
            patient_identity_removed=None,
        )

        with self.assertRaises(
            UnsafePixelDataError
        ):
            DicomProcessor().process(source)

    def test_rejects_recognizable_visual_features(
        self,
    ):
        source, _, _ = build_dicom(
            burned_in_annotation=None,
            patient_identity_removed="YES",
            recognizable_visual_features="YES",
        )

        with self.assertRaises(
            UnsafePixelDataError
        ):
            DicomProcessor().process(source)

    def test_rejects_unknown_burned_in_value(
        self,
    ):
        source, _, _ = build_dicom(
            burned_in_annotation="UNKNOWN",
            patient_identity_removed="YES",
        )

        with self.assertRaises(
            UnsafePixelDataError
        ):
            DicomProcessor().process(source)


if __name__ == "__main__":
    unittest.main()
