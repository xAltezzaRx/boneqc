# Развёртывание BoneQC

## Назначение

BoneQC состоит из продуктового контура и отдельного frozen C7 inference runtime.

Продуктовый deployment может изменяться независимо от зафиксированной конкурсной модели.

## Основные компоненты

Продуктовый контур включает:

- Next.js Web;
- FastAPI API;
- Processing Worker;
- PostgreSQL;
- Redis;
- Object Storage;
- ML gateway к frozen C7 runtime.

## Локальный запуск

Для разработки используется `compose.yaml`.

Конкретные настройки среды передаются через `.env`.

Реальные production secrets не должны храниться в Git.

## Stateful-компоненты

Persistent storage требуется как минимум для:

- PostgreSQL;
- Object Storage;
- других компонентов, которым необходимо сохранять состояние между перезапусками.

## API и Worker

API принимает пользовательские запросы и создаёт задания анализа.

Worker выполняет длительную обработку отдельно от HTTP request lifecycle.

Общий поток:

~~~text
API
 ↓
AnalysisJob
 ↓
Worker
 ↓
Frozen C7 Runtime
 ↓
AnalysisResult
~~~

## Frozen C7 Runtime

Конкурсный runtime зафиксирован отдельно от продуктового deployment.

Authoritative image:

~~~text
ghcr.io/xaltezzarx/boneqc-c7@
sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7
~~~

Использование immutable digest позволяет проверять идентичность запускаемого образа.

## Проверка конкурсной среды

Из корня репозитория:

~~~bash
bash evaluator/judge_preflight.sh
~~~

Подробная инструкция:

[../competition/JUDGE_QUICKSTART.md](../competition/JUDGE_QUICKSTART.md)

## Основной inference-контур

Основной C7 runtime рассчитан на NVIDIA GPU и CUDA.

Для конкурсной проверки evaluator запускает frozen runtime независимо от продуктового web/API-контура.

## Compatibility / fallback runtime

В проекте проверялся дополнительный runtime для GTX 1060.

Это не отдельная модель.

Для compatibility runtime сохраняются:

- те же веса;
- те же thresholds;
- та же логика `quality_class`;
- те же output semantics.

Различия CUDA/PyTorch stack допустимы только при сохранении семантической эквивалентности результата.

## Health checks

Инфраструктурные сервисы должны предоставлять health/readiness проверки.

Различаются:

- liveness — процесс работает;
- readiness — сервис готов обслуживать запросы и необходимые зависимости доступны.

## Порядок запуска

Типовой порядок:

~~~text
PostgreSQL / Redis / Object Storage
        ↓
API
        ↓
Worker
        ↓
Web
~~~

ML runtime может быть развёрнут отдельно.

## HTTPS

Публичный deployment должен использовать HTTPS.

Session/cookie configuration должна соответствовать HTTPS-режиму.

## Network boundary

Во внешний контур должны публиковаться только необходимые сервисы.

Не следует напрямую публиковать в интернет:

- PostgreSQL;
- Redis;
- внутренний Object Storage endpoint;
- внутренние ML endpoints.

## Firewall

Правила firewall должны разрешать только необходимые входящие соединения.

Внутренние инфраструктурные сервисы должны оставаться во внутренней сети deployment.

## Secrets

К секретам относятся, в частности:

- database credentials;
- session secrets;
- gateway tokens;
- API credentials;
- инфраструктурные ключи.

В репозитории допускаются только шаблоны конфигурации без реальных секретов.

## Logging

Логи предназначены для технической диагностики и аудита.

В логи не должны намеренно записываться:

- персональные медицинские данные;
- секреты;
- access tokens;
- исходные идентификаторы пациента.

## Обновление продукта

Обновление Web/API не должно автоматически изменять frozen C7.

Изменение ML release должно выполняться отдельно и явно.

## Защита frozen image

Для финального evaluator используется immutable image digest.

Mutable tag сам по себе не является достаточной гарантией идентичности runtime.

## NVIDIA H200

Frozen C7 runtime использует PyTorch/CUDA stack с поддержкой `sm_90`.

Это обеспечивает архитектурную совместимость с NVIDIA H200/Hopper.

Физический benchmark на H200 командой не выполнялся; фактическая производительность должна проверяться на оборудовании организатора.

## Competition mode

В конкурсном режиме ML inference выполняется без сетевого доступа.

Runtime не должен скачивать модели или обращаться к внешним AI-сервисам во время обработки.

## Deployment boundary

BoneQC является исследовательским и конкурсным прототипом.

Конкретная production-инфраструктура и требования медицинской организации должны проверяться отдельно перед эксплуатацией.
