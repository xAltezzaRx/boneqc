# BoneQC evaluator

Каталог содержит конкурсный wrapper для запуска frozen C7 runtime.

Основная инструкция:

[Judge Quickstart](../docs/competition/JUDGE_QUICKSTART.md)

Проверка окружения:

~~~bash
bash evaluator/judge_preflight.sh
~~~

Запуск:

~~~bash
python3 evaluator/boneqc_evaluator.py INPUT OUTPUT_DIR
~~~

Evaluator использует immutable frozen C7 container.

Во время конкурсного inference:

- модель не переобучается;
- thresholds не изменяются;
- внешние AI API не используются;
- runtime запускается без сетевого доступа.

Основной результат сохраняется в CSV/XLSX вместе с manifest и audit-файлом.
