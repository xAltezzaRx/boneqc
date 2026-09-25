from __future__ import annotations

import hashlib
import hmac
from io import BytesIO

import pydicom
from pydicom.errors import InvalidDicomError


PSEUDONYM_VERSION = "pg1"


def derive_privacy_group_id(
    dicom_bytes: bytes,
    *,
    secret: str,
) -> str | None:
    if len(secret.encode("utf-8")) < 32:
        raise ValueError(
            "Pseudonym secret must contain "
            "at least 32 bytes"
        )

    try:
        dataset = pydicom.dcmread(
            BytesIO(dicom_bytes),
            stop_before_pixels=True,
            force=False,
        )
    except InvalidDicomError:
        # The normal DICOM processor will return
        # the proper input validation error later.
        return None

    patient_id = str(
        getattr(
            dataset,
            "PatientID",
            "",
        )
        or ""
    ).strip()

    if not patient_id:
        return None

    issuer = str(
        getattr(
            dataset,
            "IssuerOfPatientID",
            "",
        )
        or ""
    ).strip()

    message = (
        "boneqc-patient-link-v1"
        + "\x1f"
        + issuer
        + "\x1f"
        + patient_id
    ).encode("utf-8")

    digest = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()

    return (
        f"{PSEUDONYM_VERSION}_{digest}"
    )
