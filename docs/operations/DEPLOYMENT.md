# Развёртывание BoneQC

## 1. Назначение

BoneQC состоит из:

1. продуктового web stack;
2. frozen C7 competition runtime.

Продуктовый deployment может изменяться независимо от зафиксированной конкурсной ML-модели.

## 2. Product stack

Основные компоненты:

```text
Next.js Web
FastAPI API
Processing Worker
PostgreSQL
Redis
Object Storage
Frozen C7 gateway/runtime
```

Для локальной разработки используется `compose.yaml`.

Конфигурация передаётся через environment variables / `.env`.

Реальные secrets не должны храниться в Git.

## Локальный product quickstart

Из корня репозитория:

```bash
cp .env.example .env
```

После заполнения обязательных локальных значений:

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

Основные product services:

```text
postgres
object-store
redis
api
worker
web
```

Логи:

```bash
docker compose logs -f api worker web
```

Остановка:

```bash
docker compose down
```

`compose.yaml` использует PostgreSQL 17, Redis 8-alpine и SeaweedFS 4.46. API/worker собираются из `apps/api`, web — из `apps/web`.

### Product source dependencies

Backend:

```text
Python >=3.12,<3.13
FastAPI >=0.115,<1.0
SQLAlchemy >=2.0,<3.0
asyncpg >=0.30,<1.0
pydicom >=3.0.2,<4.0
redis >=8.0,<9.0
```

Web:

```text
Next.js 16.3.3
React 19.3.0
TypeScript 5.9.x
```

Полные dependency declarations находятся в:

```text
apps/api/pyproject.toml
apps/ai-engine/pyproject.toml
apps/web/package.json
```

## Frozen submission package

Финальный runtime package содержит Unix/Linux entrypoints для самостоятельного конкурсного запуска:

```text
build.sh
run.sh
api.sh
Dockerfile.pinned
DEPENDENCIES.lock
SHA256SUMS
```

`build.sh` собирает runtime image, `run.sh` выполняет offline batch inference и submission adapter, а `api.sh` запускает локальный batch API.

Authoritative judge path также может использовать уже опубликованный immutable GHCR digest без пересборки.

## 3. Competition runtime

Authoritative image:

```text
ghcr.io/xaltezzarx/boneqc-c7@
sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7
```

Для оценки используется exact immutable digest.

## 4. Competition preflight

Из корня репозитория:

```bash
bash evaluator/judge_preflight.sh
```

Preflight проверяет:

- Linux/x86_64;
- Docker;
- NVIDIA GPU;
- доступность GPU из контейнера;
- evaluator CLI;
- immutable C7 image;
- запуск frozen runtime.

Подробно:

[../competition/JUDGE_QUICKSTART.md](../competition/JUDGE_QUICKSTART.md)

## 5. Запуск evaluator

```bash
python3 evaluator/boneqc_evaluator.py INPUT OUTPUT_DIR
```

Поддерживаются:

- отдельный DICOM-файл;
- directory;
- ZIP.

## 6. Offline inference

Во время ML inference контейнер запускается без сетевого доступа.

Runtime не должен:

- скачивать weights;
- обращаться к внешним AI API;
- менять model artifacts;
- менять thresholds.

## 7. Практические системные требования

Ниже приведены эксплуатационные ориентиры для текущего frozen C7, а не сертифицированные минимумы.

### Compatibility floor, проверенный командой

```text
Linux x86_64
Docker + NVIDIA Container Toolkit
NVIDIA GTX 1060 6 GB
```

GTX 1060 использовалась как compatibility/fallback runtime той же C7-модели.

### Основная проверенная среда

```text
CPU: Intel i5-10400F
RAM: 32 GB
GPU: NVIDIA RTX 3080 10 GB
OS: Linux/WSL2 host workflow
```

### Рекомендуемый ориентир для воспроизводимого локального запуска

```text
CPU: 6 cores or more
RAM: 32 GB
GPU VRAM: 10 GB or more
Free disk: 40 GB or more
```

### Нижний практический ориентир

```text
CPU: 4 cores
RAM: 16 GB
GPU VRAM: 6 GB
Free disk: 20 GB
```

Эти два последних блока являются deployment guidance, а не результатом отдельного formal minimum-hardware benchmark.

## 8. H200

Authoritative Linux amd64 runtime использует PyTorch 2.14.0 + CUDA 13.0 stack с поддержкой `sm_90`.

NVIDIA H200 относится к Hopper / `sm_90`, поэтому runtime архитектурно совместим с H200.

Физический benchmark на H200 командой не выполнялся.

## 9. Performance boundary

Конкурсный кейс требует укладываться в лимит обработки исследования.

BoneQC сохраняет `time_of_processing` для каждой строки результата.

Фактическую производительность необходимо проверять на целевом оборудовании организатора, особенно для H200.

## 10. Product startup order

Типовой порядок:

```text
PostgreSQL / Redis / Object Storage
        ↓
API
        ↓
Worker
        ↓
Web
```

ML runtime может быть развёрнут отдельно.

## 11. Health checks

Необходимо различать:

```text
liveness  → процесс работает
readiness → сервис готов обслуживать запросы
```

Competition batch API предоставляет:

```text
GET /health/live
GET /health/ready
```

## 12. Stateful data

Persistent storage требуется как минимум для:

- PostgreSQL;
- Object Storage;
- других stateful product components.

Competition evaluator сам по себе не требует product database.

## 13. Network boundary

Не следует публиковать напрямую в интернет:

- PostgreSQL;
- Redis;
- internal Object Storage;
- internal ML endpoints.

Публичный product deployment должен использовать HTTPS.

## 14. Secrets

К секретам относятся:

- database credentials;
- session secrets;
- gateway tokens;
- API credentials;
- private keys.

В публичном репозитории должны находиться только безопасные templates/examples.

## 15. Logging

Логи не должны намеренно содержать:

- персональные медицинские данные;
- access tokens;
- production secrets;
- исходные patient identifiers.

## 16. Update policy

Обновление Web/API не должно автоматически изменять frozen C7.

Новый ML release должен иметь отдельный version/digest и проходить отдельную проверку.

## 17. Rollback

Для product changes необходимо сохранять возможность rollback конфигурации и контейнеров.

Frozen C7 competition runtime привязан к immutable digest, что позволяет повторно запустить именно ту же ML-версию.

## 18. Backup boundary

Для stateful production deployment необходима отдельная backup/restore стратегия.

Backup медицинских данных требует тех же мер защиты, что и primary storage.

## 19. Deployment boundary

BoneQC — исследовательский и конкурсный прототип.

Production deployment в медицинской организации требует отдельной проверки инфраструктуры, security policy и regulatory requirements.

## 20. Проверка standalone frozen release

Пошаговая инструкция для организатора по:

- скачиванию `boneqc-c7-final-v1.tar.gz`;
- проверке внешнего `.sha256`;
- проверке внутреннего `SHA256SUMS`;
- распаковке;
- `build.sh`;
- `run.sh`;
- `api.sh`;
- сравнению archive identity с authoritative GHCR digest;

находится в:

[../competition/FROZEN_C7_REPRODUCIBILITY.md](../competition/FROZEN_C7_REPRODUCIBILITY.md)

Важно различать exact image reproducibility и source/archive rebuild: immutable GHCR digest является authoritative runtime identity, тогда как archive обеспечивает frozen code/weights/manifests и возможность независимой пересборки.
