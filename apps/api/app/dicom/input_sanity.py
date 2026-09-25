from __future__ import annotations

import math
import zlib

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import numpy as np
import pydicom


NOISE_ENTROPY_MIN = 7.5
NOISE_CORRELATION_ABS_MAX = 0.10
NOISE_MEAN_DIFF_MIN = 50.0
NOISE_ZLIB_RATIO_MIN = 0.90


@dataclass(
    frozen=True,
    slots=True,
)
class InputSanityResult:
    assessable: bool
    reason: str | None
    metrics: dict[str, Any]


def _safe_correlation(
    left: np.ndarray,
    right: np.ndarray,
) -> float:
    a = left.astype(
        np.float64,
        copy=False,
    ).ravel()

    b = right.astype(
        np.float64,
        copy=False,
    ).ravel()

    if (
        a.size < 2
        or b.size < 2
    ):
        return 0.0

    std_a = float(
        np.std(a)
    )

    std_b = float(
        np.std(b)
    )

    if (
        std_a <= 0.0
        or std_b <= 0.0
    ):
        return 0.0

    value = float(
        np.corrcoef(
            a,
            b,
        )[0, 1]
    )

    if not math.isfinite(
        value
    ):
        return 0.0

    return value


def _normalize_u8(
    pixels: np.ndarray,
) -> np.ndarray:
    array = np.asarray(
        pixels,
        dtype=np.float64,
    )

    finite = array[
        np.isfinite(array)
    ]

    if finite.size == 0:
        return np.zeros(
            array.shape,
            dtype=np.uint8,
        )

    low = float(
        np.percentile(
            finite,
            1.0,
        )
    )

    high = float(
        np.percentile(
            finite,
            99.0,
        )
    )

    if high <= low:
        return np.zeros(
            array.shape,
            dtype=np.uint8,
        )

    normalized = (
        np.clip(
            (array - low)
            / (high - low),
            0.0,
            1.0,
        )
        * 255.0
    )

    return normalized.astype(
        np.uint8
    )


def _entropy_u8(
    image: np.ndarray,
) -> float:
    histogram = np.bincount(
        image.ravel(),
        minlength=256,
    ).astype(
        np.float64
    )

    total = float(
        histogram.sum()
    )

    if total <= 0.0:
        return 0.0

    probabilities = (
        histogram
        / total
    )

    probabilities = probabilities[
        probabilities > 0.0
    ]

    return float(
        -np.sum(
            probabilities
            * np.log2(
                probabilities
            )
        )
    )


def evaluate_pixels(
    pixels: np.ndarray,
) -> InputSanityResult:
    array = np.asarray(
        pixels
    )

    if array.ndim != 2:
        return InputSanityResult(
            assessable=False,
            reason=(
                "UNSUPPORTED_PIXEL_DIMENSIONS"
            ),
            metrics={
                "shape": list(
                    array.shape
                ),
            },
        )

    raw = array.astype(
        np.float64,
        copy=False,
    )

    finite = raw[
        np.isfinite(raw)
    ]

    if finite.size == 0:
        return InputSanityResult(
            assessable=False,
            reason=(
                "NO_FINITE_PIXELS"
            ),
            metrics={},
        )

    raw_min = float(
        finite.min()
    )

    raw_max = float(
        finite.max()
    )

    raw_range = (
        raw_max
        - raw_min
    )

    raw_std = float(
        finite.std()
    )

    normalized = _normalize_u8(
        raw
    )

    unique_values = int(
        np.unique(
            normalized
        ).size
    )

    entropy = _entropy_u8(
        normalized
    )

    corr_h = _safe_correlation(
        normalized[:, :-1],
        normalized[:, 1:],
    )

    corr_v = _safe_correlation(
        normalized[:-1, :],
        normalized[1:, :],
    )

    if normalized.shape[1] > 1:
        diff_h = float(
            np.mean(
                np.abs(
                    normalized[:, 1:]
                    .astype(np.int16)
                    - normalized[:, :-1]
                    .astype(np.int16)
                )
            )
        )
    else:
        diff_h = 0.0

    if normalized.shape[0] > 1:
        diff_v = float(
            np.mean(
                np.abs(
                    normalized[1:, :]
                    .astype(np.int16)
                    - normalized[:-1, :]
                    .astype(np.int16)
                )
            )
        )
    else:
        diff_v = 0.0

    normalized_bytes = (
        np.ascontiguousarray(
            normalized
        ).tobytes()
    )

    compressed = zlib.compress(
        normalized_bytes,
        level=9,
    )

    zlib_ratio = (
        len(compressed)
        / len(normalized_bytes)
        if normalized_bytes
        else 0.0
    )

    metrics = {
        "raw_min":
            raw_min,

        "raw_max":
            raw_max,

        "raw_range":
            raw_range,

        "raw_std":
            raw_std,

        "normalized_std":
            float(
                normalized.std()
            ),

        "unique_values":
            unique_values,

        "entropy":
            entropy,

        "correlation_horizontal":
            corr_h,

        "correlation_vertical":
            corr_v,

        "mean_diff_horizontal":
            diff_h,

        "mean_diff_vertical":
            diff_v,

        "zlib_ratio":
            zlib_ratio,
    }

    if (
        raw_range <= 0.0
        or unique_values <= 1
    ):
        return InputSanityResult(
            assessable=False,
            reason=(
                "DEGENERATE_UNIFORM_PIXELS"
            ),
            metrics=metrics,
        )

    random_noise = (
        entropy
        >= NOISE_ENTROPY_MIN
        and abs(corr_h)
        <= NOISE_CORRELATION_ABS_MAX
        and abs(corr_v)
        <= NOISE_CORRELATION_ABS_MAX
        and diff_h
        >= NOISE_MEAN_DIFF_MIN
        and diff_v
        >= NOISE_MEAN_DIFF_MIN
        and zlib_ratio
        >= NOISE_ZLIB_RATIO_MIN
    )

    if random_noise:
        return InputSanityResult(
            assessable=False,
            reason=(
                "SYNTHETIC_NOISE_PATTERN"
            ),
            metrics=metrics,
        )

    return InputSanityResult(
        assessable=True,
        reason=None,
        metrics=metrics,
    )


def evaluate_dicom_bytes(
    dicom_bytes: bytes,
) -> InputSanityResult:
    if not dicom_bytes:
        return InputSanityResult(
            assessable=False,
            reason="EMPTY_DICOM_PAYLOAD",
            metrics={},
        )

    try:
        dataset = pydicom.dcmread(
            BytesIO(
                dicom_bytes
            ),
            force=False,
        )

        pixels = np.asarray(
            dataset.pixel_array
        )

    except Exception as exc:
        return InputSanityResult(
            assessable=False,
            reason=(
                "PIXEL_DECODE_FAILED"
            ),
            metrics={
                "error_type":
                    type(exc).__name__,
            },
        )

    if (
        pixels.ndim == 3
        and pixels.shape[0] == 1
    ):
        pixels = pixels[0]

    return evaluate_pixels(
        pixels
    )
