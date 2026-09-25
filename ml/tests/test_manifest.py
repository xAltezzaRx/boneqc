import unittest

from boneqc_ml.manifest import (
    ManifestValidationError,
    assign_splits,
    dataset_fingerprint,
    validate_manifest,
)


def record(
    sample: str,
    group: str,
) -> dict:
    return {
        "schema_version": "0.1",
        "sample_id": sample,
        "group_id": group,
        "dicom_path": (
            f"dicom/{sample}.dcm"
        ),
        "preview_path": (
            f"preview/{sample}.png"
        ),
        "modality": "DX",
        "labels": [
            {
                "code": "POSITIONING",
                "score": 0.8,
                "confidence": 1.0,
                "assessable": True,
                "source": "SYNTHETIC",
                "annotator_id": "test",
            }
        ],
        "metadata": {
            "modality": "DX",
            "rows": 256,
            "columns": 256,
        },
        "split": None,
    }


class ManifestTests(unittest.TestCase):
    def test_valid_manifest(self):
        records = [
            record("a", "g1"),
            record("b", "g2"),
        ]

        validate_manifest(records)

    def test_rejects_non_whitelisted_metadata(self):
        item = record(
            "a",
            "g1",
        )

        item["metadata"][
            "patient_name"
        ] = "SHOULD NEVER BE HERE"

        with self.assertRaises(
            ManifestValidationError
        ):
            validate_manifest([item])

    def test_group_safe_split(self):
        records = [
            record("a1", "g1"),
            record("a2", "g1"),
            record("b", "g2"),
            record("c", "g3"),
            record("d", "g4"),
            record("e", "g5"),
            record("f", "g6"),
        ]

        output = assign_splits(
            records,
            train_ratio=0.5,
            val_ratio=0.25,
            test_ratio=0.25,
            seed=2026,
        )

        assignments = {}

        for item in output:
            group = item["group_id"]
            split = item["split"]

            if group in assignments:
                self.assertEqual(
                    assignments[group],
                    split,
                )

            assignments[group] = split

        self.assertEqual(
            assignments["g1"],
            next(
                item["split"]
                for item in output
                if item["sample_id"]
                == "a2"
            ),
        )

    def test_detects_existing_group_leakage(self):
        first = record(
            "a",
            "same-group",
        )

        second = record(
            "b",
            "same-group",
        )

        first["split"] = "train"
        second["split"] = "test"

        with self.assertRaises(
            ManifestValidationError
        ):
            validate_manifest(
                [first, second]
            )

    def test_fingerprint_is_order_independent(self):
        first = record(
            "a",
            "g1",
        )

        second = record(
            "b",
            "g2",
        )

        self.assertEqual(
            dataset_fingerprint(
                [first, second]
            ),
            dataset_fingerprint(
                [second, first]
            ),
        )


if __name__ == "__main__":
    unittest.main()
