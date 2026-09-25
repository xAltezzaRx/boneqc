from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.database.session import (
    AsyncSessionLocal,
)
from app.models.enums import (
    AnnotationConsensusStatus,
)
from app.models.study import Study
from app.models.study_annotation_consensus import (
    StudyAnnotationConsensus,
)
from app.storage.service import storage


SAFE_METADATA_KEYS = {
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


class DatasetExportError(RuntimeError):
    pass


def build_manifest_record(
    *,
    study: Study,
    consensus: StudyAnnotationConsensus,
) -> dict:
    if not study.privacy_group_id:
        raise DatasetExportError(
            "Study does not contain "
            "privacy_group_id: "
            f"{study.id}"
        )

    if (
        consensus.status
        != AnnotationConsensusStatus
        .APPROVED
    ):
        raise DatasetExportError(
            "Consensus is not approved: "
            f"{consensus.id}"
        )

    labels = []

    for item in consensus.labels:
        labels.append(
            {
                "code": item["code"],
                "assessable": item.get(
                    "assessable",
                    True,
                ),
                "class_label": item.get(
                    "class_label"
                ),
                "confidence": item.get(
                    "confidence"
                ),
                "source": "CONSENSUS",
                "annotator_id": (
                    "consensus:"
                    + str(consensus.id)
                ),
            }
        )

    metadata = {
        key: value
        for key, value
        in dict(
            study.dicom_metadata
            or {}
        ).items()
        if key in SAFE_METADATA_KEYS
    }

    modality = str(
        metadata.get(
            "modality"
        )
        or "UNKNOWN"
    )

    sample_id = str(
        study.id
    )

    return {
        "schema_version": (
            consensus.schema_version
        ),
        "sample_id": sample_id,
        "group_id": (
            study.privacy_group_id
        ),
        "dicom_path": (
            f"dicom/{sample_id}.dcm"
        ),
        "preview_path": (
            f"preview/{sample_id}.png"
            if study.preview_object_key
            else None
        ),
        "modality": modality,
        "labels": labels,
        "metadata": metadata,
        "split": None,
    }


async def load_export_pair(
    study_id: UUID,
) -> tuple[
    Study,
    StudyAnnotationConsensus,
]:
    async with AsyncSessionLocal() as session:
        study = await session.get(
            Study,
            study_id,
        )

        if study is None:
            raise DatasetExportError(
                "Study does not exist: "
                f"{study_id}"
            )

        rows = list(
            (
                await session.scalars(
                    select(
                        StudyAnnotationConsensus
                    )
                    .where(
                        StudyAnnotationConsensus
                        .study_id
                        == study_id,
                        StudyAnnotationConsensus
                        .status
                        == AnnotationConsensusStatus
                        .APPROVED,
                    )
                )
            ).all()
        )

        if not rows:
            raise DatasetExportError(
                "Study does not have "
                "an approved consensus: "
                f"{study_id}"
            )

        if len(rows) != 1:
            raise DatasetExportError(
                "Study has more than one "
                "approved consensus: "
                f"{study_id}"
            )

        return study, rows[0]


async def export_dataset(
    *,
    study_ids: list[UUID],
    output: Path,
) -> list[dict]:
    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    if any(output.iterdir()):
        raise DatasetExportError(
            "Output directory must be empty"
        )

    dicom_dir = (
        output / "dicom"
    )

    preview_dir = (
        output / "preview"
    )

    dicom_dir.mkdir()
    preview_dir.mkdir()

    records: list[dict] = []

    consensus_ids: list[
        str
    ] = []

    for study_id in study_ids:
        study, consensus = (
            await load_export_pair(
                study_id
            )
        )

        record = (
            build_manifest_record(
                study=study,
                consensus=consensus,
            )
        )

        dicom_bytes = (
            await asyncio.to_thread(
                storage.get_bytes,
                key=(
                    study
                    .source_object_key
                ),
            )
        )

        (
            output
            / record["dicom_path"]
        ).write_bytes(
            dicom_bytes
        )

        preview_path = (
            record["preview_path"]
        )

        if preview_path is not None:
            preview_bytes = (
                await asyncio.to_thread(
                    storage.get_bytes,
                    key=(
                        study
                        .preview_object_key
                    ),
                )
            )

            (
                output
                / preview_path
            ).write_bytes(
                preview_bytes
            )

        records.append(
            record
        )

        consensus_ids.append(
            str(consensus.id)
        )

    records.sort(
        key=lambda item: (
            item["sample_id"]
        )
    )

    manifest = (
        output / "manifest.jsonl"
    )

    with manifest.open(
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

    metadata = {
        "format":
            "boneqc-training-export",
        "format_version": "0.2",
        "clinical_use": False,
        "approval_required": True,
        "samples": len(records),
        "study_ids": [
            item["sample_id"]
            for item in records
        ],
        "consensus_ids": sorted(
            consensus_ids
        ),
        "exported_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
    }

    (
        output
        / "export.json"
    ).write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return records


def parse_args():
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--study-id",
        action="append",
        required=True,
    )

    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()

    study_ids = [
        UUID(value)
        for value in args.study_id
    ]

    records = (
        await export_dataset(
            study_ids=study_ids,
            output=Path(
                args.output
            ),
        )
    )

    print(
        "DATASET_EXPORT=PASS"
    )

    print(
        "SAMPLES=",
        len(records),
    )


def main() -> None:
    asyncio.run(
        async_main()
    )


if __name__ == "__main__":
    main()
