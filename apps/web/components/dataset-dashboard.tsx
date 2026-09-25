"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";


type ReviewState =
  | "LEGACY"
  | "NOT_ANNOTATED"
  | "ANNOTATED"
  | "CONSENSUS_DRAFT"
  | "APPROVED";


interface Summary {
  total_studies: number;

  privacy_ready: number;
  legacy: number;

  not_annotated: number;
  annotated: number;
  consensus_draft: number;
  approved: number;

  eligible_for_dataset: number;
}


interface DatasetItem {
  id: string;

  study_status: string;

  modality: string | null;
  created_at: string;

  privacy_group_id:
    | string
    | null;

  privacy_ready: boolean;

  review_state: ReviewState;

  annotation_count: number;
  consensus_count: number;
  draft_consensus_count: number;

  approved_consensus_id:
    | string
    | null;

  eligible_for_dataset:
    boolean;
}


interface ResponseData {
  summary: Summary;

  items: DatasetItem[];

  total: number;
  limit: number;
  offset: number;

  state_filter:
    | ReviewState
    | null;
}


type Filter =
  | "ALL"
  | ReviewState;


const FILTERS: {
  value: Filter;
  label: string;
}[] = [
  {
    value: "ALL",
    label: "Все",
  },
  {
    value: "NOT_ANNOTATED",
    label: "Без разметки",
  },
  {
    value: "ANNOTATED",
    label: "Размечено",
  },
  {
    value: "CONSENSUS_DRAFT",
    label: "Consensus draft",
  },
  {
    value: "APPROVED",
    label: "Approved",
  },
  {
    value: "LEGACY",
    label: "Legacy",
  },
];


function stateLabel(
  state: ReviewState,
): string {
  switch (state) {
    case "LEGACY":
      return "Legacy";

    case "NOT_ANNOTATED":
      return "Без разметки";

    case "ANNOTATED":
      return "Размечено";

    case "CONSENSUS_DRAFT":
      return "Consensus draft";

    case "APPROVED":
      return "Approved";
  }
}


function stateClass(
  state: ReviewState,
): string {
  return (
    "dataset-state "
    + "dataset-state-"
    + state
      .toLowerCase()
      .replaceAll(
        "_",
        "-",
      )
  );
}


function shortGroup(
  value: string | null,
): string {
  if (!value) {
    return "—";
  }

  if (value.length <= 18) {
    return value;
  }

  return (
    value.slice(0, 12)
    + "…"
    + value.slice(-6)
  );
}


function countForFilter(
  summary: Summary,
  filter: Filter,
): number {
  switch (filter) {
    case "ALL":
      return summary.total_studies;

    case "LEGACY":
      return summary.legacy;

    case "NOT_ANNOTATED":
      return summary.not_annotated;

    case "ANNOTATED":
      return summary.annotated;

    case "CONSENSUS_DRAFT":
      return summary.consensus_draft;

    case "APPROVED":
      return summary.approved;
  }
}


export function DatasetDashboard() {
  const [
    filter,
    setFilter,
  ] = useState<Filter>("ALL");

  const [
    data,
    setData,
  ] = useState<
    ResponseData | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");


  const load = useCallback(
    async () => {
      setLoading(true);
      setError("");

      const params =
        new URLSearchParams({
          limit: "500",
          offset: "0",
        });

      if (filter !== "ALL") {
        params.set(
          "state",
          filter,
        );
      }

      try {
        const response =
          await fetch(
            "/api/backend/dataset/readiness?"
            + params.toString(),
            {
              cache: "no-store",
            },
          );

        let payload: any = null;

        try {
          payload =
            await response.json();
        } catch {
          payload = null;
        }

        if (!response.ok) {
          throw new Error(
            payload?.detail?.code
            ?? `HTTP ${response.status}`,
          );
        }

        setData(
          payload as ResponseData,
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
    [filter],
  );


  useEffect(() => {
    void load();
  }, [load]);


  return (
    <div className="stack">
      <div>
        <h1 className="page-title">
          Датасет
        </h1>

        <div className="muted">
          Готовность исследований
          к включению в обучающий
          набор BoneQC.
        </div>
      </div>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {data && (
        <section className="dataset-metrics">
          <div className="card dataset-metric">
            <div className="muted">
              Всего исследований
            </div>

            <div className="metric">
              {
                data.summary
                  .total_studies
              }
            </div>
          </div>

          <div className="card dataset-metric">
            <div className="muted">
              Privacy-ready
            </div>

            <div className="metric">
              {
                data.summary
                  .privacy_ready
              }
            </div>
          </div>

          <div className="card dataset-metric">
            <div className="muted">
              Размечено
            </div>

            <div className="metric">
              {
                data.summary
                  .annotated
              }
            </div>
          </div>

          <div className="card dataset-metric">
            <div className="muted">
              Consensus draft
            </div>

            <div className="metric">
              {
                data.summary
                  .consensus_draft
              }
            </div>
          </div>

          <div className="card dataset-metric">
            <div className="muted">
              Approved
            </div>

            <div className="metric">
              {
                data.summary
                  .approved
              }
            </div>
          </div>

          <div className="card dataset-metric">
            <div className="muted">
              Legacy
            </div>

            <div className="metric">
              {
                data.summary
                  .legacy
              }
            </div>
          </div>
        </section>
      )}

      {data && (
        <section className="card stack">
          <div>
            <h2>
              Пул исследований
            </h2>

            <div className="muted">
              В ML dataset допускаются
              только privacy-ready
              исследования с
              APPROVED consensus.
            </div>
          </div>

          <div className="dataset-filters">
            {FILTERS.map(
              (item) => (
                <button
                  className={
                    filter
                    === item.value
                      ? (
                          "dataset-filter "
                          + "dataset-filter-active"
                        )
                      : "dataset-filter"
                  }
                  key={item.value}
                  type="button"
                  onClick={() =>
                    setFilter(
                      item.value,
                    )
                  }
                >
                  {item.label}

                  <span>
                    {
                      countForFilter(
                        data.summary,
                        item.value,
                      )
                    }
                  </span>
                </button>
              ),
            )}
          </div>

          {loading && (
            <div className="muted">
              Обновление...
            </div>
          )}

          {!loading
            && data.items.length
            === 0 && (
              <div className="muted">
                В этой категории
                исследований нет.
              </div>
            )}

          <div className="dataset-table">
            {!loading
              && data.items.map(
                (item) => (
                  <Link
                    className="dataset-row"
                    href={
                      `/studies/${item.id}`
                    }
                    key={item.id}
                  >
                    <div className="dataset-main">
                      <div>
                        <strong>
                          {
                            item.modality
                            ?? "DICOM"
                          }
                        </strong>

                        <div className="muted small dataset-id">
                          {item.id}
                        </div>
                      </div>

                      <span
                        className={
                          stateClass(
                            item.review_state,
                          )
                        }
                      >
                        {
                          stateLabel(
                            item.review_state,
                          )
                        }
                      </span>
                    </div>

                    <div className="dataset-row-metrics">
                      <div>
                        <span className="muted small">
                          Разметки
                        </span>

                        <strong>
                          {
                            item
                              .annotation_count
                          }
                        </strong>
                      </div>

                      <div>
                        <span className="muted small">
                          Consensus
                        </span>

                        <strong>
                          {
                            item
                              .consensus_count
                          }
                        </strong>
                      </div>

                      <div>
                        <span className="muted small">
                          Privacy group
                        </span>

                        <strong
                          className="dataset-group"
                          title={
                            item
                              .privacy_group_id
                            ?? "Нет"
                          }
                        >
                          {
                            shortGroup(
                              item
                                .privacy_group_id,
                            )
                          }
                        </strong>
                      </div>

                      <div>
                        <span className="muted small">
                          Dataset
                        </span>

                        <strong>
                          {
                            item
                              .eligible_for_dataset
                              ? "READY"
                              : "NO"
                          }
                        </strong>
                      </div>
                    </div>

                    <div className="muted small">
                      Загружено:{" "}
                      {new Date(
                        item.created_at,
                      ).toLocaleString(
                        "ru-RU",
                      )}
                    </div>
                  </Link>
                ),
              )}
          </div>
        </section>
      )}

      {!data && loading && (
        <section className="card">
          <div className="muted">
            Загрузка состояния
            датасета...
          </div>
        </section>
      )}
    </div>
  );
}
