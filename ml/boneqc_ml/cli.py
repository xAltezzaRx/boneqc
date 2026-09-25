from __future__ import annotations

import argparse
import json

from boneqc_ml.manifest import (
    assign_splits,
    dataset_fingerprint,
    load_manifest,
    manifest_summary,
    write_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="boneqc-ml",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    validate = subparsers.add_parser(
        "validate",
    )
    validate.add_argument(
        "--manifest",
        required=True,
    )

    summary = subparsers.add_parser(
        "summary",
    )
    summary.add_argument(
        "--manifest",
        required=True,
    )

    fingerprint = subparsers.add_parser(
        "fingerprint",
    )
    fingerprint.add_argument(
        "--manifest",
        required=True,
    )

    split = subparsers.add_parser(
        "split",
    )
    split.add_argument(
        "--manifest",
        required=True,
    )
    split.add_argument(
        "--output",
        required=True,
    )
    split.add_argument(
        "--train",
        type=float,
        default=0.70,
    )
    split.add_argument(
        "--val",
        type=float,
        default=0.15,
    )
    split.add_argument(
        "--test",
        type=float,
        default=0.15,
    )
    split.add_argument(
        "--seed",
        type=int,
        default=2026,
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    records = load_manifest(
        args.manifest
    )

    if args.command == "validate":
        print(
            "VALID",
            len(records),
            dataset_fingerprint(records),
        )
        return

    if args.command == "summary":
        print(
            json.dumps(
                manifest_summary(records),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return

    if args.command == "fingerprint":
        print(
            dataset_fingerprint(records)
        )
        return

    if args.command == "split":
        output = assign_splits(
            records,
            train_ratio=args.train,
            val_ratio=args.val,
            test_ratio=args.test,
            seed=args.seed,
        )

        write_manifest(
            args.output,
            output,
        )

        print(
            json.dumps(
                manifest_summary(output),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return

    raise RuntimeError(
        "unreachable command"
    )


if __name__ == "__main__":
    main()
