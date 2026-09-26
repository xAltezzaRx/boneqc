# BoneQC C7 — воспроизводимость frozen runtime

## 1. Назначение

Этот документ предназначен для организатора или независимого проверяющего, которому нужно получить и запустить именно финальную frozen C7 без product web stack.

Есть два поддерживаемых пути:

1. **authoritative immutable image** — предпочтительный путь для точного запуска той же зафиксированной runtime-версии;
2. **frozen release archive** — автономный package с weights, caches, scripts, dependency evidence и SHA256 manifests для независимого хранения и пересборки.

Для конкурсной оценки рекомендуется использовать immutable image digest либо проверенный release archive.

---

## 2. Authoritative C7 identity

Финальная ML-версия:

```text
C7
```

Authoritative container:

```text
ghcr.io/xaltezzarx/boneqc-c7@
sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7
```

Model selection, weights, thresholds и output semantics frozen.

---

## 3. Public Release assets

Release:

```text
c7-final-v1
```

Страница Release:

```text
https://github.com/xAltezzaRx/boneqc/releases/tag/c7-final-v1
```

Для standalone frozen package используются два assets:

```text
boneqc-c7-final-v1.tar.gz
boneqc-c7-final-v1.tar.gz.sha256
```

Ожидаемый SHA256 архива:

```text
bf52b9b5170fe7a917b5d7a8e93e89cb5448d0c7883c1ae0d3454cf74d552a42
```

Ожидаемый размер архива:

```text
1453601555 bytes
```

Эти значения относятся именно к frozen historical C7 archive, который был повторно проверен перед публичной публикацией.

---

## 4. Вариант A — запуск authoritative GHCR image

Это предпочтительный способ, если задача — запустить ту же immutable runtime-версию без пересборки.

Проверить Docker/NVIDIA runtime:

```bash
docker version
nvidia-smi
docker run --rm --gpus all nvidia/cuda:13.0.0-base-ubuntu24.04 nvidia-smi
```

Получить image:

```bash
docker pull   ghcr.io/xaltezzarx/boneqc-c7@sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7
```

Проверить локальный RepoDigest:

```bash
docker image inspect   ghcr.io/xaltezzarx/boneqc-c7@sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7   --format '{{json .RepoDigests}}'
```

Для обычной конкурсной проверки удобнее использовать repository evaluator:

```bash
bash evaluator/judge_preflight.sh

python3 evaluator/boneqc_evaluator.py   INPUT   OUTPUT_DIR
```

Evaluator сам использует exact frozen image и запускает ML inference без сетевого доступа.

---

## 5. Вариант B — скачать standalone frozen archive

Скачать оба Release assets:

```bash
curl -fL -O   https://github.com/xAltezzaRx/boneqc/releases/download/c7-final-v1/boneqc-c7-final-v1.tar.gz

curl -fL -O   https://github.com/xAltezzaRx/boneqc/releases/download/c7-final-v1/boneqc-c7-final-v1.tar.gz.sha256
```

Перед распаковкой обязательно проверить внешний SHA256:

```bash
sha256sum -c   boneqc-c7-final-v1.tar.gz.sha256
```

Ожидаемый результат:

```text
boneqc-c7-final-v1.tar.gz: OK
```

Дополнительная проверка gzip:

```bash
gzip -t boneqc-c7-final-v1.tar.gz
```

---

## 6. Распаковка

```bash
tar -xzf boneqc-c7-final-v1.tar.gz
cd boneqc-c7-final-v1
```

Ключевые top-level files:

```text
README.md
FREEZE_STATUS.md
CONTAINER_BASE.txt
DEPENDENCIES.lock
Dockerfile.pinned
SHA256SUMS
THIRD_PARTY_MODELS.md
build.sh
run.sh
api.py
api.sh
submission_adapter.py
runtime/
evidence/
```

Все необходимые frozen model weights и локальные Hugging Face snapshots включены в package.

---

## 7. Внутренняя проверка package

До build/run рекомендуется проверить внутренний SHA manifest:

```bash
sha256sum -c SHA256SUMS
```

`SHA256SUMS` фиксирует control surface и frozen artifacts package, включая:

- dependency evidence;
- pinned Dockerfile;
- inference runner;
- model manifests;
- ключевые model weights;
- local pretrained snapshots.

Также полезно проверить freeze metadata:

```bash
cat FREEZE_STATUS.md
cat CONTAINER_BASE.txt
```

---

## 8. Сборка из archive

Скрипт:

```bash
./build.sh
```

По умолчанию создаётся image:

```text
boneqc-c7-final:runtime-v1
```

Можно задать своё локальное имя:

```bash
BONEQC_IMAGE=boneqc-c7-local:runtime-v1   ./build.sh
```

`build.sh` использует:

```text
Dockerfile.pinned
runtime/
```

и не изменяет model selection / weights / thresholds.

---

## 9. Важная оговорка о reproducibility

**Immutable GHCR digest** является наиболее сильной гарантией запуска той же container image.

Frozen archive обеспечивает:

- точную идентичность package по внешнему SHA256;
- внутренний SHA256 manifest;
- frozen weights;
- frozen code;
- pinned application dependencies;
- pinned Docker base image digest;
- локальные model caches.

При этом пересборка Docker image из archive не заявляется как гарантированно **bit-for-bit identical image rebuild** для любого будущего момента времени: часть OS packages устанавливается через package repositories, а полный `DEPENDENCIES.lock` является evidence/record среды, а не единственным install source Dockerfile.

Поэтому для конкурсного inference:

```text
exact runtime execution → prefer immutable GHCR digest
independent archival/rebuild evidence → use release archive + SHA256 manifests
```

---

## 10. Standalone CLI run

`run.sh` принимает два аргумента:

```text
<input_dicom_directory>
<output_directory>
```

Пример:

```bash
mkdir -p ./output

./run.sh   /path/to/dicom-directory   ./output
```

Frozen inference внутри `run.sh` запускается с:

```text
--gpus all
--network none
```

Input монтируется read-only.

После inference запускается output-only submission adapter.

---

## 11. Standalone outputs

Основные raw outputs:

```text
boneqc-c7-results-v1.csv
boneqc-c7-results-v1.xlsx
```

Extended outputs:

```text
boneqc-results-with-probability.csv
boneqc-results-with-probability.xlsx
```

Strict competition outputs:

```text
boneqc-results-required-8-columns.csv
boneqc-results-required-8-columns.xlsx
```

Strict contract:

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

Extended output дополнительно содержит `quality_prob`.

---

## 12. Standalone batch HTTP API

Запуск:

```bash
./api.sh start   /path/to/dicom-directory   /path/to/output   18080
```

Health:

```bash
curl   http://127.0.0.1:18080/health/live

curl   http://127.0.0.1:18080/health/ready
```

Запустить batch:

```bash
curl -X POST   -H 'Content-Type: application/json'   -d '{}'   http://127.0.0.1:18080/v1/batch
```

Посмотреть logs:

```bash
./api.sh logs
```

Остановить:

```bash
./api.sh stop
```

API использует тот же frozen C7 runner и submission adapter.

---

## 13. Какой путь использовать организатору

### Если нужно просто прогнать закрытый набор

Рекомендуется:

```text
public repository
→ judge_preflight.sh
→ boneqc_evaluator.py
→ immutable GHCR digest
```

Преимущества:

- exact image identity;
- DICOM file/directory/ZIP input;
- source-path restore;
- evaluator manifest/audit;
- mixed Success/Failure semantics.

### Если нужна полностью автономная копия frozen submission

Использовать:

```text
Release archive
→ outer .sha256 verification
→ extraction
→ internal SHA256SUMS verification
→ build.sh / run.sh
```

---

## 14. Минимальный acceptance checklist

Перед закрытым прогоном:

```text
[ ] archive SHA256 / image digest совпадает
[ ] NVIDIA GPU доступна Docker
[ ] frozen artifacts verification проходит
[ ] model weights локальны
[ ] inference выполняется без сети
[ ] input читается из отдельного directory
[ ] output directory writable
[ ] CSV/XLSX сформированы
[ ] обязательные 8 полей присутствуют
[ ] processing_status заполнен
```

---

## 15. Связанные документы

- [Judge Quickstart](JUDGE_QUICKSTART.md)
- [Deployment](../operations/DEPLOYMENT.md)
- [Solution Overview](../SOLUTION_OVERVIEW.md)
- [Model Card](../ml/MODEL_CARD.md)
- [Validation](../ml/VALIDATION.md)
