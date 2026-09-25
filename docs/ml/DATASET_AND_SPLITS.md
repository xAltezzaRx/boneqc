# Данные и разбиение выборки C7

## Назначение

Этот документ описывает разбиение данных, использованное при разработке и one-time validation frozen C7.

C8 использует отдельную methodology и не должен смешиваться с этим split.

## Разбиение по исследованиям

Основной C7 dataset разделён по study identifier:

~~~text
TRAIN       = 80 исследований
VALIDATION  = 20 исследований
TOTAL       = 100 исследований
~~~

Official VALIDATION содержит:

~~~text
49 image rows
20 unique studies
~~~

TRAIN и VALIDATION не пересекаются по study identifier.

## TRAIN class support

### Позвоночник

| Задача | N | Positive | Negative |
|---|---:|---:|---:|
| positioning | 80 | 5 | 75 |
| axis | 80 | 8 | 72 |
| artifact | 80 | 14 | 66 |
| overall spine quality | 80 | 25 | 55 |

### Бедро

Для hip задачи строка соответствует размеченной стороне исследования.

| Задача | N | Positive | Negative |
|---|---:|---:|---:|
| positioning / rotation | 120 | 29 | 91 |
| ROI | 120 | 5 | 115 |
| overall hip quality | 120 | 33 | 87 |

## Official VALIDATION class support

### Позвоночник

| Задача | N | Positive | Negative |
|---|---:|---:|---:|
| positioning | 19 | 1 | 18 |
| axis | 19 | 2 | 17 |
| artifact | 19 | 3 | 16 |

### Бедро

| Задача | N | Positive | Negative |
|---|---:|---:|---:|
| positioning / rotation | 30 | 7 | 23 |
| ROI | 30 | 2 | 28 |

### Overall QC

~~~text
N         = 49
Positive  = 14
Negative  = 35
~~~

## Class imbalance

Некоторые нарушения представлены очень небольшим числом positive cases.

Особенно:

~~~text
TRAIN hip ROI            = 5 positives
VALIDATION positioning   = 1 positive
VALIDATION spine axis    = 2 positives
VALIDATION hip ROI       = 2 positives
~~~

Поэтому subtype metrics имеют высокую статистическую неопределённость и должны интерпретироваться вместе с числом positive cases.

## Development OOF

Выбор компонентов C7 выполнялся только на TRAIN.

Для большинства development artifacts использовались held-out fold predictions.

Аудит OOF artifacts показал:

~~~text
candidate files               = 19
files with study column       = 18
files with fold column        = 17
studies in multiple folds     = 0
validation overlap events     = 0
~~~

Для audited artifacts с fold assignment каждое исследование находилось только в одном held-out fold.

## TRAIN / VALIDATION isolation

Итоговый аудит подтвердил:

~~~text
train / validation isolation = PASS
union validation overlap     = 0
~~~

Official VALIDATION studies не входили в development OOF model-selection artifacts.

## Guardrails

Во время split/leakage audit:

~~~text
inference executed          = false
model selection changed     = false
thresholds changed          = false
validation retuning         = false
patient metadata published  = false
UID values published        = false
~~~

## One-time validation policy

Official VALIDATION была изолирована от model selection и threshold tuning.

После однократной оценки frozen C7:

- model selection не изменялся;
- thresholds не изменялись;
- output semantics не изменялись.

## C8 boundary

После завершения C7 был проведён отдельный C8 challenger cycle.

Поскольку результаты C7 VALIDATION к тому моменту уже были известны, эта выборка не рассматривалась как новая независимая blind validation для C8.

C8 evaluation methodology описывается в `EXPERIMENT_HISTORY.md`.

## Public evidence

Агрегированный audit:

[split-leakage.json](evidence/split-leakage.json)
