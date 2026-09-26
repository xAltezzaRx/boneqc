# BoneQC competition evaluator

`boneqc_evaluator.py` — wrapper вокруг immutable frozen C7.

## Быстрый запуск

```bash
bash evaluator/judge_preflight.sh
python3 evaluator/boneqc_evaluator.py INPUT OUTPUT_DIR
```

Поддерживаются:

```text
single DICOM
directory
ZIP
```

## Discover-only

```bash
python3 evaluator/boneqc_evaluator.py INPUT --discover-only
```

## Output

```text
boneqc-c7-results-v1.csv
boneqc-c7-results-v1.xlsx
boneqc-evaluator-manifest-v1.json
boneqc-evaluator-audit-v1.json
```

## Error semantics

Повреждённый DICOM-кандидат сохраняется как отдельная row с:

```text
processing_status = Failure
```

Обычные non-DICOM файлы в batch игнорируются.

Mixed Success/Failure batch считается валидным завершённым batch, если C7 создал полный output и failure rows отражены в результате.

## Frozen image

```text
ghcr.io/xaltezzarx/boneqc-c7@
sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7
```

Inference запускается без network access.

Полная инструкция:

[../docs/competition/JUDGE_QUICKSTART.md](../docs/competition/JUDGE_QUICKSTART.md)
