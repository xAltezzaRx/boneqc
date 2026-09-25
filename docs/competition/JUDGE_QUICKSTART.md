# BoneQC — запуск конкурсного evaluator

## Назначение

Этот документ описывает проверку окружения и запуск финального frozen C7 runtime.

## Требования

Рекомендуемая среда:

~~~text
Linux x86_64
Docker
NVIDIA GPU
NVIDIA Container Toolkit
Python 3
~~~

Для GPU должен быть доступен рабочий NVIDIA driver и Docker runtime с поддержкой GPU.

## Проверка окружения

Из корня репозитория:

~~~bash
bash evaluator/judge_preflight.sh
~~~

Preflight проверяет:

- Linux/x86_64;
- Docker;
- доступность NVIDIA GPU;
- CUDA runtime;
- evaluator CLI;
- immutable C7 image;
- возможность запуска frozen runtime;
- отсутствие необходимости в сетевом доступе во время inference.

## Frozen C7 runtime

Authoritative container:

~~~text
ghcr.io/xaltezzarx/boneqc-c7@
sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7
~~~

Использование immutable digest исключает незаметную замену образа под тем же Docker tag.

## Поддерживаемый вход

Evaluator принимает:

- отдельный DICOM-файл;
- каталог с DICOM;
- ZIP-архив.

Пример запуска для архива:

~~~bash
python3 evaluator/boneqc_evaluator.py INPUT.zip OUTPUT_DIR
~~~

Пример для каталога:

~~~bash
python3 evaluator/boneqc_evaluator.py ./dicom OUTPUT_DIR
~~~

## Основные выходные файлы

Evaluator создаёт:

~~~text
boneqc-c7-results-v1.csv
boneqc-c7-results-v1.xlsx
boneqc-evaluator-manifest-v1.json
boneqc-evaluator-audit-v1.json
~~~

## Обязательный конкурсный контракт

Результат содержит восемь обязательных полей:

~~~text
path_to_study
study_uid
image_uid
anatomical_region
quality_class
violation_type
processing_status
time_of_processing
~~~

Дополнительно BoneQC сохраняет:

~~~text
quality_prob
~~~

`quality_prob` — непрерывный QC score. Он не заменяет `quality_class`.

## Семантика quality_class

~~~text
0 → PASS
1 → FAIL
~~~

Если автоматическая оценка невозможна, это отражается через `processing_status`.

## Сетевой режим

ML inference выполняется в контейнере без сетевого доступа.

Runtime не должен:

- загружать веса из интернета;
- обращаться к внешним AI API;
- подменять model artifacts во время обработки.

## NVIDIA H200

Frozen runtime использует PyTorch/CUDA stack с поддержкой архитектуры `sm_90`.

NVIDIA H200 относится к архитектуре Hopper (`sm_90`), поэтому runtime является архитектурно совместимым с H200.

Физический запуск и benchmark на H200 командой не выполнялись. Поэтому проект не заявляет физически подтверждённую производительность на H200 до проверки на оборудовании организатора.

## Frozen guarantees

Во время конкурсного запуска не изменяются:

- веса;
- thresholds;
- model selection;
- output semantics;
- frozen model artifacts.

## Назначение результата

BoneQC выполняет технический контроль качества DXA-исследования.

Результат evaluator не является диагнозом.
