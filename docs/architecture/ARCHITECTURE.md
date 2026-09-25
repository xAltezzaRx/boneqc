# Архитектура BoneQC

## Назначение

BoneQC состоит из двух логически разделённых контуров:

1. продуктового веб-сервиса;
2. frozen C7 runtime и конкурсного evaluator.

Такое разделение позволяет развивать интерфейс, API и экспертные функции без изменения зафиксированной ML-модели.

## Общая схема

~~~text
Browser
  ↓
Next.js Web
  ↓
FastAPI API
  ├── PostgreSQL
  ├── Redis
  └── Object Storage
        ↓
   Processing Worker
        ↓
   Frozen C7 Runtime
        ↓
   AnalysisResult
~~~

Конкурсный контур:

~~~text
DICOM / ZIP / directory
        ↓
boneqc_evaluator.py
        ↓
immutable C7 container
        ↓
CSV / XLSX / manifest / audit
~~~

## Web

Frontend реализован на Next.js.

Основные сценарии:

- авторизация;
- загрузка исследования;
- просмотр списка исследований;
- просмотр результата QC;
- экспертная разметка;
- административный интерфейс.

Web не выполняет ML inference.

## API

Backend реализован на FastAPI.

Основные задачи:

- пользователи и RBAC;
- исследования;
- приём DICOM;
- очередь анализа;
- результаты;
- экспертные аннотации;
- аудит;
- управление служебными объектами системы.

## Хранение данных

### PostgreSQL

Хранит структурированные данные:

- исследования;
- пользователей;
- задания анализа;
- результаты;
- экспертные аннотации;
- audit events.

### Redis

Используется как инфраструктурный компонент очереди и служебного состояния обработки.

### Object Storage

Используется для файлов исследования и производных объектов.

## DICOM processing boundary

До передачи данных в ML-контур выполняются:

- проверка входного DICOM;
- деидентификация;
- удаление или замена идентифицирующих metadata;
- UID remapping;
- подготовка объекта для дальнейшей обработки.

Preview-изображение используется интерфейсом и не является входом frozen C7.

## Frozen C7 Runtime

C7 — финальная зафиксированная ML-архитектура BoneQC.

### Routing

Сначала определяется анатомическая область:

~~~text
SPINE
LEFT_HIP
RIGHT_HIP
~~~

Для hip также определяется сторона исследования.

### Позвоночник

Используются три специализированных сигнала:

~~~text
positioning → BiomedCLIP
axis        → deterministic geometry
artifact    → RAD-DINO
~~~

### Бедро

Используются:

~~~text
positioning / rotation → ResNet18 + C2
ROI / FOV              → geometry/FOV + RAD-DINO
~~~

Standalone ROI decision и общий hip-quality score имеют разные роли.

## Семантика результата

~~~text
quality_class = 0 → PASS
quality_class = 1 → FAIL
~~~

`quality_class` формируется из зафиксированных subtype decisions.

`quality_prob` — непрерывный QC score и не является самостоятельным правилом классификации.

Нельзя восстанавливать итоговый класс простым правилом:

~~~text
quality_prob >= 0.5
~~~

поскольку отдельные specialists используют собственные frozen thresholds и правила агрегации.

## CANNOT_ASSESS

Если исследование не относится к поддерживаемой области или безопасная автоматическая оценка невозможна, система должна вернуть состояние невозможности оценки, а не PASS.

## Processing Worker

Worker:

1. получает задание;
2. извлекает подготовленный DICOM;
3. передаёт данные в frozen runtime;
4. получает результат;
5. сохраняет `AnalysisResult`.

## BoneQC Expert

Экспертный контур хранится отдельно от автоматического C7 result.

Эксперт может:

- указать оценку качества;
- выбрать тип нарушения;
- добавить комментарий;
- сохранить геометрическую разметку;
- отметить невозможность оценки.

Экспертная разметка не изменяет frozen C7.

## Blind expert workflow

При независимой экспертной проверке врач формирует собственную оценку до просмотра автоматического результата.

Это позволяет сравнивать экспертную и автоматическую оценку без прямого влияния ответа модели на первоначальную разметку.

## Runtime isolation

Для C7 отдельно зафиксированы:

- model artifacts;
- weights;
- thresholds;
- model selection;
- output semantics;
- inference runner;
- зависимости runtime.

Конкурсный evaluator запускает runtime без сетевого доступа.

## Deployment runtime

Основной inference рассчитан на NVIDIA GPU.

Дополнительный GTX-контур является compatibility/fallback runtime той же C7-модели:

- веса не меняются;
- thresholds не меняются;
- decision semantics не меняются.

## Trust boundaries

BoneQC разделяет:

~~~text
product data
frozen model artifacts
expert annotations
~~~

Изменение одного контура не должно неявно изменять другой.

## Clinical boundary

BoneQC выполняет технический QC DXA-исследования.

Система не определяет диагноз и не заменяет медицинское заключение.
