"use client";

import Link from "next/link";
import {
  useRouter,
  useSearchParams,
} from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  ExpertReviewDrawer,
} from "@/components/expert-review-drawer";


type Role =
  | "ADMIN"
  | "DOCTOR"
  | "OPERATOR";


interface CurrentUser {
  id: string;
  username: string;
  role: Role;
}


interface Study {
  id: string;
  status: string;

  original_filename:
    string;

  source_object_key:
    string;

  preview_object_key:
    string | null;

  dicom_metadata:
    Record<string, unknown>;

  created_at: string;
  updated_at: string;
}


interface Job {
  id: string;
  study_id: string;

  qc_analysis_id:
    string | null;

  status: string;
  attempts: number;

  error_message:
    string | null;
}


interface QCAnalysis {
  id: string;
  status: string;

  decision:
    string | null;

  quality_score:
    number | null;
}


interface Observation {
  code: string;
  score: number | null;
  message: string;
  assessable: boolean;

  confidence:
    number | null;
}


interface Violation {
  code: string;
  score?: number | null;
  severity?: string | null;
  threshold?: number | null;
  message?: string | null;
}


interface ResultJson {
  observations?: Observation[];

  quality?: {
    status?: string;

    quality_score?:
      number | null;

    quality_prob?:
      number | null;

    quality_class?:
      number | null;

    anatomical_region?:
      string | null;

    violation_type?:
      string | null;

    violations?:
      Violation[];
  };

  c7_result?: {
    path_to_study?: string;
    study_uid?: string;
    image_uid?: string;

    anatomical_region?:
      string | null;

    quality_class?:
      number | null;

    violation_type?:
      string | null;

    quality_prob?:
      number | null;

    processing_status?:
      string | null;

    time_of_processing?:
      number | null;
  };

  uncertainty?: {
    decision?: string;

    mean_confidence?:
      number | null;

    minimum_confidence?:
      number | null;

    reasons?: string[];
  };

  final_decision?: {
    status?: string;
    reasons?: string[];
  };

  provider?: {
    name?: string;
    version?: string;
    summary?: string;
  };

  provider_metadata?: {
    clinical_use?: boolean;

    [key: string]:
      unknown;
  };
}


interface AnalysisResult {
  id: string;
  status: string;

  quality_score:
    number | null;

  model_version_id:
    string | null;

  result_json:
    ResultJson;
}


interface StudyResult {
  study: Study;

  qc_analysis:
    QCAnalysis | null;

  job:
    Job | null;

  result:
    AnalysisResult | null;

  model:
    {
      id?: string;
      name?: string;
      version?: string;
      status?: string;
    } | null;

  audit: unknown[];
}


interface Props {
  studyId: string;
}


function shortId(
  value: string,
): string {
  return value.slice(0, 8);
}


function percent(
  value:
    | number
    | null
    | undefined,
): string {
  if (
    value === null
    || value === undefined
  ) {
    return "—";
  }

  return (
    Math.round(value * 100)
    + "%"
  );
}


function decisionLabel(
  value:
    | string
    | null
    | undefined,
): string {
  switch (value) {
    case "PASS":
      return "Качество соответствует";

    case "REVIEW":
      return "Требует проверки";

    case "FAIL":
      return "Нарушения качества";

    case "CANNOT_ASSESS":
      return "Невозможно оценить";

    case "ERROR":
    case "FAILED":
      return "Ошибка анализа";

    case "PROCESSING":
      return "Анализируется";

    case "COMPLETED":
      return "Анализ завершён";

    default:
      return "Ожидает анализа";
  }
}


function decisionClass(
  value:
    | string
    | null
    | undefined,
): string {
  switch (value) {
    case "PASS":
      return "qc-pass";

    case "REVIEW":
      return "qc-review";

    case "FAIL":
      return "qc-fail";

    case "CANNOT_ASSESS":
      return "qc-neutral";

    case "ERROR":
    case "FAILED":
      return "qc-error";

    case "PROCESSING":
    case "COMPLETED":
      return "qc-processing";

    default:
      return "qc-neutral";
  }
}


function categoryTitle(
  code: string,
): string {
  switch (code) {
    case "POSITIONING":
      return "Позиционирование";

    case "ROI_PLACEMENT":
      return "ROI";

    case "ARTIFACTS":
      return "Артефакты";

    default:
      return code;
  }
}


function observationState(
  observation: Observation,
  violations: Violation[],
): string {
  if (!observation.assessable) {
    return "CANNOT_ASSESS";
  }

  const violation =
    violations.find(
      (item) =>
        item.code
        === observation.code,
    );

  if (
    violation?.severity
    === "FAIL"
  ) {
    return "FAIL";
  }

  if (
    violation?.severity
    === "REVIEW"
  ) {
    return "REVIEW";
  }

  return "PASS";
}


function analysisExplanation(
  decision: string | null,
  providerName:
    | string
    | null
    | undefined = null,
): string {
  switch (decision) {
    case "PASS":
      return (
        "Автоматическая проверка "
        + "не выявила технических "
        + "нарушений."
      );

    case "REVIEW":
      return (
        "Один или несколько "
        + "параметров требуют "
        + "экспертной проверки."
      );

    case "FAIL":
      return (
        "Обнаружены нарушения "
        + "технического качества."
      );

    case "CANNOT_ASSESS":
      if (
        providerName
        === "anatomy_guard"
      ) {
        return (
          "Анатомическая область "
          + "не поддерживается. BoneQC "
          + "выполняет автоматический "
          + "контроль исследований "
          + "поясничного отдела "
          + "позвоночника и "
          + "проксимального отдела бедра."
        );
      }

      if (
        providerName
        === "input_sanity_gate"
      ) {
        return (
          "Изображение не прошло "
          + "техническую проверку "
          + "входных данных. "
          + "Автоматический анализ "
          + "не выполнялся."
        );
      }

      return (
        "Недостаточно данных "
        + "для автоматической оценки."
      );

    case "ERROR":
    case "FAILED":
      return (
        "Автоматический анализ "
        + "не завершён из-за "
        + "технической ошибки."
      );

    case "PROCESSING":
      return (
        "Идёт автоматическая "
        + "проверка качества "
        + "исследования."
      );

    case "COMPLETED":
      return (
        "Автоматическая обработка "
        + "завершена."
      );

    default:
      return (
        "Автоматический контроль "
        + "качества ещё не выполнен."
      );
  }
}


export function StudyViewer({
  studyId,
}: Props) {
  const router =
    useRouter();

  const searchParams =
    useSearchParams();

  const initialJobId =
    searchParams.get("job");

  const [
    study,
    setStudy,
  ] = useState<Study | null>(
    null,
  );

  const [
    me,
    setMe,
  ] = useState<
    CurrentUser | null
  >(null);

  const [
    aggregate,
    setAggregate,
  ] = useState<
    StudyResult | null
  >(null);

  const [
    job,
    setJob,
  ] = useState<Job | null>(
    null,
  );

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    starting,
    setStarting,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    previewFailed,
    setPreviewFailed,
  ] = useState(false);

  const [
    previewLoaded,
    setPreviewLoaded,
  ] = useState(false);

  const [
    zoom,
    setZoom,
  ] = useState(1);

  const [
    reviewOpen,
    setReviewOpen,
  ] = useState(false);

  const viewerRef =
    useRef<HTMLDivElement | null>(
      null,
    );


  const loadResult =
    useCallback(
      async () => {
        const response =
          await fetch(
            `/api/backend/studies/${studyId}/result`,
            {
              cache: "no-store",
            },
          );

        if (!response.ok) {
          return;
        }

        const data:
          StudyResult =
          await response.json();

        setAggregate(data);
      },
      [studyId],
    );


  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [
          studyResponse,
          meResponse,
        ] = await Promise.all([
          fetch(
            `/api/backend/studies/${studyId}`,
            {
              cache: "no-store",
            },
          ),

          fetch(
            "/api/session/me",
            {
              cache: "no-store",
            },
          ),
        ]);

        if (!studyResponse.ok) {
          throw new Error(
            "Не удалось загрузить "
            + "исследование.",
          );
        }

        if (!meResponse.ok) {
          throw new Error(
            "Не удалось определить "
            + "текущего пользователя.",
          );
        }

        const [
          studyData,
          meData,
        ] = await Promise.all([
          studyResponse.json(),
          meResponse.json(),
        ]);

        if (!cancelled) {
          setStudy(studyData);
          setMe(meData);
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
  }, [studyId]);


  useEffect(() => {
    if (me?.role === "DOCTOR") {
      router.replace(
        `/expert/${studyId}`,
      );
    }
  }, [
    me,
    router,
    studyId,
  ]);


  useEffect(() => {
    if (
      me?.role === "ADMIN"
      || me?.role === "OPERATOR"
    ) {
      void loadResult();
    }
  }, [
    me,
    loadResult,
  ]);


  useEffect(() => {
    if (
      !initialJobId
      || job !== null
    ) {
      return;
    }

    let cancelled = false;

    async function loadInitialJob() {
      try {
        const response =
          await fetch(
            `/api/backend/jobs/${initialJobId}`,
            {
              cache: "no-store",
            },
          );

        if (
          response.ok
          && !cancelled
        ) {
          setJob(
            await response.json(),
          );
        }
      } catch {
        // Viewer remains usable even
        // if the transient job lookup
        // is unavailable.
      }
    }

    void loadInitialJob();

    return () => {
      cancelled = true;
    };
  }, [
    initialJobId,
    job,
  ]);


  useEffect(() => {
    if (!job) {
      return;
    }

    if (
      job.status === "COMPLETED"
      || job.status === "FAILED"
    ) {
      if (
        me?.role === "ADMIN"
        || me?.role === "OPERATOR"
      ) {
        void loadResult();
      }

      return;
    }

    const timer =
      window.setInterval(
        async () => {
          const response =
            await fetch(
              `/api/backend/jobs/${job.id}`,
              {
                cache:
                  "no-store",
              },
            );

          if (!response.ok) {
            return;
          }

          const nextJob:
            Job =
            await response.json();

          setJob(nextJob);
        },
        1200,
      );

    return () => {
      window.clearInterval(
        timer,
      );
    };
  }, [
    job,
    me,
    loadResult,
  ]);


  const result =
    aggregate?.result
    ?? null;

  const resultJson =
    result?.result_json
    ?? null;

  const observations =
    resultJson?.observations
    ?? [];

  const violations =
    resultJson
      ?.quality
      ?.violations
    ?? [];


  const decision =
    aggregate
      ?.qc_analysis
      ?.decision
    ?? result?.status
    ?? null;


  const qualityScore =
    aggregate
      ?.qc_analysis
      ?.quality_score
    ?? result
      ?.quality_score
    ?? resultJson
      ?.quality
      ?.quality_score
    ?? null;


  const activeJob =
    job
    ?? aggregate?.job
    ?? null;


  const activeJobRunning =
    activeJob !== null
    && ![
      "COMPLETED",
      "FAILED",
    ].includes(
      activeJob.status,
    );


  const displayState =
    useMemo(
      () => {
        if (
          activeJob?.status
          === "FAILED"
          || aggregate
            ?.qc_analysis
            ?.status
            === "FAILED"
        ) {
          return "ERROR";
        }

        if (decision) {
          return decision;
        }

        if (activeJobRunning) {
          return "PROCESSING";
        }

        if (
          activeJob?.status
          === "COMPLETED"
        ) {
          return "COMPLETED";
        }

        return null;
      },
      [
        activeJob,
        activeJobRunning,
        aggregate,
        decision,
      ],
    );


  const c7Quality =
    resultJson?.quality
    ?? null;

  const c7Native =
    resultJson?.c7_result
    ?? null;

  const isC7Result =
    resultJson?.provider?.name
    === "frozen_c7";

  const c7QualityProb =
    c7Quality?.quality_prob
    ?? c7Native?.quality_prob
    ?? null;

  const c7QualityClass =
    c7Quality?.quality_class
    ?? c7Native?.quality_class
    ?? null;

  const c7AnatomicalRegion =
    c7Quality?.anatomical_region
    ?? c7Native?.anatomical_region
    ?? null;

  const c7ViolationType =
    c7Quality?.violation_type
    ?? c7Native?.violation_type
    ?? null;

  const c7ViolationLabels =
    (
      c7Quality?.violations
      ?? []
    )
      .map(
        (violation) =>
          violation.message
          ?? violation.code,
      )
      .filter(
        (
          value,
          index,
          values,
        ) =>
          Boolean(value)
          && values.indexOf(value)
            === index,
      );

  const c7ProcessingStatus =
    c7Native?.processing_status
    ?? null;

  const runtimeImageValue =
    resultJson?.provider_metadata
      ?.runtime_image;

  const c7RuntimeImage =
    typeof runtimeImageValue
      === "string"
      ? runtimeImageValue
      : null;

  const c7ModelLabel =
    "BoneQC C7 · frozen";

  const demoMode =
    resultJson
      ?.provider_metadata
      ?.clinical_use
    !== true;


  const canAnalyze =
    me?.role === "ADMIN"
    || me?.role
      === "OPERATOR";


  const canReview =
    me?.role === "DOCTOR";


  async function analyze() {
    setStarting(true);
    setError("");

    try {
      const response =
        await fetch(
          `/api/backend/studies/${studyId}/analyze`,
          {
            method: "POST",
          },
        );

      let data: any = null;

      try {
        data =
          await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        const code =
          data?.detail?.code;

        throw new Error(
          code
          ?? `HTTP ${response.status}`,
        );
      }

      setAggregate(null);
      setJob(data);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : String(reason),
      );
    } finally {
      setStarting(false);
    }
  }


  async function fullscreen() {
    if (
      viewerRef.current
      && document.fullscreenElement
      === null
    ) {
      await viewerRef.current
        .requestFullscreen();
      return;
    }

    if (
      document.fullscreenElement
    ) {
      await document
        .exitFullscreen();
    }
  }


  if (loading) {
    return (
      <div className="muted">
        Загрузка исследования...
      </div>
    );
  }


  if (!study) {
    return (
      <div className="error">
        {error
          || "Исследование не найдено."}
      </div>
    );
  }


  const modality =
    typeof study
      .dicom_metadata
      ?.Modality === "string"
      ? String(
          study
            .dicom_metadata
            .Modality,
        )
      : (
          typeof study
            .dicom_metadata
            ?.modality === "string"
            ? String(
                study
                  .dicom_metadata
                  .modality,
              )
            : "DICOM"
        );


  return (
    <>
      <div className="study-viewer-page">
        <div className="study-viewer-heading">
          <div>
            <Link
              className="viewer-back"
              href="/studies"
            >
              ← Исследования
            </Link>

            <div className="page-eyebrow viewer-eyebrow">
              STUDY REVIEW
            </div>

            <div className="viewer-study-title">
              <h1>
                {modality}
                {" · "}
                Исследование{" "}
                {shortId(
                  study.id,
                )}
              </h1>

              <span className="muted">
                {new Date(
                  study.created_at,
                ).toLocaleString(
                  "ru-RU",
                )}
              </span>
            </div>
          </div>

          <span
            className={
              "viewer-decision-badge "
              + decisionClass(
                displayState,
              )
            }
          >
            {decisionLabel(
              displayState,
            )}
          </span>
        </div>


        {error && (
          <div className="error">
            {error}
          </div>
        )}


        {demoMode && (
          <div className="viewer-demo-warning">
            <strong>
              Демонстрационный режим.
            </strong>
            {" "}
            Результат предназначен
            только для исследовательской
            и демонстрационной проверки
            и не предназначен
            для медицинских решений.
          </div>
        )}


        <div className="viewer-layout">
          <section
            className="viewer-image-card"
            ref={viewerRef}
          >
            <div className="viewer-toolbar">
              <div>
                <strong>
                  Изображение
                </strong>

                <span className="muted small">
                  Оригинал
                </span>
              </div>

              <div className="viewer-tools">
                <button
                  className="viewer-tool"
                  type="button"
                  aria-label={
                    "Уменьшить"
                  }
                  onClick={() =>
                    setZoom(
                      (value) =>
                        Math.max(
                          0.5,
                          value - 0.1,
                        ),
                    )
                  }
                >
                  −
                </button>

                <button
                  className="viewer-tool viewer-tool-wide"
                  type="button"
                  onClick={() =>
                    setZoom(1)
                  }
                >
                  {Math.round(
                    zoom * 100,
                  )}
                  %
                </button>

                <button
                  className="viewer-tool"
                  type="button"
                  aria-label={
                    "Увеличить"
                  }
                  onClick={() =>
                    setZoom(
                      (value) =>
                        Math.min(
                          3,
                          value + 0.1,
                        ),
                    )
                  }
                >
                  +
                </button>

                <button
                  className="viewer-tool viewer-tool-wide"
                  type="button"
                  onClick={() =>
                    void fullscreen()
                  }
                >
                  ⛶
                </button>
              </div>
            </div>


            <div className="viewer-stage">
              {!previewFailed && (
                <img
                  className={
                    previewLoaded
                      ? (
                          "viewer-image "
                          + "viewer-image-loaded"
                        )
                      : "viewer-image"
                  }
                  src={
                    `/api/backend/studies/${studyId}/preview`
                  }
                  alt={
                    "Предпросмотр DICOM"
                  }
                  style={{
                    transform:
                      `scale(${zoom})`,
                  }}
                  onLoad={() =>
                    setPreviewLoaded(
                      true,
                    )
                  }
                  onError={() =>
                    setPreviewFailed(
                      true,
                    )
                  }
                />
              )}

              {!previewLoaded
                && !previewFailed && (
                <div className="viewer-placeholder">
                  <strong>
                    Загрузка изображения
                  </strong>

                  <span>
                    Получаем DICOM
                    preview…
                  </span>
                </div>
              )}

              {previewFailed && (
                <div className="viewer-placeholder">
                  <div className="viewer-placeholder-icon">
                    ◫
                  </div>

                  <strong>
                    Предпросмотр недоступен
                  </strong>

                  <span>
                    Для этого исследования
                    отсутствует доступный
                    preview-файл.
                  </span>
                </div>
              )}
            </div>


            <div className="viewer-layer-bar">
              <span className="viewer-layer-active">
                Оригинал
              </span>

              <span
                className="viewer-layer-muted"
                aria-disabled="true"
              >
                Дополнительные слои не предоставлены моделью
              </span>
            </div>
          </section>


          <aside className="viewer-qc-panel">
            <div className="viewer-qc-heading">
              <div>
                <span className="viewer-qc-kicker">
                  AUTOMATIC QC
                </span>

                <h2>
                  Контроль качества
                </h2>
              </div>

              <span
                className={
                  "viewer-qc-dot "
                  + decisionClass(
                    displayState,
                  )
                }
                aria-hidden="true"
              />
            </div>


            <div
              className={
                "viewer-qc-result "
                + decisionClass(
                  displayState,
                )
              }
            >
              <strong>
                {decisionLabel(
                  displayState,
                )}
              </strong>

              <span>
                {analysisExplanation(
                  displayState,
                  resultJson?.provider?.name,
                )}
              </span>
            </div>


            {isC7Result
              && decision
              && (
              <div className="viewer-c7-summary">
                <div className="viewer-c7-row">
                  <span>
                    Анатомическая область
                  </span>

                  <strong>
                    {c7AnatomicalRegion
                      ?? "—"}
                  </strong>
                </div>

                <div className="viewer-c7-row">
                  <span>
                    Вероятность нарушения
                  </span>

                  <strong>
                    {c7QualityProb !== null
                      ? (
                        c7QualityProb
                        * 100
                      ).toFixed(1)
                        + "%"
                      : "—"}
                  </strong>
                </div>

                <div className="viewer-c7-row">
                  <span>
                    Выявленные нарушения
                  </span>

                  {c7ViolationLabels.length > 0
                    ? (
                      <ul className="viewer-c7-violations">
                        {c7ViolationLabels.map(
                          (item) => (
                            <li key={item}>
                              {item}
                            </li>
                          ),
                        )}
                      </ul>
                    )
                    : (
                      <strong>
                        {c7QualityClass === 0
                          ? "Не выявлены"
                          : (
                            c7ViolationType
                            ?? "—"
                          )}
                      </strong>
                    )}
                </div>

                <div className="viewer-c7-row">
                  <span>
                    AI-модель
                  </span>

                  <strong>
                    {c7ModelLabel}
                  </strong>
                </div>

                <div className="viewer-c7-row">
                  <span>
                    C7 обработка
                  </span>

                  <strong>
                    {c7ProcessingStatus
                      === "Success"
                      ? "Завершено"
                      : (
                        c7ProcessingStatus
                        ?? "—"
                      )}
                  </strong>
                </div>

                {c7RuntimeImage && (
                  <div className="viewer-c7-runtime">
                    {c7RuntimeImage}
                  </div>
                )}
              </div>
            )}


            {activeJobRunning && (
              <div className="analysis-progress">
                <div className="analysis-progress-line">
                  <span
                    className={
                      activeJob
                        ?.status
                        === "PREPROCESSING"
                        || activeJob
                          ?.status
                          === "ANALYZING"
                        || activeJob
                          ?.status
                          === "POSTPROCESSING"
                        ? "done"
                        : ""
                    }
                  >
                    1
                  </span>

                  <div>
                    <strong>
                      Подготовка
                    </strong>

                    <small>
                      Проверка данных
                      исследования
                    </small>
                  </div>
                </div>

                <div className="analysis-progress-line">
                  <span
                    className={
                      activeJob
                        ?.status
                        === "ANALYZING"
                        || activeJob
                          ?.status
                          === "POSTPROCESSING"
                        ? "done"
                        : ""
                    }
                  >
                    2
                  </span>

                  <div>
                    <strong>
                      Анализ качества
                    </strong>

                    <small>
                      Обработка изображения
                    </small>
                  </div>
                </div>

                <div className="analysis-progress-line">
                  <span
                    className={
                      activeJob
                        ?.status
                        === "POSTPROCESSING"
                        ? "done"
                        : ""
                    }
                  >
                    3
                  </span>

                  <div>
                    <strong>
                      Результат
                    </strong>

                    <small>
                      Формирование оценки
                    </small>
                  </div>
                </div>
              </div>
            )}


            {observations.length > 0 && (
              <div className="qc-observations">
                {observations.map(
                  (observation) => {
                    const state =
                      observationState(
                        observation,
                        violations,
                      );

                    return (
                      <div
                        className="qc-observation"
                        key={
                          observation.code
                        }
                      >
                        <div>
                          <strong>
                            {categoryTitle(
                              observation.code,
                            )}
                          </strong>

                          <span
                            className={
                              "qc-observation-status "
                              + decisionClass(
                                state,
                              )
                            }
                          >
                            {decisionLabel(
                              state,
                            )}
                          </span>
                        </div>

                        <span className="qc-confidence">
                          {percent(
                            observation
                              .confidence,
                          )}
                        </span>
                      </div>
                    );
                  },
                )}
              </div>
            )}


            {qualityScore !== null && (
              <div className="qc-score">
                <span>
                  Итоговое качество
                </span>

                <strong>
                  {percent(
                    qualityScore,
                  )}
                </strong>
              </div>
            )}


            {activeJob?.status
              === "FAILED" && (
              <div className="viewer-error-state">
                <strong>
                  Анализ не выполнен
                </strong>

                <span>
                  Возникла техническая
                  ошибка обработки.
                </span>
              </div>
            )}


            {!activeJobRunning
              && !decision
              && activeJob?.status
                !== "FAILED" && (
              <div className="viewer-empty-result">
                Автоматический QC
                для исследования
                ещё не выполнен.
              </div>
            )}


            <div className="viewer-primary-actions">
              {canAnalyze
                && !activeJobRunning
                && !decision
                && activeJob?.status
                  !== "FAILED" && (
                <button
                  className="button"
                  type="button"
                  disabled={starting}
                  onClick={analyze}
                >
                  {starting
                    ? "Запуск..."
                    : "Проверить качество"}
                </button>
              )}

              {canAnalyze
                && activeJob?.status
                  === "FAILED" && (
                <button
                  className="button"
                  type="button"
                  disabled={starting}
                  onClick={analyze}
                >
                  {starting
                    ? "Запуск..."
                    : "Повторить анализ"}
                </button>
              )}

              {canReview && (
                <button
                  className="button"
                  type="button"
                  onClick={() =>
                    setReviewOpen(
                      true,
                    )
                  }
                >
                  Экспертная проверка
                </button>
              )}
            </div>


            {(me?.role === "ADMIN"
              || me?.role
                === "OPERATOR") && (
              <details className="viewer-technical">
                <summary>
                  Техническая информация
                </summary>

                <dl>
                  <div>
                    <dt>
                      Study ID
                    </dt>

                    <dd>
                      {study.id}
                    </dd>
                  </div>

                  <div>
                    <dt>
                      Статус
                    </dt>

                    <dd>
                      {study.status}
                    </dd>
                  </div>

                  {activeJob && (
                    <>
                      <div>
                        <dt>
                          Job
                        </dt>

                        <dd>
                          {activeJob.status}
                        </dd>
                      </div>

                      <div>
                        <dt>
                          Попыток
                        </dt>

                        <dd>
                          {
                            activeJob
                              .attempts
                          }
                        </dd>
                      </div>
                    </>
                  )}

                  {aggregate?.model && (
                    <div>
                      <dt>
                        AI-модель
                      </dt>

                      <dd>
                        {
                          aggregate
                            .model
                            .name
                          ?? "—"
                        }
                        {" "}
                        {
                          aggregate
                            .model
                            .version
                          ?? ""
                        }
                      </dd>
                    </div>
                  )}
                </dl>

                {activeJob
                  ?.error_message && (
                  <pre>
                    {
                      activeJob
                        .error_message
                    }
                  </pre>
                )}
              </details>
            )}
          </aside>
        </div>
      </div>


      <ExpertReviewDrawer
        studyId={studyId}
        open={reviewOpen}
        onClose={() =>
          setReviewOpen(false)
        }
      />
    </>
  );
}
