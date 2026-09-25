import unittest

from app.model_registry.service import (
    ModelVersionMetadataConflictError,
    reconcile_model_metadata,
)
from app.models.enums import ModelVersionStatus
from app.models.model_version import ModelVersion


def model() -> ModelVersion:
    return ModelVersion(
        name="boneqc-test-model",
        version="1.0.0",
        task="quality_control",
        status=ModelVersionStatus.EXPERIMENTAL,
        git_commit=None,
        dataset_version=None,
        weights_hash=None,
        metrics={},
    )


class ModelTraceabilityTests(
    unittest.TestCase
):
    def test_populates_missing_provenance(self):
        item = model()

        changed = reconcile_model_metadata(
            item,
            task="quality_control",
            git_commit="abcdef123456",
            dataset_version="dataset-sha256",
            weights_hash=(
                "sha256:"
                + ("a" * 64)
            ),
            metrics={
                "synthetic_test_metric": 0.91,
            },
        )

        self.assertTrue(changed)

        self.assertEqual(
            item.git_commit,
            "abcdef123456",
        )

        self.assertEqual(
            item.dataset_version,
            "dataset-sha256",
        )

        self.assertEqual(
            item.weights_hash,
            "sha256:" + ("a" * 64),
        )

        self.assertEqual(
            item.metrics[
                "synthetic_test_metric"
            ],
            0.91,
        )

    def test_same_provenance_is_idempotent(self):
        item = model()

        item.dataset_version = "same"
        item.weights_hash = "sha256:same"
        item.metrics = {
            "accuracy": 0.9,
        }

        changed = reconcile_model_metadata(
            item,
            task="quality_control",
            dataset_version="same",
            weights_hash="sha256:same",
            metrics={
                "accuracy": 0.9,
            },
        )

        self.assertFalse(changed)

    def test_rejects_dataset_conflict(self):
        item = model()

        item.dataset_version = "dataset-a"

        with self.assertRaises(
            ModelVersionMetadataConflictError
        ):
            reconcile_model_metadata(
                item,
                task="quality_control",
                dataset_version="dataset-b",
            )

    def test_rejects_weights_conflict(self):
        item = model()

        item.weights_hash = "sha256:a"

        with self.assertRaises(
            ModelVersionMetadataConflictError
        ):
            reconcile_model_metadata(
                item,
                task="quality_control",
                weights_hash="sha256:b",
            )

    def test_rejects_task_conflict(self):
        item = model()

        with self.assertRaises(
            ModelVersionMetadataConflictError
        ):
            reconcile_model_metadata(
                item,
                task="diagnosis",
            )

    def test_rejects_metric_conflict(self):
        item = model()

        item.metrics = {
            "accuracy": 0.8,
        }

        with self.assertRaises(
            ModelVersionMetadataConflictError
        ):
            reconcile_model_metadata(
                item,
                task="quality_control",
                metrics={
                    "accuracy": 0.9,
                },
            )


if __name__ == "__main__":
    unittest.main()
