# BoneQC — Judge Quickstart

## 1. Назначение

Этот документ описывает минимальный путь независимого запуска финального frozen C7.

Competition evaluator не требует полного web-продукта.

## 2. Требования

Необходимы:

```text
Linux x86_64
Docker
NVIDIA GPU
NVIDIA Container Toolkit
Python 3
```

GPU должен быть доступен из Docker container runtime.

## 3. Frozen runtime

Authoritative image:

```text
ghcr.io/xaltezzarx/boneqc-c7@
sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7
```

Использование digest исключает незаметную замену image под mutable tag.

## 4. Preflight

Из корня repository:

```bash
bash evaluator/judge_preflight.sh
```

Preflight проверяет окружение и доступность frozen runtime.

## 5. Поддерживаемый input

Evaluator принимает:

- отдельный DICOM file;
- directory;
- ZIP archive.

Одно исследование может содержать несколько изображений/серий.

## 6. Запуск

Directory:

```bash
python3 evaluator/boneqc_evaluator.py ./dicom OUTPUT_DIR
```

ZIP:

```bash
python3 evaluator/boneqc_evaluator.py INPUT.zip OUTPUT_DIR
```

Single file:

```bash
python3 evaluator/boneqc_evaluator.py image.dcm OUTPUT_DIR
```

## 7. Discover-only

Для проверки DICOM discovery без inference:

```bash
python3 evaluator/boneqc_evaluator.py INPUT --discover-only
```

## 8. Output files

Evaluator создаёт:

```text
boneqc-c7-results-v1.csv
boneqc-c7-results-v1.xlsx
boneqc-evaluator-manifest-v1.json
boneqc-evaluator-audit-v1.json
```

Frozen C7 также может создавать внутренний inference report/debug artifacts.

## 9. Обязательные поля

Строгий competition contract:

```text
path_to_study
study_uid
image_uid
anatomical_region
quality_class
violation_type
processing_status
time_of_processing
```

Extended output может дополнительно содержать:

```text
quality_prob
```

## 10. quality_class

```text
0 → PASS
1 → FAIL
```

`quality_class` формируется frozen C7 subtype decisions.

Не следует вычислять его заново по `quality_prob`.

## 11. processing_status

Успешная обработка:

```text
Success
```

Повреждённый DICOM-кандидат:

```text
Failure
```

Ошибка отдельного файла не должна приводить к его исчезновению из output.

## 12. Mixed batch semantics

Допустим batch, в котором одновременно есть:

```text
1 valid DICOM
1 corrupted DICOM candidate
ordinary non-DICOM files
```

Ожидаемое поведение:

```text
valid DICOM      → Success row
corrupted DICOM  → Failure row
non-DICOM        → ignored
```

Evaluator должен завершить batch и сформировать audit при сохранении полного набора DICOM-кандидатов в результате.

## 13. Source paths

Evaluator staging не должен подменять пользовательские source paths в финальном output.

После inference исходные relative paths восстанавливаются.

## 14. Network isolation

Frozen inference выполняется с:

```text
--network none
```

Runtime не загружает weights во время обработки и не использует external AI API.

## 15. Immutable model boundary

Во время judge run не меняются:

- weights;
- thresholds;
- model selection;
- output semantics;
- frozen model artifacts.

## 16. Hardware

Основной проверенный runtime:

```text
NVIDIA RTX 3080 10 GB
```

Compatibility replay также выполнялся на GTX 1060 6 GB.

H200:

- архитектура Hopper;
- `sm_90`;
- runtime содержит поддержку `sm_90`;
- физический benchmark на H200 командой не выполнялся.

## 17. Performance

Competition requirement — обработать исследование в установленный организатором лимит.

BoneQC сохраняет `time_of_processing`.

Фактическое время зависит от target GPU и должно измеряться на judge hardware.

## 18. Batch HTTP API

Standalone frozen submission runtime также содержит:

```text
GET  /health/live
GET  /health/ready
POST /v1/batch
```

HTTP API использует тот же frozen C7 runner и submission adapter.

## 19. Что считать корректным запуском

Корректный evaluator run должен обеспечить:

- input discovery;
- row completeness;
- required columns;
- non-empty processing status;
- восстановление source paths;
- CSV и XLSX;
- manifest;
- audit.

## 20. Clinical boundary

BoneQC выполняет технический QC DXA-исследований.

Результат evaluator не является диагнозом.

## 21. Полная воспроизводимость frozen C7

Для организатора, которому нужно проверить Release archive, внешний `.sha256`, внутренний `SHA256SUMS`, пересобрать standalone image или запустить `run.sh` / `api.sh`, подготовлена отдельная инструкция:

[FROZEN_C7_REPRODUCIBILITY.md](FROZEN_C7_REPRODUCIBILITY.md)

Для точного конкурсного inference предпочтителен immutable GHCR digest. Standalone archive используется как автономная frozen copy и rebuild evidence.
