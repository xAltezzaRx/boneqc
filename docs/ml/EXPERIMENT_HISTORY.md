# История развития ML-архитектуры BoneQC

## Назначение

Этот документ описывает, как команда пришла к финальной архитектуре C7 и почему последующий challenger cycle C8 не заменил её.

Здесь приведены только инженерно значимые этапы и результаты.

Документ содержит только итоговые инженерно значимые эксперименты, сравнения и решения.

## Принцип разработки

BoneQC не строился как единый универсальный classifier.

Задача технического QC была разделена на отдельные нарушения, после чего для каждого подтипа сравнивались специализированные подходы.

Основные группы кандидатов:

- convolutional models;
- medical vision-language embeddings;
- self-supervised medical image embeddings;
- deterministic geometry;
- фиксированные комбинации specialist signals.

Development metrics ниже использовались для выбора архитектуры и не являются результатами official VALIDATION.

## Укладка позвоночника

Проверялись baseline, RAD-DINO, BiomedCLIP и фиксированная fusion-схема.

| Кандидат | ROC-AUC | PR-AUC |
|---|---:|---:|
| Baseline | 0.8267 | 0.5443 |
| RAD-DINO | 0.5680 | 0.1740 |
| BiomedCLIP | **0.9920** | **0.9250** |
| Baseline + BiomedCLIP | 0.9653 | 0.7958 |

Выбран standalone **BiomedCLIP**.

Фиксированное объединение с baseline было хуже standalone BiomedCLIP по обеим point estimates.

## Ось позвоночника

Сравнивались deterministic geometry, RAD-DINO и BiomedCLIP.

| Кандидат | ROC-AUC | PR-AUC |
|---|---:|---:|
| Deterministic axis magnitude | **0.8594** | **0.3815** |
| RAD-DINO | 0.5503 | 0.1318 |
| BiomedCLIP | 0.4097 | 0.0976 |

Для этой задачи геометрический сигнал оказался сильнее learned representations.

Поэтому в C7 сохранён deterministic axis specialist.

Отдельный semantic threshold для нарушения оси является частью frozen C7 contract и не следует напрямую из ROC-AUC ranking comparison.

## Артефакты позвоночника

Сравнивались baseline, RAD-DINO, BiomedCLIP и fixed fusion.

| Кандидат | ROC-AUC | PR-AUC |
|---|---:|---:|
| Baseline | 0.7013 | 0.2903 |
| RAD-DINO | **0.8485** | **0.6909** |
| BiomedCLIP | 0.6840 | 0.3100 |
| Baseline + RAD-DINO | 0.8571 | 0.6494 |

Fusion давал небольшое увеличение ROC-AUC, но уменьшал PR-AUC.

Paired bootstrap не показал устойчивого преимущества fusion над standalone RAD-DINO.

В C7 выбран **RAD-DINO**.

## Итоговый QC позвоночника

Сравнивались direct score и фиксированные способы объединения specialist signals.

| Вариант | ROC-AUC | PR-AUC |
|---|---:|---:|
| Direct score | 0.6255 | 0.4246 |
| Direct + RAD-DINO | 0.6778 | 0.5461 |
| Specialist max | 0.8425 | 0.6240 |
| Specialist mean | **0.8400** | **0.6562** |

`specialist max` имел практически сопоставимый ROC-AUC, однако `specialist mean` показал более высокий PR-AUC.

Для C7 выбрана фиксированная specialist aggregation без обучаемых fusion weights.

## Укладка и ротация бедра

Проверялись ResNet18, C2 center-medial signal, их fixed fusion, RAD-DINO и BiomedCLIP.

| Кандидат | ROC-AUC | PR-AUC |
|---|---:|---:|
| ResNet18 baseline | 0.7571 | 0.5484 |
| C2 center-medial | 0.8128 | 0.6424 |
| ResNet18 + C2, 50/50 | **0.8268** | **0.6472** |
| RAD-DINO | 0.6340 | 0.3382 |
| BiomedCLIP | 0.5794 | 0.3866 |

В C7 сохранена фиксированная комбинация **ResNet18 + C2**.

## ROI и поле обзора бедра

Сравнивались baseline, RAD-DINO, BiomedCLIP и геометрический FOV specialist.

| Кандидат | ROC-AUC | PR-AUC |
|---|---:|---:|
| Baseline | 0.7565 | 0.1319 |
| RAD-DINO | 0.7113 | 0.2025 |
| BiomedCLIP | 0.4157 | 0.0991 |
| FOV geometry specialist | **0.8365** | **0.5453** |
| Baseline + FOV geometry | 0.8330 | 0.4973 |

Лучшее сочетание development ROC-AUC и PR-AUC показал geometry/FOV specialist.

Он выбран для standalone ROI decision.

## Итоговый QC бедра

Для overall hip QC проверялись несколько фиксированных формул.

| Формула | ROC-AUC | PR-AUC |
|---|---:|---:|
| Direct hip score | 0.7677 | 0.6163 |
| max(rotation, ROI geometry) | 0.8349 | 0.6803 |
| max(rotation, ROI geometry/current) | 0.8387 | 0.7042 |
| max(rotation, min(ROI geometry, ROI RAD-DINO)) | **0.8575** | **0.7295** |

В финальной aggregation RAD-DINO используется как консервативный gate внутри hip-quality score.

Standalone ROI decision при этом остаётся геометрическим.

## Финальная архитектура C7

После development model selection была зафиксирована архитектура:

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

После freeze C7 прошёл отдельную one-time validation.

Результаты этой validation не использовались для последующей перенастройки C7.

См. [VALIDATION.md](VALIDATION.md).

## Почему появился C8

После завершения C7 была предпринята отдельная попытка улучшить финальное overall QC решение.

К этому моменту исторические результаты C7 VALIDATION уже были известны.

Поэтому она не могла использоваться как новая независимая blind validation для C8.

C8 оценивался в отдельном repeated grouped development CV.

## C7 reference внутри C8

C7 был воспроизведён внутри C8 CV как фиксированная reference architecture.

~~~text
repeats       = 10
rows / repeat = 249

mean F1       = 0.6340
mean ROC-AUC  = 0.7840
~~~

Это development CV reference.

Это не независимый final-test estimate.

## Promotion gate

Для confirmatory C8 candidate заранее использовались требования:

~~~text
mean ΔF1      >= +0.02
mean ΔROC-AUC >= +0.01

ΔF1 > 0       минимум в 7/10 repeats
ΔROC-AUC > 0  минимум в 7/10 repeats

protocol integrity = PASS
~~~

## Decision layer: Noisy-OR

~~~text
mean ΔF1      = -0.0502
mean ΔROC-AUC = -0.0038

positive F1 repeats      = 0/10
positive ROC-AUC repeats = 5/10
~~~

Результат:

~~~text
DO_NOT_PROMOTE
~~~

## Decision layer: regularized logistic stacker

~~~text
mean ΔF1      = -0.0383
mean ΔROC-AUC = -0.0077

positive F1 repeats      = 1/10
positive ROC-AUC repeats = 3/10
~~~

Результат:

~~~text
DO_NOT_PROMOTE
~~~

Confirmatory first promotion gate сохранил C7 reference.

## Score-only alternative

Отдельно проверялся вариант изменения только continuous score при сохранении class decisions.

~~~text
ΔF1      = 0
ΔROC-AUC = -0.0072

positive ROC-AUC repeats = 2/10
~~~

Результат:

~~~text
DO_NOT_ACCEPT_SCORE_ONLY
~~~

## Direct overall-QC head

Exploratory candidate:

~~~text
mean ΔF1      = -0.0863
mean ΔROC-AUC = -0.0329

positive repeats = 0/10
~~~

Результат:

~~~text
EXPLORATORY_NOT_ADOPTED
~~~

## Patch-token RAD-DINO

Exploratory patch-token candidate:

~~~text
C7 mean F1        = 0.6340
candidate mean F1 = 0.5908
ΔF1               = -0.0431

C7 mean ROC-AUC        = 0.7840
candidate mean ROC-AUC = 0.7688
ΔROC-AUC               = -0.0153

positive repeats = 1/10
~~~

Результат:

~~~text
EXPLORATORY_NOT_ADOPTED
~~~

## Geometry challenger

Для C8 была предусмотрена отдельная geometry branch.

Однозначный совместимый C8 implementation contract восстановить не удалось.

После просмотра frozen outer results новый candidate создавать и оптимизировать на тех же folds было бы методологически некорректно.

Поэтому дополнительный performance experiment не запускался.

~~~text
EXPLORATORY_NOT_EXECUTED
~~~

## Synthetic positives

Исторический synthetic pipeline также рассматривался как возможный challenger.

Он не соответствовал зафиксированному C8 subtype/fold contract.

Новый эксперимент на уже просмотренных frozen folds не запускался.

~~~text
EXPLORATORY_NOT_EXECUTED
~~~

## Итог C8

Ни один кандидат не выполнил условия promotion.

Формальное решение:

~~~text
NO_C8_PROMOTION_KEEP_C7
~~~

Выбранный release:

~~~text
C7
~~~

C8 не рассматривается как неудачная попытка, которую нужно скрывать.

Он показал, что более сложный decision layer и дополнительные learned candidates на доступных development данных не дали устойчивого преимущества над уже собранной specialist architecture C7.

## Что считается независимой оценкой

C7 one-time VALIDATION и C8 development CV имеют разные назначения.

C8 CV не является независимой финальной оценкой конкурсной производительности.

Окончательная независимая проверка выполняется организатором на закрытом test set.

## Публичные evidence

Агрегированное сравнение C7 candidates:

[model-selection.csv](evidence/model-selection.csv)

Данные и leakage audit:

[DATASET_AND_SPLITS.md](DATASET_AND_SPLITS.md)

One-time C7 validation:

[VALIDATION.md](VALIDATION.md)
