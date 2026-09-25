from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy


class SnapshotSplitError(
    ValueError
):
    pass


def validate_ratios(
    *,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> None:
    values = (
        train_ratio,
        val_ratio,
        test_ratio,
    )

    if any(
        value < 0.0
        or value > 1.0
        for value in values
    ):
        raise SnapshotSplitError(
            "Split ratios must be "
            "between 0 and 1"
        )

    if not math.isclose(
        sum(values),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise SnapshotSplitError(
            "Split ratios must sum "
            "to 1.0"
        )


def _group_counts(
    *,
    groups: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> dict[str, int]:
    if groups < 0:
        raise SnapshotSplitError(
            "Group count cannot "
            "be negative"
        )

    ratios = {
        "train": train_ratio,
        "val": val_ratio,
        "test": test_ratio,
    }

    raw = {
        name: groups * ratio
        for name, ratio
        in ratios.items()
    }

    counts = {
        name: math.floor(value)
        for name, value
        in raw.items()
    }

    remainder = (
        groups
        - sum(counts.values())
    )

    order = sorted(
        raw,
        key=lambda name: (
            -(raw[name] - counts[name]),
            (
                "train",
                "val",
                "test",
            ).index(name),
        ),
    )

    for name in order[:remainder]:
        counts[name] += 1

    return counts


def assign_group_splits(
    records: list[dict],
    *,
    seed: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> list[dict]:
    validate_ratios(
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
    )

    groups = {
        str(record["group_id"])
        for record in records
    }

    ranked = sorted(
        groups,
        key=lambda group_id: hashlib.sha256(
            (
                f"{seed}"
                "\x1f"
                f"{group_id}"
            ).encode("utf-8")
        ).hexdigest(),
    )

    counts = _group_counts(
        groups=len(ranked),
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
    )

    split_by_group: dict[
        str,
        str,
    ] = {}

    position = 0

    for split in (
        "train",
        "val",
        "test",
    ):
        count = counts[split]

        for group_id in ranked[
            position:
            position + count
        ]:
            split_by_group[
                group_id
            ] = split

        position += count

    output: list[dict] = []

    for record in records:
        copy = deepcopy(record)

        copy["split"] = (
            split_by_group[
                str(
                    copy["group_id"]
                )
            ]
        )

        output.append(copy)

    output.sort(
        key=lambda item: str(
            item["sample_id"]
        )
    )

    return output


def manifest_fingerprint(
    records: list[dict],
) -> str:
    canonical = sorted(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for record in records
    )

    payload = (
        "\n".join(canonical)
        + "\n"
    ).encode("utf-8")

    return hashlib.sha256(
        payload
    ).hexdigest()


def split_counts(
    records: list[dict],
) -> dict[str, int]:
    counts = {
        "train": 0,
        "val": 0,
        "test": 0,
    }

    for record in records:
        split = record["split"]

        if split not in counts:
            raise SnapshotSplitError(
                "Invalid split in "
                f"record: {split!r}"
            )

        counts[split] += 1

    return counts


def validate_group_safety(
    records: list[dict],
) -> None:
    group_splits: dict[
        str,
        set[str],
    ] = {}

    for record in records:
        group_id = str(
            record["group_id"]
        )

        split = str(
            record["split"]
        )

        group_splits.setdefault(
            group_id,
            set(),
        ).add(split)

    leaking = {
        group_id: splits
        for group_id, splits
        in group_splits.items()
        if len(splits) > 1
    }

    if leaking:
        raise SnapshotSplitError(
            "Patient/group leakage "
            "detected across splits"
        )
