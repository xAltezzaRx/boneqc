# BoneQC

**BoneQC** — исследовательский веб-сервис для автоматического технического контроля качества DXA-исследований в формате DICOM.

Система оценивает качество выполнения исследования, определяет поддерживаемую анатомическую область и выявляет типовые нарушения качества. BoneQC не ставит диагноз и не заменяет заключение врача.

Проект разработан командой **ХМ ЛАБ** для хакатона 2026.

## Возможности

Поддерживаются исследования:

- поясничного отдела позвоночника;
- проксимального отдела бедренной кости слева;
- проксимального отдела бедренной кости справа.

Для позвоночника контролируются:

- корректность укладки;
- отклонение оси;
- посторонние объекты и выраженные артефакты.

Для бедра контролируются:

- укладка и ротация;
- область интереса и поле обзора.

## Результат анализа

Основной результат технического QC:

~~~text
quality_class = 0 → PASS
quality_class = 1 → FAIL
~~~

Если исследование невозможно корректно оценить автоматически, используется `CANNOT_ASSESS`.

`quality_prob` — непрерывный QC score frozen C7. Он не является accuracy модели, процентом качества исследования или заявленной клинически откалиброванной вероятностью.

## Архитектура

Основной продуктовый контур:

~~~text
Web
 ↓
FastAPI API
 ↓
PostgreSQL / Redis / Object Storage
 ↓
Processing Worker
 ↓
Frozen C7 Runtime
 ↓
AnalysisResult
~~~

ML runtime отделён от продуктового слоя: изменение интерфейса, API или экспертных функций не должно изменять frozen C7.

Подробнее: [архитектура BoneQC](docs/architecture/ARCHITECTURE.md).

## Финальная ML-архитектура

Финальной конкурсной версией является **C7**.

Основные компоненты:

- BiomedCLIP — контроль укладки позвоночника;
- детерминированная геометрия — контроль оси позвоночника;
- RAD-DINO — контроль артефактов позвоночника;
- ResNet18 + C2 — укладка и ротация бедра;
- geometry/FOV + RAD-DINO — контроль области интереса бедра.

История выбора компонентов и экспериментов C7/C8 описана в [EXPERIMENT_HISTORY.md](docs/ml/EXPERIMENT_HISTORY.md).

## Конкурсный evaluator

Для проверки frozen C7 используется отдельный evaluator.

Проверка окружения:

~~~bash
bash evaluator/judge_preflight.sh
~~~

Запуск:

~~~bash
python3 evaluator/boneqc_evaluator.py INPUT OUTPUT_DIR
~~~

Подробная инструкция:

[docs/competition/JUDGE_QUICKSTART.md](docs/competition/JUDGE_QUICKSTART.md)

## Frozen C7 container

Authoritative runtime:

~~~text
ghcr.io/xaltezzarx/boneqc-c7@
sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7
~~~

Для конкурсного inference контейнер запускается без сетевого доступа.

## Документация

- [Архитектура](docs/architecture/ARCHITECTURE.md)
- [API](docs/api/API.md)
- [Рабочий процесс](docs/clinical/CLINICAL_WORKFLOW.md)
- [Model Card](docs/ml/MODEL_CARD.md)
- [Валидация](docs/ml/VALIDATION.md)
- [Данные и разбиение](docs/ml/DATASET_AND_SPLITS.md)
- [История экспериментов](docs/ml/EXPERIMENT_HISTORY.md)
- [Развёртывание](docs/operations/DEPLOYMENT.md)
- [Безопасность и конфиденциальность](docs/security/PRIVACY_AND_SECURITY.md)
- [Запуск evaluator](docs/competition/JUDGE_QUICKSTART.md)

## Статус

BoneQC — исследовательский и конкурсный прототип технического QC.

Система не предназначена для диагностики остеопороза и не является зарегистрированным медицинским изделием.
