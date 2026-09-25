from __future__ import annotations

import re

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import pydicom
from pydicom.dataset import Dataset


@dataclass(
    frozen=True,
    slots=True,
)
class AnatomyGuardResult:
    supported: bool
    reason: str | None
    evidence: dict[str, Any]


# BoneQC competition scope:
#
# - lumbar spine
# - proximal femur / hip
#
# This is intentionally NOT an anatomy classifier.
#
# We reject only explicit, high-confidence metadata evidence
# of anatomy outside the supported scope.
#
# Missing / empty / ambiguous metadata must pass through to C7.

SUPPORTED_HINTS = (
    "LUMBAR",
    "L SPINE",
    "L-SPINE",
    "LSPINE",
    "HIP",
    "FEMUR",
    "FEMORAL",
    "PROXIMAL FEMUR",
)


EXPLICIT_UNSUPPORTED_HINTS = (
    # Head
    "SKULL",
    "CRANIUM",

    # Chest
    "CHEST",
    "THORAX",
    "RIB",

    # Upper extremity
    "HAND",
    "WRIST",
    "FOREARM",
    "ELBOW",
    "SHOULDER",
    "HUMERUS",

    # Lower extremity outside proximal femur
    "KNEE",
    "ANKLE",
    "FOOT",
    "CALCANEUS",
    "TIBIA",
    "FIBULA",

    # Unsupported spine regions
    "CERVICAL",
    "C SPINE",
    "C-SPINE",
    "THORACIC",
    "T SPINE",
    "T-SPINE",

    # DXA site outside competition scope
    "WHOLE BODY",
    "TOTAL BODY",

    # Russian values, if present in source metadata
    "ЧЕРЕП",
    "ГРУДНАЯ КЛЕТКА",
    "КИСТЬ",
    "ЗАПЯСТЬЕ",
    "ПРЕДПЛЕЧЬЕ",
    "ЛОКОТЬ",
    "ПЛЕЧО",
    "КОЛЕНО",
    "ГОЛЕНОСТОП",
    "СТОПА",
    "ШЕЙНЫЙ",
    "ГРУДНОЙ ОТДЕЛ",
    "ВСЕ ТЕЛО",
)


def _normalize(
    value: Any,
) -> str:
    if value is None:
        return ""

    text = str(
        value
    ).strip().upper()

    text = re.sub(
        r"[_/\\]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def _contains_hint(
    value: str,
    hints: tuple[str, ...],
) -> str | None:
    for hint in hints:
        normalized_hint = _normalize(
            hint
        )

        if normalized_hint in value:
            return hint

    return None


def _anatomic_region_values(
    dataset: Dataset,
) -> list[dict[str, str]]:
    sequence = getattr(
        dataset,
        "AnatomicRegionSequence",
        None,
    )

    if not sequence:
        return []

    result: list[
        dict[str, str]
    ] = []

    for item in sequence:
        result.append(
            {
                "code_value":
                    _normalize(
                        getattr(
                            item,
                            "CodeValue",
                            None,
                        )
                    ),

                "code_meaning":
                    _normalize(
                        getattr(
                            item,
                            "CodeMeaning",
                            None,
                        )
                    ),

                "coding_scheme":
                    _normalize(
                        getattr(
                            item,
                            "CodingSchemeDesignator",
                            None,
                        )
                    ),
            }
        )

    return result


def evaluate_dataset(
    dataset: Dataset,
) -> AnatomyGuardResult:
    body_part = _normalize(
        getattr(
            dataset,
            "BodyPartExamined",
            None,
        )
    )

    regions = (
        _anatomic_region_values(
            dataset
        )
    )

    evidence = {
        "body_part_examined":
            body_part or None,

        "anatomic_regions":
            regions,
    }


    candidates: list[
        tuple[str, str]
    ] = []

    if body_part:
        candidates.append(
            (
                "BodyPartExamined",
                body_part,
            )
        )

    for index, region in enumerate(
        regions
    ):
        meaning = (
            region.get(
                "code_meaning"
            )
            or ""
        )

        if meaning:
            candidates.append(
                (
                    (
                        "AnatomicRegionSequence"
                        f"[{index}].CodeMeaning"
                    ),
                    meaning,
                )
            )


    for source, value in candidates:
        unsupported_hint = (
            _contains_hint(
                value,
                EXPLICIT_UNSUPPORTED_HINTS,
            )
        )

        if unsupported_hint is None:
            continue

        # A specific unsupported anatomical marker wins over
        # generic terms such as "SPINE".
        return AnatomyGuardResult(
            supported=False,
            reason=(
                "EXPLICIT_UNSUPPORTED_ANATOMY"
            ),
            evidence={
                **evidence,

                "source":
                    source,

                "matched_value":
                    value,

                "matched_hint":
                    unsupported_hint,
            },
        )


    # Positive hints are recorded only for observability.
    # They are not required for acceptance.
    supported_matches = []

    for source, value in candidates:
        hint = _contains_hint(
            value,
            SUPPORTED_HINTS,
        )

        if hint is not None:
            supported_matches.append(
                {
                    "source":
                        source,

                    "value":
                        value,

                    "hint":
                        hint,
                }
            )


    return AnatomyGuardResult(
        supported=True,
        reason=None,
        evidence={
            **evidence,

            "supported_matches":
                supported_matches,

            "policy":
                (
                    "explicit-negative-only"
                ),
        },
    )


def evaluate_dicom_anatomy(
    dicom_bytes: bytes,
) -> AnatomyGuardResult:
    if not dicom_bytes:
        return AnatomyGuardResult(
            supported=True,
            reason=None,
            evidence={
                "policy":
                    "explicit-negative-only",

                "metadata_available":
                    False,
            },
        )

    try:
        dataset = pydicom.dcmread(
            BytesIO(
                dicom_bytes
            ),
            stop_before_pixels=True,
            force=False,
        )

    except Exception as exc:
        # Parsing failures are handled elsewhere by the
        # normal DICOM validation path.
        #
        # Anatomy guard must not transform technical failures
        # into CANNOT_ASSESS.
        return AnatomyGuardResult(
            supported=True,
            reason=None,
            evidence={
                "policy":
                    "explicit-negative-only",

                "metadata_available":
                    False,

                "read_error":
                    type(exc).__name__,
            },
        )

    return evaluate_dataset(
        dataset
    )
