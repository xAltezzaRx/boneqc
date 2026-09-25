# BoneQC C7 — Model Card

## Назначение

C7 — финальная frozen ML-архитектура BoneQC для автоматического технического контроля качества DXA-исследований в формате DICOM.

Модель оценивает качество выполнения исследования.

C7 не предназначен для диагностики остеопороза и не заменяет заключение врача.

## Поддерживаемые области

~~~text
SPINE
LEFT_HIP
RIGHT_HIP
~~~

## Контролируемые нарушения

### Позвоночник

Контролируются:

- корректность укладки;
- отклонение оси;
- посторонние объекты и выраженные артефакты.

### Проксимальный отдел бедра

Контролируются:

- укладка и ротация;
- область интереса;
- поле обзора.

## Структура C7

C7 не является одним универсальным classifier.

Финальный pipeline объединяет несколько специализированных компонентов.

### Anatomy routing

Входное изображение сначала маршрутизируется в spine или hip pipeline.

### Laterality routing

Для hip определяется левая или правая сторона.

### Spine positioning

Для контроля укладки позвоночника используется frozen BiomedCLIP representation и зафиксированный classifier.

Foundation model:

~~~text
microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224
~~~

### Spine axis

Контроль оси использует детерминированный геометрический сигнал.

Для ranking на development data геометрический сигнал оказался сильнее проверенных RAD-DINO и BiomedCLIP alternatives.

Semantic rule для итогового subtype decision является частью frozen C7 contract.

### Spine artifact

Для контроля посторонних объектов и выраженных артефактов используется RAD-DINO / DINOv2-based representation и зафиксированный classifier.

### Hip positioning / rotation

Используется фиксированная комбинация:

~~~text
ResNet18 + C2 center-medial signal
~~~

Комбинация была выбрана на development data до one-time validation.

### Hip ROI / FOV

Для standalone ROI decision используется geometry/FOV specialist.

RAD-DINO применяется дополнительно внутри общей hip-quality aggregation.

Standalone ROI decision и aggregate hip QC не являются одной и той же величиной.

## Итоговая архитектура

~~~text
SPINE
  positioning → BiomedCLIP
  axis        → deterministic geometry
  artifact    → RAD-DINO

HIP
  positioning / rotation → ResNet18 + C2
  ROI / FOV              → geometry specialist
  aggregate hip QC       → geometry + conservative RAD-DINO gate
~~~

## Формирование результата

Основной бинарный результат:

~~~text
quality_class = 0 → PASS
quality_class = 1 → FAIL
~~~

`quality_class` формируется из зафиксированных specialist decisions и правил агрегации.

## quality_prob

`quality_prob` — непрерывный QC score frozen C7.

Он используется как дополнительный численный сигнал, но не является:

- accuracy модели;
- процентом качества исследования;
- вероятностью диагноза;
- вероятностью того, что модель права;
- заявленной клинически откалиброванной вероятностью.

Итоговый класс нельзя восстанавливать правилом:

~~~text
quality_prob >= 0.5
~~~

поскольку отдельные компоненты используют собственные frozen thresholds и правила принятия решения.

## violation_type

`violation_type` содержит тип или типы выявленных нарушений качества.

Он формируется согласованно с итоговыми subtype decisions.

## processing_status

Технический статус обработки отделён от бинарного QC результата.

Если автоматическая оценка невозможна, это не должно интерпретироваться как PASS.

## Frozen policy

До просмотра official VALIDATION labels были зафиксированы:

- model selection;
- model artifacts;
- weights;
- thresholds;
- output semantics;
- inference runner.

После one-time validation C7 не перенастраивался по её результатам.

## Authoritative runtime

~~~text
ghcr.io/xaltezzarx/boneqc-c7@
sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7
~~~

Runtime может выполнять inference без сетевого доступа при наличии frozen artifacts.

## RTX / GTX parity

Compatibility runtime для GTX использует ту же C7-модель.

При проверке frozen 49-case replay:

- semantic mismatches отсутствовали;
- class flips отсутствовали;
- небольшие численные различия `quality_prob` не меняли итоговый класс.

Compatibility runtime не является новой обученной моделью.

## Валидация

One-time official validation описана отдельно:

[VALIDATION.md](VALIDATION.md)

## Данные и разбиение

Описание TRAIN / VALIDATION и leakage guardrails:

[DATASET_AND_SPLITS.md](DATASET_AND_SPLITS.md)

## История выбора компонентов

Development model selection и последующие C8 challenger-эксперименты описываются отдельно:

`EXPERIMENT_HISTORY.md`

## Ограничения

C7 имеет ограничения:

- малое число positive cases для ряда нарушений;
- class imbalance;
- ограничение поддерживаемыми анатомическими областями;
- отсутствие внешней многоцентровой clinical validation;
- необходимость отдельной проверки на данных других устройств и учреждений.

Prototype validation не эквивалентна медицинской сертификации.

## Clinical boundary

C7 выполняет технический QC DXA-исследования.

C7 не ставит диагноз.
