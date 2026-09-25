import unittest

from pydantic import ValidationError

from app.schemas.annotation import (
    AnnotationCreateRequest,
    ClinicalLabel,
)


class AnnotationSchemaTests(
    unittest.TestCase
):
    def test_valid_assessable_label(self):
        label = ClinicalLabel(
            code="POSITIONING",
            assessable=True,
            class_label="ACCEPTABLE",
            confidence=0.95,
        )

        self.assertEqual(
            label.code,
            "POSITIONING",
        )

    def test_assessable_requires_label(self):
        with self.assertRaises(
            ValidationError
        ):
            ClinicalLabel(
                code="POSITIONING",
                assessable=True,
            )

    def test_unassessable_rejects_class(self):
        with self.assertRaises(
            ValidationError
        ):
            ClinicalLabel(
                code="POSITIONING",
                assessable=False,
                class_label="ACCEPTABLE",
            )

    def test_confidence_range(self):
        with self.assertRaises(
            ValidationError
        ):
            ClinicalLabel(
                code="POSITIONING",
                class_label="ACCEPTABLE",
                confidence=1.5,
            )

    def test_requires_at_least_one_label(self):
        with self.assertRaises(
            ValidationError
        ):
            AnnotationCreateRequest(
                schema_version="0.1",
                labels=[],
            )

    def test_rejects_free_form_code(self):
        with self.assertRaises(
            ValidationError
        ):
            ClinicalLabel(
                code="patient did badly",
                class_label="ACCEPTABLE",
            )


if __name__ == "__main__":
    unittest.main()
