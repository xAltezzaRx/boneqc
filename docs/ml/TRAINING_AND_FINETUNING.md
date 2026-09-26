# BoneQC — training / fine-tuning guide

## 1. Назначение

Этот документ описывает правила дальнейшей исследовательской разработки моделей BoneQC.

Он не является инструкцией по изменению финального competition C7.

## 2. Frozen C7 policy

Текущий competition C7 зафиксирован.

Нельзя изменять его:

- weights;
- thresholds;
- model selection;
- aggregation logic;
- output semantics;

и продолжать называть изменённый runtime тем же C7 release.

## 3. Новый эксперимент

Любое новое обучение или fine-tuning должно выполняться как отдельный challenger experiment.

Рекомендуемый принцип:

```text
frozen C7
vs
new challenger
```

## 4. Data split discipline

Необходимо сохранять разделение:

```text
TRAIN / development
VALIDATION
future external / closed test
```

Official validation не должна использоваться для ретроспективной настройки C7.

## 5. Leakage guardrails

Перед обучением необходимо проверять:

- duplicate studies;
- duplicate images;
- UID overlap;
- patient/study leakage;
- near-duplicate preprocessing artifacts;
- accidental validation feature fitting.

## 6. Class imbalance

Для редких violations необходимо отдельно учитывать:

- число positives;
- class weights / sampling strategy;
- threshold instability;
- confidence intervals.

Высокий ROC-AUC при очень малом числе positives не следует интерпретировать без `n`.

## 7. Metrics

Для binary QC:

- sensitivity;
- specificity;
- balanced accuracy;
- F1;
- ROC-AUC;
- PR-AUC.

Для multi-label subtype evaluation:

- per-subtype F1;
- macro-F1;
- ROC/PR metrics where meaningful.

Для geometry/localization:

- Dice;
- IoU;
- keypoint distance;

если соответствующий функционал действительно реализован.

## 8. Confidence intervals

Для итоговой оценки желательно рассчитывать 95% CI.

Для study-level clustered data bootstrap должен учитывать группировку по исследованию.

95% CI не означает 95% accuracy.

## 9. Champion selection

Model selection выполняется только на development evidence.

После выбора champion необходимо зафиксировать:

- architecture;
- preprocessing;
- artifacts;
- weights;
- thresholds;
- hashes;
- exact evaluation script.

## 10. Promotion gate

Новый challenger должен сравниваться с текущим frozen champion до promotion.

Если улучшение не подтверждено, сохраняется текущий champion.

Именно так C8 не был promoted поверх C7.

## 11. Reproducibility

Для каждого experiment желательно сохранять:

- source commit;
- environment/dependencies;
- dataset manifest;
- random seed;
- training config;
- artifact hashes;
- metrics;
- decision to promote / reject.

## 12. Runtime parity

Перед deployment новой модели необходимо проверить:

- CPU/GPU preprocessing parity;
- target GPU inference;
- output schema;
- class decision parity;
- deterministic/repeatable behavior where expected.

## 13. Security

Medical data для обучения не должны попадать в публичный repository.

Использование внешних AI services для medical images требует отдельного разрешённого security/privacy contour.

## 14. Clinical boundary

Новая модель BoneQC должна сохранять scope технического QC, если отдельно не проводится новый clinical/regulatory project.
