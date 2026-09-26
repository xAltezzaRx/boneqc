#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile


IMAGE = (
    "ghcr.io/xaltezzarx/boneqc-c7@"
    "sha256:"
    "d67b6a3c695a0cd495e5fd7c31e4d5f"
    "2142d13452afec4e304e2f01c9fc045d7"
)

DIGEST = (
    "sha256:"
    "d67b6a3c695a0cd495e5fd7c31e4d5f"
    "2142d13452afec4e304e2f01c9fc045d7"
)

CSV_NAME = "boneqc-c7-results-v1.csv"
XLSX_NAME = "boneqc-c7-results-v1.xlsx"

MANIFEST_NAME = "boneqc-evaluator-manifest-v1.json"
AUDIT_NAME = "boneqc-evaluator-audit-v1.json"

C7_REPORT_NAME = "c7-15c-inference-report-v1.json"

REQUIRED_COLUMNS = {
    "path_to_study",
    "study_uid",
    "image_uid",
    "anatomical_region",
    "quality_class",
    "violation_type",
    "processing_status",
    "time_of_processing",
}

MAX_ZIP_FILES = 10000
MAX_ZIP_UNCOMPRESSED = 8 * 1024 * 1024 * 1024


class EvaluatorError(RuntimeError):
    pass


def run(
    command: list[str],
    *,
    capture: bool = False,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        input=stdin,
        text=True,
        capture_output=capture,
        check=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True

    except ValueError:
        return False


def ensure_image() -> None:
    inspected = run(
        [
            "docker",
            "image",
            "inspect",
            IMAGE,
        ],
        capture=True,
    )

    if inspected.returncode != 0:
        print(
            "[BoneQC] immutable C7 image is not local; "
            "pulling exact digest..."
        )

        pulled = run(
            [
                "docker",
                "pull",
                IMAGE,
            ]
        )

        if pulled.returncode != 0:
            raise EvaluatorError(
                "Unable to obtain immutable C7 image"
            )

    digest_result = run(
        [
            "docker",
            "image",
            "inspect",
            IMAGE,
            "--format",
            "{{json .RepoDigests}}",
        ],
        capture=True,
    )

    if (
        digest_result.returncode != 0
        or DIGEST not in digest_result.stdout
    ):
        raise EvaluatorError(
            "C7 image immutable digest verification failed"
        )

    print(
        "[BoneQC] C7_IMAGE_DIGEST=PASS"
    )


def safe_extract_zip(
    archive: Path,
    destination: Path,
) -> None:
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_count = 0
    total_size = 0

    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            raw_name = info.filename.replace(
                "\\",
                "/",
            )

            path = PurePosixPath(raw_name)

            if (
                not raw_name
                or path.is_absolute()
                or ".." in path.parts
                or (
                    path.parts
                    and ":" in path.parts[0]
                )
            ):
                raise EvaluatorError(
                    "Unsafe ZIP path: "
                    + raw_name
                )

            mode = (
                info.external_attr >> 16
            ) & 0xFFFF

            if stat.S_ISLNK(mode):
                raise EvaluatorError(
                    "ZIP symbolic links are not permitted: "
                    + raw_name
                )

            if info.flag_bits & 0x1:
                raise EvaluatorError(
                    "Encrypted ZIP entries are not supported"
                )

            if info.is_dir():
                continue

            file_count += 1
            total_size += int(info.file_size)

            if file_count > MAX_ZIP_FILES:
                raise EvaluatorError(
                    "ZIP contains too many files"
                )

            if total_size > MAX_ZIP_UNCOMPRESSED:
                raise EvaluatorError(
                    "ZIP uncompressed size exceeds safety limit"
                )

            target = destination.joinpath(
                *path.parts
            )

            if not is_within(
                target,
                destination,
            ):
                raise EvaluatorError(
                    "ZIP extraction escaped destination"
                )

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with (
                zf.open(info, "r") as source,
                target.open("wb") as output,
            ):
                shutil.copyfileobj(
                    source,
                    output,
                )


def prepare_source(
    input_path: Path,
    work: Path,
) -> tuple[Path, str]:
    input_path = input_path.resolve()

    if not input_path.exists():
        raise EvaluatorError(
            f"Input not found: {input_path}"
        )

    if input_path.is_dir():
        return input_path, "directory"

    if not input_path.is_file():
        raise EvaluatorError(
            "Input must be a file, directory, or ZIP"
        )

    if zipfile.is_zipfile(input_path):
        extracted = work / "extracted"

        safe_extract_zip(
            input_path,
            extracted,
        )

        return extracted, "zip"

    single = work / "single"
    single.mkdir()

    target = single / input_path.name

    shutil.copyfile(
        input_path,
        target,
    )

    return single, "single-file"


def discover_dicoms(
    root: Path,
) -> list[str]:
    scanner = r'''
import json
from pathlib import Path

import pydicom

root = Path("/scan")

selected = []

keywords = [
    "SOPClassUID",
    "SOPInstanceUID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "Rows",
    "Columns",
    "Modality",
]

for path in sorted(
    p for p in root.rglob("*")
    if p.is_file()
):
    suffix_hint = (
        path.suffix.lower()
        in {
            ".dcm",
            ".dicom",
        }
    )

    preamble_hint = False

    try:
        with path.open("rb") as handle:
            header = handle.read(132)

        preamble_hint = (
            len(header) >= 132
            and header[128:132] == b"DICM"
        )

    except OSError:
        pass

    explicit_candidate = (
        suffix_hint
        or preamble_hint
    )

    try:
        ds = pydicom.dcmread(
            str(path),
            stop_before_pixels=True,
            force=True,
            specific_tags=keywords,
        )

        sop_class = str(
            getattr(
                ds,
                "SOPClassUID",
                "",
            )
        ).strip()

        sop_instance = str(
            getattr(
                ds,
                "SOPInstanceUID",
                "",
            )
        ).strip()

        study_uid = str(
            getattr(
                ds,
                "StudyInstanceUID",
                "",
            )
        ).strip()

        series_uid = str(
            getattr(
                ds,
                "SeriesInstanceUID",
                "",
            )
        ).strip()

        rows = int(
            getattr(ds, "Rows", 0)
            or 0
        )

        columns = int(
            getattr(ds, "Columns", 0)
            or 0
        )

        identity_signals = sum(
            bool(value)
            for value in (
                sop_instance,
                study_uid,
                series_uid,
            )
        )

        if (
            sop_class
            and rows > 0
            and columns > 0
            and identity_signals >= 1
        ):
            selected.append(
                path.relative_to(root).as_posix()
            )

        elif explicit_candidate:
            selected.append(
                path.relative_to(root).as_posix()
            )

    except Exception:
        if explicit_candidate:
            selected.append(
                path.relative_to(root).as_posix()
            )

print(
    json.dumps(
        selected,
        ensure_ascii=False,
    )
)
'''

    result = run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            f"{root.resolve()}:/scan:ro",
            "--entrypoint",
            "python",
            IMAGE,
            "-c",
            scanner,
        ],
        capture=True,
    )

    if result.returncode != 0:
        raise EvaluatorError(
            "DICOM discovery failed:\n"
            + result.stderr[-4000:]
        )

    lines = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    if not lines:
        raise EvaluatorError(
            "DICOM discovery returned no response"
        )

    try:
        paths = json.loads(lines[-1])

    except json.JSONDecodeError as exc:
        raise EvaluatorError(
            "Invalid DICOM discovery response"
        ) from exc

    if not isinstance(paths, list):
        raise EvaluatorError(
            "Invalid DICOM discovery result"
        )

    return sorted(
        str(path)
        for path in paths
    )


def stage_dicoms(
    root: Path,
    relative_paths: list[str],
    staging: Path,
) -> list[dict[str, str]]:
    staging.mkdir(
        parents=True,
        exist_ok=True,
    )

    records: list[dict[str, str]] = []

    for index, relative in enumerate(
        relative_paths,
        start=1,
    ):
        source_path = root / relative

        if source_path.is_symlink():
            raise EvaluatorError(
                "Input symbolic links are not permitted: "
                + relative
            )

        if not is_within(
            source_path,
            root,
        ):
            raise EvaluatorError(
                "Input path escaped source root: "
                + relative
            )

        if not source_path.is_file():
            raise EvaluatorError(
                "Discovered input disappeared: "
                + relative
            )

        digest = sha256_file(
            source_path
        )

        stage_name = (
            f"{index:06d}-"
            f"{digest[:12]}.dcm"
        )

        destination = (
            staging / stage_name
        )

        shutil.copyfile(
            source_path,
            destination,
        )

        records.append(
            {
                "source_path": relative,
                "stage_name": stage_name,
                "sha256": digest,
            }
        )

    return records


def write_manifest(
    path: Path,
    *,
    source_type: str,
    records: list[dict[str, str]],
) -> None:
    payload = {
        "schema_version":
            "boneqc-evaluator-manifest-v1",
        "c7_image": IMAGE,
        "c7_manifest_digest": DIGEST,
        "source_type": source_type,
        "dicom_count": len(records),
        "files": records,
    }

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def run_c7(
    staging: Path,
    output: Path,
) -> tuple[float, int]:
    started = time.perf_counter()

    result = run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--gpus",
            "all",
            "-v",
            f"{staging.resolve()}:/input:ro",
            "-v",
            f"{output.resolve()}:/output",
            IMAGE,
            "--input",
            "/input",
            "--output-dir",
            "/output",
        ]
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    return (
        elapsed,
        result.returncode,
    )


def validate_c7_exit_semantics(
    output: Path,
    returncode: int,
) -> str:
    if returncode == 0:
        return "success"

    if returncode != 2:
        raise EvaluatorError(
            "Frozen C7 inference failed "
            f"with exit code {returncode}"
        )

    csv_path = output / CSV_NAME
    xlsx_path = output / XLSX_NAME
    report_path = output / C7_REPORT_NAME

    missing = [
        path.name
        for path in (
            csv_path,
            xlsx_path,
            report_path,
        )
        if not path.is_file()
    ]

    if missing:
        raise EvaluatorError(
            "Frozen C7 REVIEW exit did not produce "
            "required artifacts: "
            + ", ".join(missing)
        )

    try:
        report = json.loads(
            report_path.read_text(
                encoding="utf-8"
            )
        )

    except Exception as exc:
        raise EvaluatorError(
            "Unable to read frozen C7 review report"
        ) from exc

    try:
        failure_rows = int(
            report.get(
                "failure_rows",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise EvaluatorError(
            "Invalid failure_rows in frozen C7 report"
        ) from exc

    if failure_rows <= 0:
        raise EvaluatorError(
            "Frozen C7 returned REVIEW without "
            "recorded per-file Failure rows"
        )

    return "mixed-batch-review"


def restore_source_paths(
    output: Path,
) -> None:
    script = r'''
import json
from pathlib import Path

import pandas as pd

root = Path("/output")

manifest = json.loads(
    (
        root
        / "boneqc-evaluator-manifest-v1.json"
    ).read_text(
        encoding="utf-8"
    )
)

mapping = {
    item["stage_name"]:
        item["source_path"]
    for item in manifest["files"]
}

csv_path = (
    root
    / "boneqc-c7-results-v1.csv"
)

xlsx_path = (
    root
    / "boneqc-c7-results-v1.xlsx"
)

frame = pd.read_csv(
    csv_path,
    dtype=str,
    keep_default_na=False,
)

if "path_to_study" not in frame.columns:
    raise RuntimeError(
        "Missing path_to_study"
    )

def restore(value):
    name = Path(str(value)).name
    return mapping.get(
        name,
        str(value),
    )

frame["path_to_study"] = (
    frame["path_to_study"]
    .map(restore)
)

frame.to_csv(
    csv_path,
    index=False,
)

frame.to_excel(
    xlsx_path,
    index=False,
)

print(
    "SOURCE_PATH_RESTORE=PASS"
)
'''

    result = run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            f"{output.resolve()}:/output",
            "--entrypoint",
            "python",
            IMAGE,
            "-c",
            script,
        ],
        capture=True,
    )

    if result.stdout:
        print(
            result.stdout,
            end="",
        )

    if result.returncode != 0:
        raise EvaluatorError(
            "Unable to restore source paths:\n"
            + result.stderr[-4000:]
        )


def audit_outputs(
    output: Path,
    records: list[dict[str, str]],
    elapsed: float,
) -> dict[str, object]:
    csv_path = output / CSV_NAME
    xlsx_path = output / XLSX_NAME

    if not csv_path.is_file():
        raise EvaluatorError(
            f"Missing output: {CSV_NAME}"
        )

    if not xlsx_path.is_file():
        raise EvaluatorError(
            f"Missing output: {XLSX_NAME}"
        )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        fields = set(
            reader.fieldnames or []
        )

        missing = (
            REQUIRED_COLUMNS
            - fields
        )

        if missing:
            raise EvaluatorError(
                "Missing required output columns: "
                + ", ".join(
                    sorted(missing)
                )
            )

        rows = list(reader)

    if len(rows) != len(records):
        raise EvaluatorError(
            "Output row count mismatch: "
            f"input={len(records)} "
            f"output={len(rows)}"
        )

    expected_paths = {
        item["source_path"]
        for item in records
    }

    output_paths = {
        row.get(
            "path_to_study",
            "",
        )
        for row in rows
    }

    if output_paths != expected_paths:
        raise EvaluatorError(
            "Output path completeness mismatch"
        )

    empty_status = [
        row.get(
            "path_to_study",
            "",
        )
        for row in rows
        if not row.get(
            "processing_status",
            "",
        ).strip()
    ]

    if empty_status:
        raise EvaluatorError(
            "Empty processing_status detected"
        )

    allowed_statuses = {
        "Success",
        "Failure",
    }

    invalid_statuses = sorted(
        {
            row.get(
                "processing_status",
                "",
            ).strip()
            for row in rows
        }
        - allowed_statuses
    )

    if invalid_statuses:
        raise EvaluatorError(
            "Unexpected processing_status values: "
            + ", ".join(invalid_statuses)
        )

    status_counts = {
        status: sum(
            1
            for row in rows
            if row.get(
                "processing_status",
                "",
            ).strip()
            == status
        )
        for status in sorted(
            allowed_statuses
        )
    }

    audit = {
        "schema_version":
            "boneqc-evaluator-audit-v1",
        "status": "PASS",
        "c7_image": IMAGE,
        "input_dicom_count":
            len(records),
        "output_row_count":
            len(rows),
        "path_completeness": True,
        "required_columns_present": True,
        "processing_status_complete": True,
        "processing_status_counts":
            status_counts,
        "csv": CSV_NAME,
        "xlsx": XLSX_NAME,
        "wall_seconds": round(
            elapsed,
            6,
        ),
    }

    (
        output
        / AUDIT_NAME
    ).write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "BoneQC LCT 2026 evaluator wrapper "
            "around immutable frozen C7"
        )
    )

    parser.add_argument(
        "input",
        type=Path,
        help=(
            "DICOM file, directory, "
            "or ZIP archive"
        ),
    )

    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help=(
            "Output directory "
            "(not required with --discover-only)"
        ),
    )

    parser.add_argument(
        "--discover-only",
        action="store_true",
        help=(
            "Discover DICOM files by content "
            "without running inference"
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacement of evaluator outputs",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        ensure_image()

        with tempfile.TemporaryDirectory(
            prefix="boneqc-evaluator-"
        ) as temp:
            work = Path(temp)

            root, source_type = (
                prepare_source(
                    args.input,
                    work,
                )
            )

            print(
                "[BoneQC] SOURCE_TYPE="
                + source_type
            )

            dicoms = discover_dicoms(
                root
            )

            # A directly supplied file is an explicit
            # evaluator input. Even if its DICOM
            # metadata is damaged beyond discovery,
            # stage it so frozen C7 can emit its
            # existing per-file Failure row.
            if (
                source_type == "single-file"
                and not dicoms
            ):
                single_files = sorted(
                    path
                    for path in root.iterdir()
                    if path.is_file()
                )

                if len(single_files) == 1:
                    dicoms = [
                        single_files[
                            0
                        ].relative_to(
                            root
                        ).as_posix()
                    ]

            print(
                "[BoneQC] DICOM_COUNT="
                + str(len(dicoms))
            )

            for path in dicoms:
                print(
                    "[BoneQC] DICOM="
                    + path
                )

            if not dicoms:
                raise EvaluatorError(
                    "No DICOM images discovered"
                )

            if args.discover_only:
                print(
                    "R8.6_DICOM_DISCOVERY=PASS"
                )
                return 0

            if args.output is None:
                raise EvaluatorError(
                    "Output directory is required"
                )

            output = args.output.resolve()

            input_resolved = (
                args.input.resolve()
            )

            if (
                input_resolved.is_dir()
                and is_within(
                    output,
                    input_resolved,
                )
            ):
                raise EvaluatorError(
                    "Output directory must not be "
                    "inside input directory"
                )

            output.mkdir(
                parents=True,
                exist_ok=True,
            )

            protected_outputs = [
                output / CSV_NAME,
                output / XLSX_NAME,
                output / MANIFEST_NAME,
                output / AUDIT_NAME,
            ]

            if (
                not args.force
                and any(
                    path.exists()
                    for path
                    in protected_outputs
                )
            ):
                raise EvaluatorError(
                    "Evaluator output already exists; "
                    "use --force to replace"
                )

            staging = (
                work / "staging"
            )

            records = stage_dicoms(
                root,
                dicoms,
                staging,
            )

            write_manifest(
                output / MANIFEST_NAME,
                source_type=source_type,
                records=records,
            )

            print(
                "[BoneQC] STAGED_COUNT="
                + str(len(records))
            )

            print(
                "[BoneQC] FROZEN_C7_MODIFIED=NO"
            )

            print(
                "[BoneQC] NETWORK_DURING_INFERENCE=NONE"
            )

            (
                elapsed,
                c7_returncode,
            ) = run_c7(
                staging,
                output,
            )

            c7_exit_semantics = (
                validate_c7_exit_semantics(
                    output,
                    c7_returncode,
                )
            )

            print(
                "[BoneQC] C7_RETURN_CODE="
                + str(c7_returncode)
            )

            print(
                "[BoneQC] C7_EXIT_SEMANTICS="
                + c7_exit_semantics
            )

            restore_source_paths(
                output
            )

            audit = audit_outputs(
                output,
                records,
                elapsed,
            )

            print(
                "[BoneQC] OUTPUT_ROWS="
                + str(
                    audit[
                        "output_row_count"
                    ]
                )
            )

            print(
                "[BoneQC] CSV="
                + str(
                    output
                    / CSV_NAME
                )
            )

            print(
                "[BoneQC] XLSX="
                + str(
                    output
                    / XLSX_NAME
                )
            )

            print(
                "[BoneQC] EVALUATOR_AUDIT=PASS"
            )

            print(
                "R8.6_EVALUATOR=PASS"
            )

            return 0

    except EvaluatorError as exc:
        print(
            "[BoneQC] ERROR="
            + str(exc),
            file=sys.stderr,
        )

        print(
            "R8.6_EVALUATOR=FAIL",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
