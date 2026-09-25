"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";


type Role =
  | "ADMIN"
  | "DOCTOR"
  | "OPERATOR";


interface ClinicalLabel {
  code: string;
  assessable: boolean;
  class_label: string | null;
  confidence: number | null;
}


interface Annotation {
  id: string;
  study_id: string;
  reviewer_user_id: string | null;
  schema_version: string;
  labels: ClinicalLabel[];
  created_at: string;
}


interface Consensus {
  id: string;
  study_id: string;

  created_by_user_id:
    | string
    | null;

  reviewed_by_user_id:
    | string
    | null;

  schema_version: string;

  status:
    | "DRAFT"
    | "APPROVED"
    | "REJECTED";

  source_annotation_ids: string[];

  labels: ClinicalLabel[];

  reviewed_at:
    | string
    | null;

  created_at: string;
}


interface AnnotationList {
  items: Annotation[];
  total: number;
}


interface ConsensusList {
  items: Consensus[];
  total: number;
}


interface Props {
  studyId: string;
  currentRole: Role;
}


const DEFAULT_LABELS:
  ClinicalLabel[] = [
    {
      code: "POSITIONING",
      assessable: true,
      class_label:
        "PROVISIONAL_REVIEW",
      confidence: 0.9,
    },
    {
      code: "ROI_PLACEMENT",
      assessable: true,
      class_label:
        "PROVISIONAL_REVIEW",
      confidence: 0.9,
    },
    {
      code: "ARTIFACTS",
      assessable: true,
      class_label:
        "PROVISIONAL_REVIEW",
      confidence: 0.9,
    },
  ];


function freshLabels():
  ClinicalLabel[] {
  return DEFAULT_LABELS.map(
    (item) => ({
      ...item,
    }),
  );
}


function shortId(
  value: string | null,
): string {
  if (!value) {
    return "—";
  }

  return (
    value.slice(0, 8)
    + "…"
  );
}


async function parseResponse(
  response: Response,
) {
  let data: any = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

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

    throw new Error(message);
  }

  return data;
}


function LabelEditor({
  labels,
  onChange,
}: {
  labels: ClinicalLabel[];
  onChange: (
    labels: ClinicalLabel[],
  ) => void;
}) {
  function update(
    index: number,
    patch: Partial<
      ClinicalLabel
    >,
  ) {
    const next = labels.map(
      (item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              ...patch,
            }
          : item,
    );

    onChange(next);
  }


  return (
    <div className="review-labels">
      {labels.map(
        (label, index) => (
          <div
            className="review-label-row"
            key={label.code}
          >
            <div>
              <strong>
                {label.code}
              </strong>

              <div className="muted small">
                Временная техническая
                категория
              </div>
            </div>

            <label className="review-check">
              <input
                type="checkbox"
                checked={
                  label.assessable
                }
                onChange={(event) => {
                  const assessable =
                    event.target.checked;

                  update(
                    index,
                    {
                      assessable,
                      class_label:
                        assessable
                          ? (
                              label.class_label
                              ?? "PROVISIONAL_REVIEW"
                            )
                          : null,
                    },
                  );
                }}
              />

              Можно оценить
            </label>

            <select
              className="input"
              disabled={
                !label.assessable
              }
              value={
                label.class_label
                ?? ""
              }
              onChange={(event) =>
                update(
                  index,
                  {
                    class_label:
                      event.target.value,
                  },
                )
              }
            >
              <option
                value={
                  "PROVISIONAL_ACCEPTABLE"
                }
              >
                PROVISIONAL_ACCEPTABLE
              </option>

              <option
                value={
                  "PROVISIONAL_REVIEW"
                }
              >
                PROVISIONAL_REVIEW
              </option>

              <option
                value={
                  "PROVISIONAL_FAIL"
                }
              >
                PROVISIONAL_FAIL
              </option>
            </select>

            <label className="label">
              Уверенность

              <input
                className="input"
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={
                  label.confidence
                  ?? ""
                }
                onChange={(event) =>
                  update(
                    index,
                    {
                      confidence:
                        event.target.value
                        === ""
                          ? null
                          : Number(
                              event
                                .target
                                .value,
                            ),
                    },
                  )
                }
              />
            </label>
          </div>
        ),
      )}
    </div>
  );
}


export function ClinicalReviewPanel({
  studyId,
  currentRole,
}: Props) {
  const [
    annotations,
    setAnnotations,
  ] = useState<Annotation[]>([]);

  const [
    consensus,
    setConsensus,
  ] = useState<Consensus[]>([]);

  const [
    annotationLabels,
    setAnnotationLabels,
  ] = useState<
    ClinicalLabel[]
  >(freshLabels);

  const [
    consensusLabels,
    setConsensusLabels,
  ] = useState<
    ClinicalLabel[]
  >(freshLabels);

  const [
    selectedAnnotations,
    setSelectedAnnotations,
  ] = useState<string[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    submitting,
    setSubmitting,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    message,
    setMessage,
  ] = useState("");


  const loadData = useCallback(
    async () => {
      setLoading(true);
      setError("");

      try {
        const [
          annotationResponse,
          consensusResponse,
        ] = await Promise.all([
          fetch(
            `/api/backend/studies/${studyId}/annotations`,
            {
              cache: "no-store",
            },
          ),
          fetch(
            `/api/backend/studies/${studyId}/consensus`,
            {
              cache: "no-store",
            },
          ),
        ]);

        const annotationData:
          AnnotationList =
          await parseResponse(
            annotationResponse,
          );

        const consensusData:
          ConsensusList =
          await parseResponse(
            consensusResponse,
          );

        setAnnotations(
          annotationData.items,
        );

        setConsensus(
          consensusData.items,
        );
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : String(reason),
        );
      } finally {
        setLoading(false);
      }
    },
    [studyId],
  );


  useEffect(() => {
    void loadData();
  }, [loadData]);


  async function createAnnotation() {
    setSubmitting(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `/api/backend/studies/${studyId}/annotations`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            schema_version: "0.1",
            labels:
              annotationLabels,
          }),
        },
      );

      await parseResponse(response);

      setMessage(
        "Разметка сохранена.",
      );

      setAnnotationLabels(
        freshLabels(),
      );

      await loadData();
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


  function toggleAnnotation(
    annotationId: string,
  ) {
    setSelectedAnnotations(
      (current) =>
        current.includes(
          annotationId,
        )
          ? current.filter(
              (item) =>
                item
                !== annotationId,
            )
          : [
              ...current,
              annotationId,
            ],
    );
  }


  async function createConsensus() {
    if (
      selectedAnnotations.length
      < 2
    ) {
      setError(
        "Для consensus нужны "
        + "минимум две независимые "
        + "разметки.",
      );

      return;
    }

    setSubmitting(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `/api/backend/studies/${studyId}/consensus`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            schema_version: "0.1",
            source_annotation_ids:
              selectedAnnotations,
            labels:
              consensusLabels,
          }),
        },
      );

      await parseResponse(response);

      setMessage(
        "Consensus создан "
        + "в статусе DRAFT.",
      );

      setSelectedAnnotations(
        [],
      );

      setConsensusLabels(
        freshLabels(),
      );

      await loadData();
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


  async function reviewConsensus(
    consensusId: string,
    action:
      | "approve"
      | "reject",
  ) {
    setSubmitting(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `/api/backend/studies/${studyId}/consensus/${consensusId}/${action}`,
        {
          method: "POST",
        },
      );

      const result =
        await parseResponse(
          response,
        );

      setMessage(
        result.status
        === "APPROVED"
          ? "Consensus утверждён."
          : "Consensus отклонён.",
      );

      await loadData();
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


  if (
    currentRole !== "ADMIN"
    && currentRole
      !== "DOCTOR"
  ) {
    return null;
  }


  return (
    <section className="card stack">
      <div>
        <h2>
          Клиническая разметка
        </h2>

        <p className="muted">
          Сейчас используются
          временные технические
          категории schema 0.1.
          Они не являются
          утверждёнными клиническими
          критериями.
        </p>
      </div>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {message && (
        <div className="success">
          {message}
        </div>
      )}

      {loading ? (
        <div className="muted">
          Загрузка разметки...
        </div>
      ) : (
        <>
          <div className="review-section">
            <div>
              <h3>
                Независимые разметки
              </h3>

              <div className="muted">
                Всего:{" "}
                {annotations.length}
              </div>
            </div>

            {annotations.length
              === 0 && (
              <div className="muted">
                Разметок пока нет.
              </div>
            )}

            <div className="review-list">
              {annotations.map(
                (annotation) => (
                  <label
                    className="review-item"
                    key={
                      annotation.id
                    }
                  >
                    <input
                      type="checkbox"
                      checked={
                        selectedAnnotations
                        .includes(
                          annotation.id,
                        )
                      }
                      onChange={() =>
                        toggleAnnotation(
                          annotation.id,
                        )
                      }
                    />

                    <div>
                      <strong>
                        Annotation{" "}
                        {shortId(
                          annotation.id,
                        )}
                      </strong>

                      <div className="muted small">
                        Reviewer:{" "}
                        {shortId(
                          annotation
                            .reviewer_user_id,
                        )}
                        {" · "}
                        {
                          annotation
                            .schema_version
                        }
                        {" · "}
                        {new Date(
                          annotation
                            .created_at,
                        )
                          .toLocaleString(
                            "ru-RU",
                          )}
                      </div>

                      <div className="review-tags">
                        {annotation.labels
                          .map(
                            (label) => (
                              <span
                                className="status"
                                key={
                                  label.code
                                }
                              >
                                {
                                  label.code
                                }
                                :
                                {" "}
                                {
                                  label
                                    .assessable
                                    ? (
                                        label
                                          .class_label
                                        ?? "—"
                                      )
                                    : "CANNOT_ASSESS"
                                }
                              </span>
                            ),
                          )}
                      </div>
                    </div>
                  </label>
                ),
              )}
            </div>
          </div>

          <div className="review-section">
            <h3>
              Добавить свою разметку
            </h3>

            <LabelEditor
              labels={
                annotationLabels
              }
              onChange={
                setAnnotationLabels
              }
            />

            <div className="actions">
              <button
                className="button"
                disabled={
                  submitting
                }
                onClick={
                  createAnnotation
                }
              >
                Сохранить разметку
              </button>
            </div>
          </div>

          <div className="review-section">
            <div>
              <h3>
                Создать consensus
              </h3>

              <div className="muted">
                Выбрано разметок:{" "}
                {
                  selectedAnnotations
                    .length
                }.
                Нужно минимум две
                разметки разных
                reviewers.
              </div>
            </div>

            <LabelEditor
              labels={
                consensusLabels
              }
              onChange={
                setConsensusLabels
              }
            />

            <div className="actions">
              <button
                className="button"
                disabled={
                  submitting
                  || selectedAnnotations
                    .length < 2
                }
                onClick={
                  createConsensus
                }
              >
                Создать DRAFT
              </button>
            </div>
          </div>

          <div className="review-section">
            <div>
              <h3>
                Consensus
              </h3>

              <div className="muted">
                Всего:{" "}
                {consensus.length}
              </div>
            </div>

            {consensus.length === 0
              && (
                <div className="muted">
                  Consensus пока нет.
                </div>
              )}

            <div className="review-list">
              {consensus.map(
                (item) => (
                  <div
                    className="review-item consensus-item"
                    key={item.id}
                  >
                    <div className="review-item-main">
                      <div>
                        <strong>
                          Consensus{" "}
                          {shortId(
                            item.id,
                          )}
                        </strong>

                        <div className="muted small">
                          Creator:{" "}
                          {shortId(
                            item
                              .created_by_user_id,
                          )}
                          {" · "}
                          Sources:{" "}
                          {
                            item
                              .source_annotation_ids
                              .length
                          }
                        </div>
                      </div>

                      <span
                        className={
                          "status "
                          + (
                            item.status
                            === "APPROVED"
                              ? "status-approved"
                              : (
                                  item.status
                                  === "REJECTED"
                                    ? "status-rejected"
                                    : ""
                                )
                          )
                        }
                      >
                        {item.status}
                      </span>
                    </div>

                    <div className="review-tags">
                      {item.labels.map(
                        (label) => (
                          <span
                            className="status"
                            key={
                              label.code
                            }
                          >
                            {
                              label.code
                            }
                            :
                            {" "}
                            {
                              label
                                .assessable
                                ? (
                                    label
                                      .class_label
                                    ?? "—"
                                  )
                                : "CANNOT_ASSESS"
                            }
                          </span>
                        ),
                      )}
                    </div>

                    {item.status
                      === "DRAFT" && (
                      <div className="actions">
                        <button
                          className="button"
                          disabled={
                            submitting
                          }
                          onClick={() =>
                            reviewConsensus(
                              item.id,
                              "approve",
                            )
                          }
                        >
                          Утвердить
                        </button>

                        <button
                          className="button danger"
                          disabled={
                            submitting
                          }
                          onClick={() =>
                            reviewConsensus(
                              item.id,
                              "reject",
                            )
                          }
                        >
                          Отклонить
                        </button>
                      </div>
                    )}

                    {item.reviewed_at
                      && (
                        <div className="muted small">
                          Рассмотрен:{" "}
                          {new Date(
                            item
                              .reviewed_at,
                          )
                            .toLocaleString(
                              "ru-RU",
                            )}
                        </div>
                      )}
                  </div>
                ),
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
