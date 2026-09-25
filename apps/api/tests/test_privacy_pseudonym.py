import unittest
from io import BytesIO

from pydicom.dataset import (
    FileDataset,
    FileMetaDataset,
)
from pydicom.uid import (
    ExplicitVRLittleEndian,
    SecondaryCaptureImageStorage,
    generate_uid,
)

from app.privacy.pseudonym import (
    derive_privacy_group_id,
)


def dicom_bytes(
    patient_id: str | None,
    issuer: str | None = None,
) -> bytes:
    meta = FileMetaDataset()

    meta.MediaStorageSOPClassUID = (
        SecondaryCaptureImageStorage
    )

    meta.MediaStorageSOPInstanceUID = (
        generate_uid()
    )

    meta.TransferSyntaxUID = (
        ExplicitVRLittleEndian
    )

    dataset = FileDataset(
        None,
        {},
        file_meta=meta,
        preamble=b"\0" * 128,
    )

    dataset.SOPClassUID = (
        SecondaryCaptureImageStorage
    )

    dataset.SOPInstanceUID = (
        meta.MediaStorageSOPInstanceUID
    )

    if patient_id is not None:
        dataset.PatientID = patient_id

    if issuer is not None:
        dataset.IssuerOfPatientID = (
            issuer
        )

    output = BytesIO()

    dataset.save_as(
        output,
        enforce_file_format=True,
    )

    return output.getvalue()


class PrivacyPseudonymTests(
    unittest.TestCase
):
    SECRET_A = "a" * 64
    SECRET_B = "b" * 64

    def test_same_patient_is_stable(self):
        first = derive_privacy_group_id(
            dicom_bytes(
                "PATIENT-42",
                "HOSPITAL-A",
            ),
            secret=self.SECRET_A,
        )

        second = derive_privacy_group_id(
            dicom_bytes(
                "PATIENT-42",
                "HOSPITAL-A",
            ),
            secret=self.SECRET_A,
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertTrue(
            first.startswith("pg1_")
        )

        self.assertNotIn(
            "PATIENT",
            first,
        )

    def test_different_secret_changes_id(self):
        data = dicom_bytes(
            "PATIENT-42"
        )

        self.assertNotEqual(
            derive_privacy_group_id(
                data,
                secret=self.SECRET_A,
            ),
            derive_privacy_group_id(
                data,
                secret=self.SECRET_B,
            ),
        )

    def test_issuer_is_part_of_identity(self):
        self.assertNotEqual(
            derive_privacy_group_id(
                dicom_bytes(
                    "42",
                    "A",
                ),
                secret=self.SECRET_A,
            ),
            derive_privacy_group_id(
                dicom_bytes(
                    "42",
                    "B",
                ),
                secret=self.SECRET_A,
            ),
        )

    def test_missing_patient_id_returns_none(self):
        self.assertIsNone(
            derive_privacy_group_id(
                dicom_bytes(None),
                secret=self.SECRET_A,
            )
        )


if __name__ == "__main__":
    unittest.main()
