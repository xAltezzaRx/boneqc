#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from evaluator.boneqc_evaluator import (
    C7_REPORT_NAME,
    CSV_NAME,
    XLSX_NAME,
    EvaluatorError,
    validate_c7_exit_semantics,
)


class C7ExitSemanticsTests(
    unittest.TestCase
):
    def test_zero_exit_is_normal_success(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)

            result = validate_c7_exit_semantics(
                output,
                0,
            )

            self.assertEqual(
                result,
                "success",
            )

    def test_review_exit_with_failure_row_is_accepted(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)

            (
                output
                / CSV_NAME
            ).write_text(
                "placeholder\n",
                encoding="utf-8",
            )

            (
                output
                / XLSX_NAME
            ).write_bytes(
                b"placeholder"
            )

            (
                output
                / C7_REPORT_NAME
            ).write_text(
                json.dumps(
                    {
                        "failure_rows": 1,
                    }
                ),
                encoding="utf-8",
            )

            result = validate_c7_exit_semantics(
                output,
                2,
            )

            self.assertEqual(
                result,
                "mixed-batch-review",
            )

    def test_review_exit_without_failure_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)

            (
                output
                / CSV_NAME
            ).write_text(
                "placeholder\n",
                encoding="utf-8",
            )

            (
                output
                / XLSX_NAME
            ).write_bytes(
                b"placeholder"
            )

            (
                output
                / C7_REPORT_NAME
            ).write_text(
                json.dumps(
                    {
                        "failure_rows": 0,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                EvaluatorError
            ):
                validate_c7_exit_semantics(
                    output,
                    2,
                )

    def test_review_exit_missing_artifacts_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)

            with self.assertRaises(
                EvaluatorError
            ):
                validate_c7_exit_semantics(
                    output,
                    2,
                )

    def test_unexpected_nonzero_exit_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)

            with self.assertRaises(
                EvaluatorError
            ):
                validate_c7_exit_semantics(
                    output,
                    1,
                )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
