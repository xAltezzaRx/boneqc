from __future__ import annotations

import copy
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import PurePosixPath
from typing import Any


SCHEMA_VERSION = "0.1"

VALID_SPLITS = {
    None,
    "train",
    "val",
    "test",
}

VALID_LABEL_SOURCES = {
    "CLINICIAN",
    "CONSENSUS",
    "SYNTHETIC",
    "IMPORT",
}

ALLOWED_RECORD_KEYS = {
    "schema_version",
    "sample_id",
    "group_id",
    "dicom_path",
    "preview_path",
    "modality",
    "labels",
    "metadata",
    "split",
}

ALLOWED_METADATA_KEYS = {
    "modality",
    "manufacturer",
    "manufacturer_model_name",
    "rows",
    "columns",
    "bits_allocated",
    "bits_stored",
    "pixel_representation",
    "samples_per_pixel",
    "photometric_interpretation",
    "pixel_spacing",
    "transfer_syntax_uid",
}


class ManifestValidationError(ValueError):
    pass


def _error(
    line_number: int,
    message: str,
) -> ManifestValidationError:
    return ManifestValidationError(
        f"line {line_number}: {message}"
    )


def _require_nonempty_string(
    value: Any,
    *,
    field: str,
    line_number: int,
) -> str:
    if not isinstance(value, str):
        raise _error(
            line_number,
            f"{field} must be a string",
        )

    value = value.strip()

    if not value:
        raise _error(
            line_number,
            f"{field} must not be empty",
        )

    return value


def _validate_relative_path(
    value: Any,
    *,
    field: str,
    line_number: int,
) -> str:
    text = _require_nonempty_string(
        value,
        field=field,
        line_number=line_number,
    )

    path = PurePosixPath(text)

    if path.is_absolute():
        raise _error(
            line_number,
            f"{field} must be relative",
        )

    if ".." in path.parts:
        raise _error(
            line_number,
            f"{field} must not escape dataset root",
        )

    return text


def _validate_probability(
    value: Any,
    *,
    field: str,
    line_number: int,
) -> None:
    if value is None:
        return

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise _error(
            line_number,
            f"{field} must be numeric",
        )

    if not 0.0 <= float(value) <= 1.0:
        raise _error(
            line_number,
            f"{field} must be in [0, 1]",
        )


def _validate_label(
    label: Any,
    *,
    line_number: int,
) -> None:
    if not isinstance(label, dict):
        raise _error(
            line_number,
            "each label must be an object",
        )

    allowed = {
        "code",
        "class_label",
        "score",
        "confidence",
        "assessable",
        "source",
        "annotator_id",
    }

    unknown = set(label) - allowed

    if unknown:
        raise _error(
            line_number,
            "unknown label fields: "
            + ", ".join(sorted(unknown)),
        )

    _require_nonempty_string(
        label.get("code"),
        field="label.code",
        line_number=line_number,
    )

    source = _require_nonempty_string(
        label.get("source"),
        field="label.source",
        line_number=line_number,
    ).upper()

    if source not in VALID_LABEL_SOURCES:
        raise _error(
            line_number,
            f"unsupported label.source: {source}",
        )

    assessable = label.get(
        "assessable",
        True,
    )

    if not isinstance(assessable, bool):
        raise _error(
            line_number,
            "label.assessable must be boolean",
        )

    class_label = label.get(
        "class_label"
    )

    if (
        class_label is not None
        and (
            not isinstance(class_label, str)
            or not class_label.strip()
        )
    ):
        raise _error(
            line_number,
            "label.class_label must be "
            "a non-empty string",
        )

    _validate_probability(
        label.get("score"),
        field="label.score",
        line_number=line_number,
    )

    _validate_probability(
        label.get("confidence"),
        field="label.confidence",
        line_number=line_number,
    )

    if (
        assessable
        and class_label is None
        and label.get("score") is None
    ):
        raise _error(
            line_number,
            "assessable label must contain "
            "class_label or score",
        )

    annotator_id = label.get(
        "annotator_id"
    )

    if (
        annotator_id is not None
        and (
            not isinstance(annotator_id, str)
            or not annotator_id.strip()
        )
    ):
        raise _error(
            line_number,
            "label.annotator_id must be "
            "a non-empty pseudonymous string",
        )


def validate_record(
    record: Any,
    *,
    line_number: int,
) -> None:
    if not isinstance(record, dict):
        raise _error(
            line_number,
            "record must be an object",
        )

    unknown = set(record) - ALLOWED_RECORD_KEYS

    if unknown:
        raise _error(
            line_number,
            "unknown record fields: "
            + ", ".join(sorted(unknown)),
        )

    if record.get("schema_version") != SCHEMA_VERSION:
        raise _error(
            line_number,
            "unsupported schema_version",
        )

    _require_nonempty_string(
        record.get("sample_id"),
        field="sample_id",
        line_number=line_number,
    )

    _require_nonempty_string(
        record.get("group_id"),
        field="group_id",
        line_number=line_number,
    )

    _validate_relative_path(
        record.get("dicom_path"),
        field="dicom_path",
        line_number=line_number,
    )

    preview_path = record.get(
        "preview_path"
    )

    if preview_path is not None:
        _validate_relative_path(
            preview_path,
            field="preview_path",
            line_number=line_number,
        )

    _require_nonempty_string(
        record.get("modality"),
        field="modality",
        line_number=line_number,
    )

    split = record.get("split")

    if split not in VALID_SPLITS:
        raise _error(
            line_number,
            f"invalid split: {split}",
        )

    metadata = record.get(
        "metadata",
        {},
    )

    if not isinstance(metadata, dict):
        raise _error(
            line_number,
            "metadata must be an object",
        )

    unknown_metadata = (
        set(metadata)
        - ALLOWED_METADATA_KEYS
    )

    if unknown_metadata:
        raise _error(
            line_number,
            "metadata contains non-whitelisted fields: "
            + ", ".join(
                sorted(unknown_metadata)
            ),
        )

    labels = record.get(
        "labels",
        [],
    )

    if not isinstance(labels, list):
        raise _error(
            line_number,
            "labels must be a list",
        )

    for label in labels:
        _validate_label(
            label,
            line_number=line_number,
        )


def validate_manifest(
    records: list[dict[str, Any]],
) -> None:
    sample_ids: set[str] = set()
    group_splits: dict[str, set[str]] = {}

    for line_number, record in enumerate(
        records,
        start=1,
    ):
        validate_record(
            record,
            line_number=line_number,
        )

        sample_id = record["sample_id"]

        if sample_id in sample_ids:
            raise _error(
                line_number,
                f"duplicate sample_id: {sample_id}",
            )

        sample_ids.add(sample_id)

        split = record.get("split")

        if split is not None:
            group_id = record["group_id"]

            group_splits.setdefault(
                group_id,
                set(),
            ).add(split)

    leaking_groups = {
        group_id: splits
        for group_id, splits
        in group_splits.items()
        if len(splits) > 1
    }

    if leaking_groups:
        details = "; ".join(
            f"{group}={sorted(splits)}"
            for group, splits
            in sorted(
                leaking_groups.items()
            )
        )

        raise ManifestValidationError(
            "group leakage across splits: "
            + details
        )


def load_manifest(
    path: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with open(
        path,
        encoding="utf-8",
    ) as handle:
        for line_number, raw in enumerate(
            handle,
            start=1,
        ):
            raw = raw.strip()

            if not raw:
                continue

            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise _error(
                    line_number,
                    "invalid JSON",
                ) from exc

            records.append(record)

    validate_manifest(records)

    return records


def write_manifest(
    path: str,
    records: list[dict[str, Any]],
) -> None:
    validate_manifest(records)

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as handle:
        for record in records:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            handle.write("\n")


def dataset_fingerprint(
    records: list[dict[str, Any]],
) -> str:
    validate_manifest(records)

    canonical = sorted(
        records,
        key=lambda item: item["sample_id"],
    )

    payload = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        payload
    ).hexdigest()


def _split_counts(
    number_of_groups: int,
    ratios: tuple[
        float,
        float,
        float,
    ],
) -> list[int]:
    raw = [
        number_of_groups * ratio
        for ratio in ratios
    ]

    counts = [
        math.floor(value)
        for value in raw
    ]

    remaining = (
        number_of_groups
        - sum(counts)
    )

    order = sorted(
        range(len(raw)),
        key=lambda index: (
            raw[index] - counts[index],
            -index,
        ),
        reverse=True,
    )

    for index in order[:remaining]:
        counts[index] += 1

    return counts


def assign_splits(
    records: list[dict[str, Any]],
    *,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> list[dict[str, Any]]:
    validate_manifest(records)

    ratios = (
        train_ratio,
        val_ratio,
        test_ratio,
    )

    if any(
        ratio < 0.0
        for ratio in ratios
    ):
        raise ValueError(
            "split ratios must be non-negative"
        )

    if not math.isclose(
        sum(ratios),
        1.0,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "split ratios must sum to 1"
        )

    groups = sorted(
        {
            record["group_id"]
            for record in records
        }
    )

    generator = random.Random(seed)
    generator.shuffle(groups)

    counts = _split_counts(
        len(groups),
        ratios,
    )

    train_count, val_count, _ = counts

    assignments: dict[str, str] = {}

    for group in groups[:train_count]:
        assignments[group] = "train"

    start = train_count
    end = start + val_count

    for group in groups[start:end]:
        assignments[group] = "val"

    for group in groups[end:]:
        assignments[group] = "test"

    output = copy.deepcopy(records)

    for record in output:
        record["split"] = assignments[
            record["group_id"]
        ]

    validate_manifest(output)

    return output


def manifest_summary(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    validate_manifest(records)

    split_counts = Counter(
        record.get("split") or "unsplit"
        for record in records
    )

    modality_counts = Counter(
        record["modality"]
        for record in records
    )

    label_counts = Counter(
        label["code"]
        for record in records
        for label in record.get(
            "labels",
            [],
        )
    )

    groups = {
        record["group_id"]
        for record in records
    }

    return {
        "samples": len(records),
        "groups": len(groups),
        "splits": dict(
            sorted(
                split_counts.items()
            )
        ),
        "modalities": dict(
            sorted(
                modality_counts.items()
            )
        ),
        "labels": dict(
            sorted(
                label_counts.items()
            )
        ),
        "fingerprint": (
            dataset_fingerprint(records)
        ),
    }
