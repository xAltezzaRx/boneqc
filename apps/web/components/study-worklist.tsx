"use client";

import Link from "next/link";
import {
  useEffect,
  useMemo,
  useState,
} from "react";


type UserRole =
  | "ADMIN"
  | "DOCTOR"
  | "OPERATOR";


type WorkState =
  | "WAITING"
  | "PROCESSING"
  | "REVIEW"
  | "PASS"
  | "FAIL"
  | "CANNOT_ASSESS"
  | "ERROR"
  | "EXPERT_PENDING"
  | "EXPERT_DONE";


type Filter =
  | "ALL"
  | "REVIEW"
  | "PROCESSING"
  | "COMPLETED"
  | "ERROR";


interface Study {
  id: string;
  status: string;

  original_filename: string;

  dicom_metadata: {
    modality?: string | null;
    rows?: number | null;
    columns?: number | null;
  };

  created_at: string;
}


interface StudyList {
  items: Study[];
  total: number;
  limit: number;
  offset: number;
}


interface WorkItem {
  study: Study;
  state: WorkState;
}


interface Props {
  currentRole: UserRole;
}


function shortId(
  value: string,
): string {
  return value.slice(0, 8);
}


function isTechnicalStudy(
  study: Study,
): boolean {
  const filename =
    study.original_filename
      .toLowerCase();

  const metadata =
    study.dicom_metadata as Record<
      string,
      unknown
    >;

  return (
    metadata?.test === true
    || filename.includes("test")
  );
}


function workPriority(
  state: WorkState,
): number {
  switch (state) {
    case "REVIEW":
    case "CANNOT_ASSESS":
    case "EXPERT_PENDING":
      return 0;

    case "ERROR":
      return 1;

    case "PROCESSING":
      return 2;

    case "WAITING":
      return 3;

    case "FAIL":
      return 4;

    case "PASS":
    case "EXPERT_DONE":
      return 5;
  }
}


function deriveState(
  study: Study,
  payload: any,
): WorkState {
  const resultStatus =
    payload?.result?.status
    ?? payload?.final_decision
    ?? payload?.decision
    ?? null;

  if (
    resultStatus === "PASS"
    || resultStatus === "REVIEW"
    || resultStatus === "FAIL"
    || resultStatus
      === "CANNOT_ASSESS"
  ) {
    return resultStatus;
  }

  const analysisStatus =
    payload?.qc_analysis?.status
    ?? payload?.analysis?.status
    ?? null;

  const jobStatus =
    payload?.job?.status
    ?? null;

  if (
    analysisStatus === "FAILED"
    || jobStatus === "FAILED"
    || study.status === "FAILED"
  ) {
    return "ERROR";
  }

  if (
    analysisStatus
    === "REVIEW_REQUIRED"
  ) {
    return "REVIEW";
  }

  if (
    analysisStatus === "CREATED"
    || analysisStatus === "QUEUED"
    || analysisStatus === "RUNNING"
    || jobStatus === "QUEUED"
    || jobStatus === "PREPROCESSING"
    || jobStatus === "ANALYZING"
    || jobStatus
      === "POSTPROCESSING"
  ) {
    return "PROCESSING";
  }

  return "WAITING";
}


function stateLabel(
  state: WorkState,
): string {
  switch (state) {
    case "EXPERT_PENDING":
      return "Требует экспертной оценки";

    case "EXPERT_DONE":
      return "Моя оценка сохранена";

    case "WAITING":
      return "Ожидает анализа";

    case "PROCESSING":
      return "Анализируется";

    case "REVIEW":
      return "Требует проверки";

    case "PASS":
      return "Качество соответствует";

    case "FAIL":
      return "Нарушения качества";

    case "CANNOT_ASSESS":
      return "Невозможно оценить";

    case "ERROR":
      return "Ошибка анализа";
  }
}


function stateClass(
  state: WorkState,
): string {
  if (state === "EXPERT_PENDING") {
    return (
      "work-state "
      + "work-state-review"
    );
  }

  if (state === "EXPERT_DONE") {
    return (
      "work-state "
      + "work-state-pass"
    );
  }

  return (
    "work-state work-state-"
    + state
      .toLowerCase()
      .replaceAll("_", "-")
  );
}


function matchesFilter(
  state: WorkState,
  filter: Filter,
): boolean {
  switch (filter) {
    case "ALL":
      return true;

    case "REVIEW":
      return (
        state === "REVIEW"
        || state
          === "CANNOT_ASSESS"
        || state
          === "EXPERT_PENDING"
      );

    case "PROCESSING":
      return (
        state === "PROCESSING"
      );

    case "COMPLETED":
      return (
        state === "PASS"
        || state === "FAIL"
        || state
          === "EXPERT_DONE"
      );

    case "ERROR":
      return state === "ERROR";
  }
}


function formatDate(
  value: string,
): string {
  return new Date(
    value,
  ).toLocaleDateString(
    "ru-RU",
    {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    },
  );
}


function formatTime(
  value: string,
): string {
  return new Date(
    value,
  ).toLocaleTimeString(
    "ru-RU",
    {
      hour: "2-digit",
      minute: "2-digit",
    },
  );
}


export function StudyWorklist({
  currentRole,
}: Props) {
  const [
    items,
    setItems,
  ] = useState<WorkItem[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  const [
    filter,
    setFilter,
  ] = useState<Filter>("ALL");

  const [
    search,
    setSearch,
  ] = useState("");


  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response =
          await fetch(
            "/api/backend/studies"
            + "?limit=100&offset=0",
            {
              cache: "no-store",
            },
          );

        if (!response.ok) {
          throw new Error(
            `HTTP ${response.status}`,
          );
        }

        const data:
          StudyList =
          await response.json();

        const prepared =
          await Promise.all(
            data.items.map(
              async (study) => {
                if (
                  currentRole
                  === "DOCTOR"
                ) {
                  try {
                    const statusResponse =
                      await fetch(
                        "/api/backend/studies/"
                        + study.id
                        + "/my-annotation-status",
                        {
                          cache:
                            "no-store",
                        },
                      );

                    if (
                      !statusResponse.ok
                    ) {
                      return {
                        study,
                        state:
                          ("ERROR" as WorkState),
                      };
                    }

                    const statusPayload:
                      {
                        reviewed:
                          boolean;
                      } =
                      await statusResponse
                        .json();

                    return {
                      study,
                      state:
                        (
                          statusPayload
                            .reviewed
                            ? "EXPERT_DONE"
                            : "EXPERT_PENDING"
                        ) as WorkState,
                    };
                  } catch {
                    return {
                      study,
                      state:
                        ("ERROR" as WorkState),
                    };
                  }
                }

                let result:
                  any = null;

                try {
                  const resultResponse =
                    await fetch(
                      "/api/backend/studies/"
                      + study.id
                      + "/result",
                      {
                        cache:
                          "no-store",
                      },
                    );

                  if (
                    resultResponse.ok
                  ) {
                    result =
                      await resultResponse
                        .json();
                  }
                } catch {
                  result = null;
                }

                return {
                  study,
                  state:
                    deriveState(
                      study,
                      result,
                    ),
                };
              },
            ),
          );

        if (!cancelled) {
          setItems(prepared);
        }
      } catch (reason) {
        if (!cancelled) {
          setError(
            reason instanceof Error
              ? reason.message
              : String(reason),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [
    currentRole,
  ]);


  const clinicalItems =
    useMemo(
      () =>
        items
          .filter(
            ({ study }) =>
              !isTechnicalStudy(
                study,
              ),
          )
          .sort(
            (left, right) => {
              const priority =
                workPriority(
                  left.state,
                )
                - workPriority(
                  right.state,
                );

              if (priority !== 0) {
                return priority;
              }

              return (
                new Date(
                  right.study
                    .created_at,
                ).getTime()
                - new Date(
                  left.study
                    .created_at,
                ).getTime()
              );
            },
          ),
      [items],
    );


  const hiddenTechnical =
    items.length
    - clinicalItems.length;


  const stats = useMemo(
    () => ({
      total:
        clinicalItems.length,

      review:
        clinicalItems.filter(
          ({ state }) =>
            state === "REVIEW"
            || state
              === "CANNOT_ASSESS"
            || state
              === "EXPERT_PENDING",
        ).length,

      processing:
        clinicalItems.filter(
          ({ state }) =>
            state === "PROCESSING",
        ).length,

      completed:
        clinicalItems.filter(
          ({ state }) =>
            state === "PASS"
            || state === "FAIL"
            || state
              === "EXPERT_DONE",
        ).length,
    }),
    [clinicalItems],
  );


  const visibleItems =
    useMemo(
      () => {
        const query =
          search
            .trim()
            .toLowerCase();

        return clinicalItems.filter(
          ({
            study,
            state,
          }) => {
            if (
              !matchesFilter(
                state,
                filter,
              )
            ) {
              return false;
            }

            if (!query) {
              return true;
            }

            const modality =
              study.dicom_metadata
                ?.modality
              ?? "";

            return (
              study.id
                .toLowerCase()
                .includes(query)
              || study
                .original_filename
                .toLowerCase()
                .includes(query)
              || modality
                .toLowerCase()
                .includes(query)
            );
          },
        );
      },
      [
        clinicalItems,
        filter,
        search,
      ],
    );


  const filters: Array<{
    value: Filter;
    label: string;
  }> = (
    currentRole === "DOCTOR"
      ? [
          {
            value: "ALL",
            label: "Все",
          },
          {
            value: "REVIEW",
            label: "Требуют оценки",
          },
          {
            value: "COMPLETED",
            label: "Оценены мной",
          },
          {
            value: "ERROR",
            label: "Ошибки",
          },
        ]
      : [
          {
            value: "ALL",
            label: "Все",
          },
          {
            value: "REVIEW",
            label: "Требуют проверки",
          },
          {
            value: "PROCESSING",
            label: "В работе",
          },
          {
            value: "COMPLETED",
            label: "Завершены",
          },
          {
            value: "ERROR",
            label: "Ошибки",
          },
        ]
  );


  return (
    <div className="clinical-worklist">
      <header className="worklist-heading">
        <div>
          <div className="page-eyebrow">
            {currentRole === "DOCTOR"
              ? "BONEQC EXPERT"
              : "QUALITY CONTROL"}
          </div>

          <h1 className="page-title">
            Исследования
          </h1>

          <p className="page-description">
            {currentRole === "DOCTOR"
              ? (
                  <>
                    Рабочий список исследований
                    для независимой экспертной
                    оценки.
                  </>
                )
              : (
                  <>
                    Рабочий список
                    денситометрических
                    исследований и результатов
                    контроля качества.
                  </>
                )}
          </p>
        </div>

        {(currentRole === "ADMIN"
          || currentRole
            === "OPERATOR") && (
          <Link
            className="button worklist-upload-button"
            href="/studies/new"
          >
            <span
              className="worklist-upload-plus"
              aria-hidden="true"
            >
              +
            </span>

            Загрузить DICOM
          </Link>
        )}
      </header>


      <section className="work-summary">
        <button
          className={
            filter === "REVIEW"
              ? (
                  "work-summary-item "
                  + "work-summary-review "
                  + "work-summary-active"
                )
              : (
                  "work-summary-item "
                  + "work-summary-review"
                )
          }
          type="button"
          onClick={() =>
            setFilter("REVIEW")
          }
        >
          <span className="work-summary-icon">
            !
          </span>

          <span className="work-summary-copy">
            <span>
              {currentRole === "DOCTOR"
                ? "Требуют оценки"
                : "Требуют проверки"}
            </span>

            <small>
              {currentRole === "DOCTOR"
                ? (
                    "Нужна независимая "
                    + "экспертная оценка"
                  )
                : "Нужна экспертная оценка"}
            </small>
          </span>

          <strong>
            {stats.review}
          </strong>
        </button>

        <button
          className={
            (
              currentRole === "DOCTOR"
                ? filter === "ALL"
                : filter === "PROCESSING"
            )
              ? (
                  "work-summary-item "
                  + "work-summary-processing "
                  + "work-summary-active"
                )
              : (
                  "work-summary-item "
                  + "work-summary-processing"
                )
          }
          type="button"
          onClick={() =>
            setFilter(
              currentRole === "DOCTOR"
                ? "ALL"
                : "PROCESSING",
            )
          }
        >
          <span className="work-summary-icon">
            ↻
          </span>

          <span className="work-summary-copy">
            <span>
              {currentRole === "DOCTOR"
                ? "Всего доступно"
                : "В работе"}
            </span>

            <small>
              {currentRole === "DOCTOR"
                ? (
                    "Исследования в "
                    + "экспертном списке"
                  )
                : "Выполняется AI-анализ"}
            </small>
          </span>

          <strong>
            {currentRole === "DOCTOR"
              ? stats.total
              : stats.processing}
          </strong>
        </button>

        <button
          className={
            filter === "COMPLETED"
              ? (
                  "work-summary-item "
                  + "work-summary-completed "
                  + "work-summary-active"
                )
              : (
                  "work-summary-item "
                  + "work-summary-completed"
                )
          }
          type="button"
          onClick={() =>
            setFilter(
              "COMPLETED",
            )
          }
        >
          <span className="work-summary-icon">
            ✓
          </span>

          <span className="work-summary-copy">
            <span>
              {currentRole === "DOCTOR"
                ? "Оценены мной"
                : "Завершены"}
            </span>

            <small>
              {currentRole === "DOCTOR"
                ? (
                    "Экспертная оценка "
                    + "сохранена"
                  )
                : "Получен QC-результат"}
            </small>
          </span>

          <strong>
            {stats.completed}
          </strong>
        </button>
      </section>


      <section className="worklist-panel">
        <div className="worklist-toolbar">
          <div className="work-search-shell">
            <span
              className="work-search-icon"
              aria-hidden="true"
            >
              ⌕
            </span>

            <input
              className="input work-search"
              type="search"
              placeholder={
                "Поиск по ID, имени файла или модальности"
              }
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value,
                )
              }
            />
          </div>

          <div className="work-filters">
            {filters.map(
              ({
                value,
                label,
              }) => (
                <button
                  className={
                    filter === value
                      ? (
                          "work-filter "
                          + "work-filter-active"
                        )
                      : "work-filter"
                  }
                  type="button"
                  key={value}
                  onClick={() =>
                    setFilter(
                      value,
                    )
                  }
                >
                  {label}
                </button>
              ),
            )}
          </div>

          <div className="worklist-meta">
            <span>
              Показано:
              {" "}
              <strong>
                {
                  visibleItems
                    .length
                }
              </strong>
            </span>

            {currentRole === "ADMIN"
              && hiddenTechnical > 0 && (
                <span>
                  Скрыто тестовых:
                  {" "}
                  <strong>
                    {
                      hiddenTechnical
                    }
                  </strong>
                </span>
              )}
          </div>
        </div>


        {error && (
          <div className="error worklist-message">
            Не удалось загрузить
            исследования:
            {" "}
            {error}
          </div>
        )}

        {loading && (
          <div className="worklist-loading">
            <span
              className="worklist-spinner"
              aria-hidden="true"
            />

            Загрузка исследований...
          </div>
        )}

        {!loading
          && visibleItems.length
            === 0 && (
            <div className="worklist-empty">
              <div className="worklist-empty-icon">
                DX
              </div>

              <strong>
                Исследований не найдено
              </strong>

              <span>
                Измените фильтр или
                строку поиска.
              </span>
            </div>
          )}


        {!loading
          && visibleItems.length
            > 0 && (
          <div className="worklist">
            {visibleItems.map(
              ({
                study,
                state,
              }) => {
                const modality =
                  study
                    .dicom_metadata
                    ?.modality
                  ?? "DICOM";

                return (
                  <Link
                    className="work-row"
                    href={
                      currentRole === "DOCTOR"
                        ? `/expert/${study.id}`
                        : `/studies/${study.id}`
                    }
                    key={study.id}
                  >
                    <div className="work-modality">
                      {modality}
                    </div>

                    <div className="work-study">
                      <strong>
                        Исследование{" "}
                        {shortId(
                          study.id,
                        )}
                      </strong>

                      <div className="work-study-meta">
                        <span>
                          {formatDate(
                            study.created_at,
                          )}
                        </span>

                        <span
                          aria-hidden="true"
                        >
                          ·
                        </span>

                        <span>
                          {formatTime(
                            study.created_at,
                          )}
                        </span>

                        <span
                          aria-hidden="true"
                        >
                          ·
                        </span>

                        <span>
                          {modality}
                        </span>
                      </div>
                    </div>

                    <span
                      className={
                        stateClass(
                          state,
                        )
                      }
                    >
                      <span
                        className="work-state-dot"
                        aria-hidden="true"
                      />

                      {stateLabel(
                        state,
                      )}
                    </span>

                    <span
                      className="work-open"
                      aria-hidden="true"
                    >
                      →
                    </span>
                  </Link>
                );
              },
            )}
          </div>
        )}
      </section>
    </div>
  );
}