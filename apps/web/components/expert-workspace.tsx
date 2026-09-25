"use client";

import Link from "next/link";

import {
  useEffect,
  useState,
} from "react";

import {
  ExpertReviewDrawer,
} from "@/components/expert-review-drawer";

import type {
  ExpertAnatomy,
  ExpertGeometryItem,
} from "@/components/expert-review-drawer";

import {
  ExpertGeometryCanvas,
} from "@/components/expert-geometry-canvas";


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

  preview_object_key:
    string | null;

  dicom_metadata:
    Record<string, unknown>;

  created_at: string;
  updated_at: string;
}


interface MyAnnotationStatus {
  reviewed: boolean;
}


interface Props {
  studyId: string;
}


function shortId(
  value: string,
): string {
  return value.slice(
    0,
    8,
  );
}


export function ExpertWorkspace({
  studyId,
}: Props) {
  const [
    user,
    setUser,
  ] = useState<
    CurrentUser | null
  >(null);

  const [
    study,
    setStudy,
  ] = useState<
    Study | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  const [
    annotationId,
    setAnnotationId,
  ] = useState<
    string | null
  >(null);

  const [
    anatomy,
    setAnatomy,
  ] = useState<
    ExpertAnatomy | null
  >(
    null,
  );

  const [
    geometry,
    setGeometry,
  ] = useState<
    ExpertGeometryItem[]
  >([]);


  useEffect(
    () => {
      let cancelled =
        false;

      async function load() {
        setLoading(true);
        setError("");

        try {
          const [
            userResponse,
            studyResponse,
            annotationStatusResponse,
          ] = await Promise.all([
            fetch(
              "/api/session/me",
              {
                cache:
                  "no-store",
              },
            ),

            fetch(
              `/api/backend/studies/${studyId}`,
              {
                cache:
                  "no-store",
              },
            ),

            fetch(
              (
                `/api/backend/studies/${studyId}`
                + "/my-annotation-status"
              ),
              {
                cache:
                  "no-store",
              },
            ),
          ]);

          if (
            !userResponse.ok
          ) {
            throw new Error(
              "Не удалось определить "
              + "текущего пользователя.",
            );
          }

          if (
            !studyResponse.ok
          ) {
            throw new Error(
              "Исследование "
              + "недоступно.",
            );
          }

          if (
            !annotationStatusResponse.ok
          ) {
            throw new Error(
              "Не удалось определить "
              + "статус экспертной оценки.",
            );
          }

          const userData =
            (
              await userResponse
                .json()
            ) as CurrentUser;

          const studyData =
            (
              await studyResponse
                .json()
            ) as Study;

          const annotationStatus =
            (
              await annotationStatusResponse
                .json()
            ) as MyAnnotationStatus;

          if (
            typeof annotationStatus
              .reviewed
              !== "boolean"
          ) {
            throw new Error(
              "Некорректный статус "
              + "экспертной оценки.",
            );
          }

          if (
            userData.role
              !== "ADMIN"
            && userData.role
              !== "DOCTOR"
          ) {
            throw new Error(
              "Режим BoneQC Expert "
              + "доступен врачу "
              + "или администратору.",
            );
          }

          if (!cancelled) {
            setUser(
              userData,
            );

            setStudy(
              studyData,
            );

            setAnnotationId(
              annotationStatus.reviewed
                ? "saved"
                : null,
            );
          }
        } catch (reason) {
          if (!cancelled) {
            setError(
              reason
                instanceof Error
                ? reason.message
                : String(
                    reason,
                  ),
            );
          }
        } finally {
          if (!cancelled) {
            setLoading(
              false,
            );
          }
        }
      }

      void load();

      return () => {
        cancelled =
          true;
      };
    },
    [
      studyId,
    ],
  );


  if (loading) {
    return (
      <main
        className={
          "expert-workspace-page"
        }
      >
        <div
          className={
            "expert-workspace-loading"
          }
        >
          <strong>
            BoneQC Expert
          </strong>

          <span>
            Загружаем исследование…
          </span>
        </div>
      </main>
    );
  }


  if (
    error
    || !study
    || !user
  ) {
    return (
      <main
        className={
          "expert-workspace-page"
        }
      >
        <div
          className={
            "expert-workspace-error"
          }
        >
          <strong>
            BoneQC Expert
          </strong>

          <span>
            {error
              || (
                "Исследование "
                + "не найдено."
              )}
          </span>

          <Link
            href="/studies"
            className="button"
          >
            К исследованиям
          </Link>
        </div>
      </main>
    );
  }


  return (
    <main
      className={
        "expert-workspace-page"
      }
    >
      <header
        className={
          "expert-workspace-header"
        }
      >
        <div>
          <Link
            href="/studies"
            className={
              "viewer-back"
            }
          >
            ← Исследования
          </Link>

          <div
            className={
              "expert-workspace-title"
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

              <h1>
                Независимая
                экспертная разметка
              </h1>

              <div
                className="muted"
              >
                Исследование{" "}
                {shortId(
                  study.id,
                )}
                {" · "}
                {study.original_filename}
              </div>
            </div>

            <div
              className={
                "expert-blind-pill"
              }
            >
              <span
                aria-hidden="true"
              >
                ●
              </span>

              BLIND REVIEW
            </div>
          </div>
        </div>

        <div
          className={
            "expert-workspace-user"
          }
        >
          <span>
            Эксперт
          </span>

          <strong>
            {user.username}
          </strong>

          <small>
            {user.role}
          </small>
        </div>
      </header>


      <div
        className={
          annotationId
            ? (
                "expert-workspace-grid "
                + "expert-workspace-locked"
              )
            : (
                "expert-workspace-grid"
              )
        }
      >
        <section
          className={
            "expert-workspace-viewer"
          }
        >
          <div
            className={
              "expert-workspace-viewer-head"
            }
          >
            <div>
              <strong>
                DXA изображение
              </strong>

              <span
                className={
                  "muted small"
                }
              >
                Исходный preview
              </span>
            </div>

            <span
              className={
                "expert-no-ai"
              }
            >
              AI result hidden
            </span>
          </div>

          <ExpertGeometryCanvas
            studyId={studyId}
            anatomy={anatomy}
            geometry={geometry}
            onChange={
              setGeometry
            }
          />

          <div
            className={
              "expert-workspace-footnote"
            }
          >
            <strong>
              Независимый режим.
            </strong>

            <span>
              На этой странице
              не запрашиваются результаты
              BoneQC до фиксации
              экспертной оценки.
            </span>
          </div>
        </section>


        <section
          className={
            "expert-workspace-form"
          }
        >
          {!annotationId && (
            <ExpertReviewDrawer
              studyId={studyId}
              open
              embedded
              anatomy={anatomy}
              geometry={geometry}
              onAnatomyChange={
                setAnatomy
              }
              onClose={() => {
                // Embedded workspace.
              }}
              onSubmitted={(
                id,
              ) => {
                setAnnotationId(
                  id ?? "saved",
                );
              }}
            />
          )}

          {annotationId && (
            <div
              className={
                "expert-workspace-lock"
              }
            >
              <div>
                <div
                  className={
                    "expert-lock-icon"
                  }
                >
                  ✓
                </div>

                <strong>
                  Экспертная оценка
                  зафиксирована
                </strong>

                <span>
                  Annotation{" "}
                  {annotationId
                    === "saved"
                    ? "сохранена"
                    : shortId(
                        annotationId,
                      )}
                </span>

                <p>
                  Мнение эксперта уже
                  сохранено. Повторное
                  заполнение этой оценки
                  недоступно.
                </p>

                <Link
                  href="/studies"
                  className="button"
                >
                  К исследованиям
                </Link>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
