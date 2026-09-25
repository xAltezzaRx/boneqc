#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
import zipfile


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

WRAPPER = (
    ROOT
    / "boneqc_evaluator.py"
)

IMAGE = (
    "ghcr.io/xaltezzarx/boneqc-c7@"
    "sha256:"
    "d67b6a3c695a0cd495e5fd7c31e4d5f"
    "2142d13452afec4e304e2f01c9fc045d7"
)


GENERATOR = r'''
from pathlib import Path
from io import BytesIO

import numpy as np
from pydicom.dataset import (
    FileDataset,
    FileMetaDataset,
)
from pydicom.uid import (
    ExplicitVRLittleEndian,
    SecondaryCaptureImageStorage,
    generate_uid,
)

root = Path("/fixtures")
(root / "nested").mkdir(
    parents=True,
    exist_ok=True,
)

def make(path, preamble):
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

    ds = FileDataset(
        None,
        {},
        file_meta=meta,
        preamble=(
            b"\0" * 128
            if preamble
            else None
        ),
    )

    ds.SOPClassUID = (
        SecondaryCaptureImageStorage
    )

    ds.SOPInstanceUID = (
        meta.MediaStorageSOPInstanceUID
    )

    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()

    ds.Modality = "DX"
    ds.Rows = 8
    ds.Columns = 8
    ds.SamplesPerPixel = 1

    ds.PhotometricInterpretation = (
        "MONOCHROME2"
    )

    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0

    pixels = np.zeros(
        (8, 8),
        dtype=np.uint16,
    )

    ds.PixelData = pixels.tobytes()

    ds.save_as(
        path,
        enforce_file_format=preamble,
    )

make(
    root / "normal.dcm",
    True,
)

make(
    root / "nested" / "odd.bin",
    False,
)

make(
    root / "nested" / "no_extension",
    False,
)

(root / "noise.txt").write_text(
    "this is not dicom",
    encoding="utf-8",
)
'''


def run_wrapper(path: Path):
    return subprocess.run(
        [
            sys.executable,
            str(WRAPPER),
            str(path),
            "--discover-only",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


class InputDiscoveryTests(
    unittest.TestCase
):
    def make_fixture(
        self,
        root: Path,
    ) -> None:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--network",
                "none",
                "-i",
                "-v",
                f"{root.resolve()}:/fixtures",
                "--entrypoint",
                "python",
                IMAGE,
                "-",
            ],
            input=GENERATOR,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr,
        )

    def assert_three_dicoms(
        self,
        output: str,
    ) -> None:
        self.assertIn(
            "[BoneQC] DICOM_COUNT=3",
            output,
        )

        self.assertIn(
            "DICOM=normal.dcm",
            output,
        )

        self.assertIn(
            "DICOM=nested/odd.bin",
            output,
        )

        self.assertIn(
            "DICOM=nested/no_extension",
            output,
        )

        self.assertNotIn(
            "DICOM=noise.txt",
            output,
        )

        self.assertIn(
            "R8.6_DICOM_DISCOVERY=PASS",
            output,
        )

    def test_directory_content_discovery(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            fixture = Path(td)

            self.make_fixture(
                fixture
            )

            result = run_wrapper(
                fixture
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=result.stderr,
            )

            self.assert_three_dicoms(
                result.stdout
            )

    def test_zip_content_discovery(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            fixture = base / "fixture"
            fixture.mkdir()

            self.make_fixture(
                fixture
            )

            archive = base / "study-batch.zip"

            with zipfile.ZipFile(
                archive,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as zf:
                for path in sorted(
                    fixture.rglob("*")
                ):
                    if path.is_file():
                        zf.write(
                            path,
                            path.relative_to(
                                fixture
                            ),
                        )

            result = run_wrapper(
                archive
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=result.stderr,
            )

            self.assert_three_dicoms(
                result.stdout
            )

    def test_zip_traversal_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            archive = (
                Path(td)
                / "unsafe.zip"
            )

            with zipfile.ZipFile(
                archive,
                "w",
            ) as zf:
                zf.writestr(
                    "../escape.dcm",
                    b"not relevant",
                )

            result = run_wrapper(
                archive
            )

            self.assertNotEqual(
                result.returncode,
                0,
            )

            self.assertIn(
                "Unsafe ZIP path",
                result.stderr,
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
