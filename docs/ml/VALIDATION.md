# Валидация BoneQC C7

## Назначение

Этот документ описывает one-time validation финального frozen C7.

Development-метрики, использованные при выборе компонентов модели, не являются результатами official VALIDATION и рассматриваются отдельно.

## Протокол

До просмотра validation labels были зафиксированы:

- model selection;
- model artifacts;
- weights;
- thresholds;
- output semantics;
- inference runner.

После получения результатов validation C7 не перенастраивался по этой выборке.

## Выборка

Official VALIDATION:

~~~text
49 image rows
20 unique studies
14 positive
35 negative
~~~

TRAIN и VALIDATION были разделены по study identifier.

Подробности:

[DATASET_AND_SPLITS.md](DATASET_AND_SPLITS.md)

## Overall QC

Итоговые метрики frozen C7:

| Метрика | Значение |
|---|---:|
| Sensitivity | 0.5000 |
| Specificity | 0.8571 |
| F1 | 0.5385 |
| Balanced accuracy | 0.6786 |
| ROC-AUC | 0.7143 |
| PR-AUC, trapezoid | 0.6567 |

## Confusion matrix

~~~text
TP = 7
FP = 5
TN = 30
FN = 7
~~~

## 95% confidence interval

Для оценки неопределённости использовался bootstrap с группировкой по исследованиям.

Для overall QC:

| Метрика | Значение | 95% CI |
|---|---:|---:|
| Sensitivity | 0.5000 | 0.250 – 0.875 |
| Specificity | 0.8571 | 0.742 – 0.956 |
| F1 | 0.5385 | 0.300 – 0.759 |
| Balanced accuracy | 0.6786 | 0.538 – 0.868 |
| ROC-AUC | 0.7143 | 0.491 – 0.946 |
| PR-AUC | 0.6567 | 0.386 – 0.867 |

95% CI — это интервал неопределённости оценки метрики.

Он не означает «95% accuracy».

## Валидация отдельных нарушений

| Задача | N | Positive | F1 | ROC-AUC |
|---|---:|---:|---:|---:|
| Spine positioning | 19 | 1 | 0.0000 | 0.8889 |
| Spine axis | 19 | 2 | 0.5000 | 0.8824 |
| Spine artifact | 19 | 3 | 0.4000 | 0.7292 |
| Hip positioning / rotation | 30 | 7 | 0.6154 | 0.8137 |
| Hip ROI | 30 | 2 | 0.3333 | 0.9286 |

Для задач с очень небольшим числом positive cases точечные значения метрик имеют высокую статистическую неопределённость.

## Aggregate QC по областям

### Позвоночник

~~~text
N        = 19
Positive = 6

F1       = 0.4000
ROC-AUC  = 0.6923
~~~

### Бедро

~~~text
N        = 30
Positive = 8

F1       = 0.6250
ROC-AUC  = 0.7955
~~~

## Ошибки overall QC

По анатомическим областям:

| Область | TP | FP | TN | FN |
|---|---:|---:|---:|---:|
| LEFT_HIP | 2 | 2 | 10 | 2 |
| RIGHT_HIP | 3 | 1 | 9 | 1 |
| SPINE | 2 | 2 | 11 | 4 |

## Компоненты false negative

Среди FN встречались нарушения:

- hip positioning / rotation;
- spine artifact;
- spine axis;
- spine positioning.

## Компоненты false positive

Среди FP встречались:

- hip ROI;
- hip positioning / rotation;
- spine artifact;
- spine axis.

## Class imbalance

Некоторые subtype-задачи представлены очень небольшим числом положительных примеров.

Например:

~~~text
Spine positioning → 1 positive
Spine axis        → 2 positives
Spine artifact    → 3 positives
Hip ROI           → 2 positives
~~~

Поэтому subtype-метрики нельзя интерпретировать без указания N и числа positive cases.

## Что означают значения 80–90%

Высокий ROC-AUC отдельного subtype classifier не означает, что весь BoneQC имеет accuracy 80–90%.

Например, ROC-AUC `0.9286` для Hip ROI рассчитан на:

~~~text
N = 30
Positive = 2
~~~

Это ranking metric конкретного specialist-компонента на небольшой выборке.

## Frozen policy

После one-time validation:

~~~text
model selection changed = NO
thresholds changed      = NO
output semantics changed = NO
validation retuning      = NO
~~~

## Runtime parity

Frozen C7 проверялся на разных NVIDIA runtime-контурах.

На frozen 49-case replay:

- semantic mismatches = 0;
- class flips = 0.

Небольшие численные различия `quality_prob` между CUDA stacks не меняли итоговый класс.

## Ограничения

Текущая validation имеет ограничения:

- всего 20 исследований;
- 49 image rows;
- малое число positive cases по отдельным нарушениям;
- выраженный class imbalance;
- отсутствие независимой многоцентровой внешней проверки.

Поэтому результаты следует рассматривать как validation конкурсного прототипа, а не как доказательство клинической эффективности.

## Независимая конкурсная оценка

Финальная независимая оценка выполняется организатором на закрытом test set.

Команда не использует этот закрытый test set для model selection или threshold tuning.

## Evidence

Агрегированные validation artifacts:

- [validation-ci.csv](evidence/validation-ci.csv)
- [validation-errors.csv](evidence/validation-errors.csv)

История development model selection публикуется отдельно в `EXPERIMENT_HISTORY.md`.
