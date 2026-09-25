"use client";

import {
  useMemo,
  useState,
} from "react";


export type ExpertAnatomy =
  | "SPINE"
  | "HIP";


export interface ExpertPoint {
  x: number;
  y: number;
}


export interface ExpertGeometryItem {
  criterionCode: string;

  kind:
    | "POINT"
    | "LINE"
    | "POLYLINE"
    | "BOX"
    | "POLYGON";

  label: string;

  points: ExpertPoint[];
}


type ReviewValue =
  | "NORMAL"
  | "VIOLATION"
  | "CANNOT_ASSESS";


type Confidence =
  | 1
  | 2
  | 3
  | 4
  | 5;


interface Props {
  studyId: string;
  open: boolean;
  onClose: () => void;

  embedded?: boolean;

  anatomy?: ExpertAnatomy | null;

  geometry?: ExpertGeometryItem[];

  onAnatomyChange?: (
    anatomy: ExpertAnatomy,
  ) => void;

  onSubmitted?: (
    annotationId?: string,
  ) => void;
}


interface Criterion {
  code: string;
  title: string;
  description: string;
}


const CRITERIA: Record<
  ExpertAnatomy,
  Criterion[]
> = {
  SPINE: [
    {
      code: "SPINE_POSITIONING",
      title: "Укладка",
      description:
        "Проверка границ сканирования: "
        + "подвздошные кости и уровень Th12.",
    },
    {
      code: "SPINE_AXIS",
      title: "Ось позвоночника",
      description:
        "Проверка выравнивания оси "
        + "позвоночника и допустимого наклона.",
    },
    {
      code: "SPINE_ARTIFACTS",
      title: "Посторонние предметы",
      description:
        "Проверка выраженных артефактов, "
        + "металлических предметов и наложений.",
    },
  ],

  HIP: [
    {
      code: "HIP_POSITIONING_ROTATION",
      title: "Укладка и ротация",
      description:
        "Оценка позиционирования бедра "
        + "и ротации по малому вертелу.",
    },
    {
      code: "HIP_ROI",
      title: "Область интереса",
      description:
        "Проверка полноты визуализации "
        + "и границ области исследования.",
    },
  ],
};


const ALL_CRITERIA = [
  ...CRITERIA.SPINE,
  ...CRITERIA.HIP,
];


function initialValues():
  Record<
    string,
    ReviewValue | null
  > {
  return Object.fromEntries(
    ALL_CRITERIA.map(
      (criterion) => [
        criterion.code,
        null,
      ],
    ),
  );
}


function initialConfidence():
  Record<
    string,
    Confidence | null
  > {
  return Object.fromEntries(
    ALL_CRITERIA.map(
      (criterion) => [
        criterion.code,
        null,
      ],
    ),
  );
}


function initialComments():
  Record<string, string> {
  return Object.fromEntries(
    ALL_CRITERIA.map(
      (criterion) => [
        criterion.code,
        "",
      ],
    ),
  );
}


function valueTitle(
  value: ReviewValue | null,
): string {
  if (value === null) {
    return "Не выбрано";
  }

  switch (value) {
    case "NORMAL":
      return "Соответствует";

    case "VIOLATION":
      return "Есть нарушение";

    case "CANNOT_ASSESS":
      return "Невозможно оценить";
  }
}


export function ExpertReviewDrawer({
  studyId,
  open,
  onClose,
  embedded = false,
  anatomy,
  geometry = [],
  onAnatomyChange,
  onSubmitted,
}: Props) {
  const [
    internalAnatomy,
    setInternalAnatomy,
  ] = useState<
    ExpertAnatomy | null
  >(
    null,
  );

  const activeAnatomy =
    anatomy ?? internalAnatomy;

  const [
    values,
    setValues,
  ] = useState<
    Record<
      string,
      ReviewValue | null
    >
  >(
    initialValues,
  );

  const [
    confidence,
    setConfidence,
  ] = useState<
    Record<
      string,
      Confidence | null
    >
  >(
    initialConfidence,
  );

  const [
    comments,
    setComments,
  ] = useState<
    Record<string, string>
  >(
    initialComments,
  );

  const [
    generalComment,
    setGeneralComment,
  ] = useState("");

  const [
    submitting,
    setSubmitting,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    success,
    setSuccess,
  ] = useState("");

  const criteria =
    activeAnatomy
      ? CRITERIA[activeAnatomy]
      : [];


  const labels =
    useMemo(
      () => {
        const clinicalLabels =
          criteria.map(
            (criterion) => {
              const value =
                values[
                  criterion.code
                ];

              const comment =
                comments[
                  criterion.code
                ].trim();

              if (
                value
                === "CANNOT_ASSESS"
              ) {
                return {
                  code:
                    criterion.code,

                  assessable:
                    false,

                  class_label:
                    null,

                  confidence:
                    null,

                  comment:
                    comment || null,

                  geometry:
                    geometry
                      .filter(
                        (item) =>
                          item.criterionCode
                          === criterion.code,
                      )
                      .map(
                        (item) => ({
                          kind:
                            item.kind,

                          label:
                            item.label,

                          points:
                            item.points,
                        }),
                      ),
                };
              }

              return {
                code:
                  criterion.code,

                assessable:
                  true,

                class_label:
                  value,

                confidence:
                  confidence[
                    criterion.code
                  ] === null
                    ? null
                    : (
                        confidence[
                          criterion.code
                        ]! / 5
                      ),

                comment:
                  comment || null,

                geometry:
                  geometry
                    .filter(
                      (item) =>
                        item.criterionCode
                        === criterion.code,
                    )
                    .map(
                      (item) => ({
                        kind:
                          item.kind,

                        label:
                          item.label,

                        points:
                          item.points,
                      }),
                    ),
              };
            },
          );

        const finalComment =
          generalComment.trim();

        if (finalComment) {
          clinicalLabels.push({
            code:
              "EXPERT_COMMENT",

            assessable:
              false,

            class_label:
              null,

            confidence:
              null,

            comment:
              finalComment,

            geometry: [],
          });
        }

        return clinicalLabels;
      },
      [
        comments,
        confidence,
        criteria,
        generalComment,
        geometry,
        values,
      ],
    );


  const canSubmit =
    activeAnatomy !== null
    && criteria.length > 0
    && criteria.every(
      (criterion) => {
        const value =
          values[
            criterion.code
          ];

        if (value === null) {
          return false;
        }

        if (
          value
          === "CANNOT_ASSESS"
        ) {
          return true;
        }

        return (
          confidence[
            criterion.code
          ] !== null
        );
      },
    );


  if (!open && !embedded) {
    return null;
  }


  function changeAnatomy(
    value: ExpertAnatomy,
  ) {
    setInternalAnatomy(
      value,
    );

    onAnatomyChange?.(
      value,
    );
    setError("");
    setSuccess("");
  }


  async function submit() {
    if (!canSubmit) {
      setError(
        "Выберите анатомическую область "
        + "и заполните все обязательные "
        + "критерии экспертной оценки.",
      );

      return;
    }

    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const response =
        await fetch(
          `/api/backend/studies/${studyId}/annotations`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              schema_version:
                "boneqc-expert-v1",

              labels,
            }),
          },
        );

      const data =
        await response
          .json()
          .catch(
            () => null,
          ) as {
            id?: string;

            detail?:
              | string
              | {
                  code?: string;
                };
          } | null;

      if (!response.ok) {
        const detail =
          data?.detail;

        const message =
          typeof detail === "string"
            ? detail
            : (
                detail?.code
                ?? `HTTP ${response.status}`
              );

        throw new Error(
          message,
        );
      }

      setSuccess(
        data?.id
          ? (
              "Экспертная оценка сохранена. "
              + `ID: ${data.id}`
            )
          : (
              "Экспертная оценка "
              + "сохранена."
            ),
      );

      onSubmitted?.(
        data?.id,
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : String(reason),
      );
    } finally {
      setSubmitting(false);
    }
  }


  return (
    <div
      className={
        embedded
          ? "expert-embedded-backdrop"
          : "review-drawer-backdrop"
      }
      role="presentation"
      onMouseDown={(event) => {
        if (
          !embedded
          && event.target
            === event.currentTarget
        ) {
          onClose();
        }
      }}
    >
      <aside
        className={
          embedded
            ? "boneqc-expert-embedded"
            : (
                "review-drawer "
                + "boneqc-expert-drawer"
              )
        }
        aria-label={
          "BoneQC Expert"
        }
      >
        <div
          className={
            "review-drawer-header"
          }
        >
          <div>
            <div
              className={
                "expert-eyebrow"
              }
            >
              BONEQC EXPERT
            </div>

            <h2>
              Независимая экспертная
              оценка
            </h2>

            <div className="muted">
              Результат ИИ не используется
              при заполнении формы.
            </div>
          </div>

          <button
            className="icon-button"
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>

        <div
          className={
            "expert-blind-banner"
          }
        >
          <strong>
            Blind review
          </strong>

          <span>
            Сначала фиксируется мнение
            эксперта. Сравнение с BoneQC
            выполняется отдельно.
          </span>
        </div>

        <section
          className={
            "expert-section"
          }
        >
          <h3>
            Анатомическая область
          </h3>

          <div
            className={
              "expert-anatomy-switch"
            }
          >
            <button
              type="button"
              className={
                activeAnatomy === "SPINE"
                  ? (
                      "expert-anatomy-button "
                      + "active"
                    )
                  : (
                      "expert-anatomy-button"
                    )
              }
              onClick={() =>
                changeAnatomy(
                  "SPINE",
                )
              }
            >
              Позвоночник
            </button>

            <button
              type="button"
              className={
                activeAnatomy === "HIP"
                  ? (
                      "expert-anatomy-button "
                      + "active"
                    )
                  : (
                      "expert-anatomy-button"
                    )
              }
              onClick={() =>
                changeAnatomy(
                  "HIP",
                )
              }
            >
              Проксимальный отдел бедра
            </button>
          </div>
        </section>

        <section
          className={
            "expert-section"
          }
        >
          <div
            className={
              "expert-section-heading"
            }
          >
            <div>
              <h3>
                Критерии качества
              </h3>

              <div className="muted">
                Оцените каждый критерий
                независимо.
              </div>
            </div>

            <span
              className={
                "expert-counter"
              }
            >
              {criteria.length}
            </span>
          </div>

          <div
            className={
              "expert-criteria"
            }
          >
            {criteria.map(
              (criterion) => {
                const value =
                  values[
                    criterion.code
                  ];

                return (
                  <article
                    className={
                      "expert-criterion"
                    }
                    key={
                      criterion.code
                    }
                  >
                    <div
                      className={
                        "expert-criterion-head"
                      }
                    >
                      <div>
                        <strong>
                          {criterion.title}
                        </strong>

                        <p>
                          {
                            criterion
                              .description
                          }
                        </p>
                      </div>

                      <span
                        className={
                          "expert-status "
                          + (
                            value
                            === "VIOLATION"
                              ? "violation"
                              : (
                                  value
                                  === "NORMAL"
                                    ? "normal"
                                    : "unknown"
                                )
                          )
                        }
                      >
                        {
                          valueTitle(
                            value,
                          )
                        }
                      </span>
                    </div>

                    <div
                      className={
                        "expert-value-grid"
                      }
                    >
                      <button
                        type="button"
                        className={
                          value === "NORMAL"
                            ? (
                                "expert-value-button "
                                + "selected-normal"
                              )
                            : (
                                "expert-value-button"
                              )
                        }
                        onClick={() =>
                          setValues(
                            (current) => ({
                              ...current,
                              [
                                criterion
                                  .code
                              ]:
                                "NORMAL",
                            }),
                          )
                        }
                      >
                        Соответствует
                      </button>

                      <button
                        type="button"
                        className={
                          value
                          === "VIOLATION"
                            ? (
                                "expert-value-button "
                                + "selected-violation"
                              )
                            : (
                                "expert-value-button"
                              )
                        }
                        onClick={() =>
                          setValues(
                            (current) => ({
                              ...current,
                              [
                                criterion
                                  .code
                              ]:
                                "VIOLATION",
                            }),
                          )
                        }
                      >
                        Есть нарушение
                      </button>

                      <button
                        type="button"
                        className={
                          value
                          === "CANNOT_ASSESS"
                            ? (
                                "expert-value-button "
                                + "selected-unknown"
                              )
                            : (
                                "expert-value-button"
                              )
                        }
                        onClick={() =>
                          setValues(
                            (current) => ({
                              ...current,
                              [
                                criterion
                                  .code
                              ]:
                                "CANNOT_ASSESS",
                            }),
                          )
                        }
                      >
                        Не могу оценить
                      </button>
                    </div>

                    {value
                      !== "CANNOT_ASSESS"
                      && (
                        <div
                          className={
                            "expert-confidence"
                          }
                        >
                          <span>
                            Уверенность
                          </span>

                          <div
                            className={
                              "expert-confidence-buttons"
                            }
                          >
                            {(
                              [
                                1,
                                2,
                                3,
                                4,
                                5,
                              ] as Confidence[]
                            ).map(
                              (score) => (
                                <button
                                  type="button"
                                  key={score}
                                  className={
                                    confidence[
                                      criterion
                                        .code
                                    ] === score
                                      ? (
                                          "expert-confidence-button "
                                          + "active"
                                        )
                                      : (
                                          "expert-confidence-button"
                                        )
                                  }
                                  onClick={() =>
                                    setConfidence(
                                      (
                                        current,
                                      ) => ({
                                        ...current,
                                        [
                                          criterion
                                            .code
                                        ]:
                                          score,
                                      }),
                                    )
                                  }
                                >
                                  {score}
                                </button>
                              ),
                            )}
                          </div>
                        </div>
                      )}

                    <textarea
                      className={
                        "expert-comment"
                      }
                      value={
                        comments[
                          criterion.code
                        ]
                      }
                      maxLength={2000}
                      placeholder={
                        "Комментарий "
                        + "(необязательно)"
                      }
                      onChange={(event) =>
                        setComments(
                          (current) => ({
                            ...current,
                            [
                              criterion
                                .code
                            ]:
                              event
                                .target
                                .value,
                          }),
                        )
                      }
                    />
                  </article>
                );
              },
            )}
          </div>
        </section>

        <section
          className={
            "expert-section"
          }
        >
          <h3>
            Общий комментарий
          </h3>

          <textarea
            className={
              "expert-comment "
              + "expert-comment-large"
            }
            value={
              generalComment
            }
            maxLength={2000}
            placeholder={
              "Дополнительные наблюдения "
              + "эксперта"
            }
            onChange={(event) =>
              setGeneralComment(
                event.target.value,
              )
            }
          />
        </section>

        {error && (
          <div
            className={
              "expert-message error"
            }
          >
            {error}
          </div>
        )}

        {success && (
          <div
            className={
              "expert-message success"
            }
          >
            {success}
          </div>
        )}

        <div
          className={
            "expert-submit-bar"
          }
        >
          <div className="muted">
            После сохранения создаётся
            отдельная экспертная
            annotation.
          </div>

          <button
            className="button"
            type="button"
            disabled={
              submitting
              || Boolean(success)
              || !canSubmit
            }
            onClick={submit}
          >
            {submitting
              ? "Сохраняем…"
              : (
                  success
                    ? "Оценка сохранена"
                    : "Завершить оценку"
                )}
          </button>
        </div>
      </aside>
    </div>
  );
}
