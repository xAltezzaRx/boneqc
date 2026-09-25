import unittest

from app.dataset.snapshots import (
    SnapshotSplitError,
    assign_group_splits,
    manifest_fingerprint,
    validate_group_safety,
    validate_ratios,
)


def records():
    return [
        {
            "schema_version": "0.1",
            "sample_id": "s1",
            "group_id": "g1",
            "labels": [],
            "metadata": {},
            "modality": "DX",
            "dicom_path": "dicom/s1.dcm",
            "preview_path": None,
            "split": None,
        },
        {
            "schema_version": "0.1",
            "sample_id": "s2",
            "group_id": "g1",
            "labels": [],
            "metadata": {},
            "modality": "DX",
            "dicom_path": "dicom/s2.dcm",
            "preview_path": None,
            "split": None,
        },
        {
            "schema_version": "0.1",
            "sample_id": "s3",
            "group_id": "g2",
            "labels": [],
            "metadata": {},
            "modality": "DX",
            "dicom_path": "dicom/s3.dcm",
            "preview_path": None,
            "split": None,
        },
        {
            "schema_version": "0.1",
            "sample_id": "s4",
            "group_id": "g3",
            "labels": [],
            "metadata": {},
            "modality": "DX",
            "dicom_path": "dicom/s4.dcm",
            "preview_path": None,
            "split": None,
        },
        {
            "schema_version": "0.1",
            "sample_id": "s5",
            "group_id": "g4",
            "labels": [],
            "metadata": {},
            "modality": "DX",
            "dicom_path": "dicom/s5.dcm",
            "preview_path": None,
            "split": None,
        },
    ]


class DatasetSnapshotTests(
    unittest.TestCase
):
    def test_group_safe_split(self):
        result = assign_group_splits(
            records(),
            seed=2026,
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        )

        validate_group_safety(
            result
        )

        g1 = {
            item["split"]
            for item in result
            if item["group_id"]
            == "g1"
        }

        self.assertEqual(
            len(g1),
            1,
        )

    def test_split_is_deterministic(self):
        first = assign_group_splits(
            records(),
            seed=2026,
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        )

        second = assign_group_splits(
            list(reversed(records())),
            seed=2026,
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        )

        self.assertEqual(
            first,
            second,
        )

    def test_fingerprint_order_independent(
        self,
    ):
        data = assign_group_splits(
            records(),
            seed=2026,
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        )

        self.assertEqual(
            manifest_fingerprint(
                data
            ),
            manifest_fingerprint(
                list(reversed(data))
            ),
        )

    def test_invalid_ratios(self):
        with self.assertRaises(
            SnapshotSplitError
        ):
            validate_ratios(
                train_ratio=0.8,
                val_ratio=0.2,
                test_ratio=0.2,
            )

    def test_fingerprint_is_sha256(self):
        value = (
            manifest_fingerprint(
                []
            )
        )

        self.assertEqual(
            len(value),
            64,
        )


if __name__ == "__main__":
    unittest.main()
