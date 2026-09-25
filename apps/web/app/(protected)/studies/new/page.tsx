"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import Link from "next/link";

import {
  useRouter,
} from "next/navigation";


interface Me {
  role:
    | "ADMIN"
    | "DOCTOR"
    | "OPERATOR";
}


type UploadStage =
  | "IDLE"
  | "UPLOADING"
  | "STARTING_ANALYSIS";


export default function UploadPage() {
  const router =
    useRouter();

  const [
    file,
    setFile,
  ] = useState<
    File | null
  >(null);

  const [
    error,
    setError,
  ] = useState("");

  const [
    stage,
    setStage,
  ] = useState<
    UploadStage
  >("IDLE");

  const [
    allowed,
    setAllowed,
  ] = useState<
    boolean | null
  >(null);


  useEffect(() => {
    fetch(
      "/api/session/me",
      {
        cache: "no-store",
      },
    )
      .then((response) =>
        response.json(),
      )
      .then((me: Me) => {
        setAllowed(
          me.role === "ADMIN"
          || me.role
            === "OPERATOR",
        );
      })
      .catch(() =>
        setAllowed(false),
      );
  }, []);


  async function upload(
    event: FormEvent,
  ) {
    event.preventDefault();

    if (!file) {
      setError(
        "Выберите DICOM файл.",
      );
      return;
    }

    setStage("UPLOADING");
    setError("");

    const form =
      new FormData();

    form.append(
      "file",
      file,
    );

    try {
      const uploadResponse =
        await fetch(
          "/api/backend/studies",
          {
            method: "POST",
            body: form,
          },
        );

      let study: any = null;

      const uploadContentType =
        uploadResponse.headers
          .get("content-type")
          ?? "";

      if (
        uploadContentType.includes(
          "application/json",
        )
      ) {
        try {
          study =
            await uploadResponse.json();
        } catch {
          study = null;
        }
      } else {
        await uploadResponse
          .text()
          .catch(() => "");
      }

      if (!uploadResponse.ok) {
        const detail =
          study?.detail;

        const apiMessage =
          typeof detail === "string"
            ? detail
            : (
                detail?.message
                ?? detail?.code
              );

        throw new Error(
          apiMessage
          ?? (
            uploadResponse.status >= 500
              ? (
                  "Сервис не смог обработать "
                  + "DICOM. Повторите попытку "
                  + "или проверьте структуру файла."
                )
              : `HTTP ${uploadResponse.status}`
          ),
        );
      }

      if (!study?.id) {
        throw new Error(
          "Сервис вернул некорректный "
          + "ответ при загрузке DICOM."
        );
      }


      setStage(
        "STARTING_ANALYSIS",
      );


      const analysisResponse =
        await fetch(
          `/api/backend/studies/${study.id}/analyze`,
          {
            method: "POST",
          },
        );

      let job: any = null;

      try {
        job =
          await analysisResponse
            .json();
      } catch {
        job = null;
      }


      if (
        analysisResponse.ok
        && job?.id
      ) {
        router.push(
          `/studies/${study.id}`
          + `?job=${job.id}`,
        );

        return;
      }


      router.push(
        `/studies/${study.id}`,
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : (
              "Ошибка загрузки "
              + "исследования."
            ),
      );

      setStage("IDLE");
    }
  }


  if (allowed === false) {
    return (
      <div className="upload-access-denied">
        <div>
          <span>
            !
          </span>
        </div>

        <h1>
          Нет доступа
        </h1>

        <p>
          У вашей роли нет права
          загружать исследования.
        </p>

        <Link
          className="button secondary"
          href="/studies"
        >
          Вернуться к исследованиям
        </Link>
      </div>
    );
  }


  const loading =
    stage !== "IDLE";


  const buttonLabel =
    stage === "UPLOADING"
      ? "Загрузка DICOM..."
      : (
          stage
            === "STARTING_ANALYSIS"
            ? "Запуск контроля..."
            : "Загрузить и проверить"
        );


  return (
    <div className="upload-page">
      <header className="upload-heading">
        <Link
          className="upload-back"
          href="/studies"
        >
          ← Исследования
        </Link>

        <div className="page-eyebrow">
          NEW STUDY
        </div>

        <h1 className="page-title">
          Загрузка исследования
        </h1>

        <p className="page-description">
          BoneQC проверит DICOM,
          выполнит privacy preprocessing
          и автоматически запустит
          контроль технического качества.
        </p>
      </header>


      <div className="upload-layout">
        <form
          className="upload-card"
          onSubmit={upload}
        >
          <div className="upload-card-header">
            <div>
              <span>
                DICOM INPUT
              </span>

              <h2>
                Выберите исследование
              </h2>
            </div>

            <div className="upload-format-badge">
              .DCM
            </div>
          </div>


          {error && (
            <div className="error">
              {error}
            </div>
          )}


          <label
            className={
              file
                ? (
                    "upload-dropzone "
                    + "upload-dropzone-selected"
                  )
                : "upload-dropzone"
            }
          >
            <div className="upload-icon">
              ↑
            </div>

            <strong>
              {file
                ? "DICOM выбран"
                : "Перетащите или выберите DICOM"}
            </strong>

            <span className="muted">
              Поддерживается один
              DICOM-файл исследования
            </span>

            <span className="upload-select-action">
              Выбрать файл
            </span>

            <input
              type="file"
              accept={
                ".dcm,"
                + "application/dicom"
              }
              onChange={(
                event,
              ) =>
                setFile(
                  event.target
                    .files?.[0]
                  ?? null,
                )
              }
              required
            />
          </label>


          {file && (
            <div className="upload-file">
              <div className="upload-file-icon">
                DX
              </div>

              <div className="upload-file-copy">
                <strong>
                  {file.name}
                </strong>

                <span>
                  {(
                    file.size
                    / 1024
                    / 1024
                  ).toFixed(2)}
                  {" MB"}
                </span>
              </div>

              <span className="upload-file-type">
                DICOM
              </span>
            </div>
          )}


          <button
            className="button upload-submit"
            disabled={
              loading
              || allowed !== true
              || file === null
            }
          >
            {loading && (
              <span
                className="button-spinner"
                aria-hidden="true"
              />
            )}

            {buttonLabel}
          </button>
        </form>


        <aside className="upload-info-panel">
          <div className="upload-info-header">
            <span>
              Как проходит обработка
            </span>

            <h2>
              От DICOM до QC-result
            </h2>
          </div>


          <div className="upload-process">
            <div className="upload-process-item">
              <div className="upload-process-number">
                01
              </div>

              <div>
                <strong>
                  Загрузка
                </strong>

                <span>
                  Файл принимается
                  защищённым product
                  layer BoneQC.
                </span>
              </div>
            </div>

            <div className="upload-process-line" />

            <div className="upload-process-item">
              <div className="upload-process-number">
                02
              </div>

              <div>
                <strong>
                  Privacy preprocessing
                </strong>

                <span>
                  Validation,
                  de-identification
                  и UID remapping.
                </span>
              </div>
            </div>

            <div className="upload-process-line" />

            <div className="upload-process-item">
              <div className="upload-process-number">
                03
              </div>

              <div>
                <strong>
                  AI Quality Control
                </strong>

                <span>
                  Frozen C7 оценивает
                  поддерживаемые
                  критерии качества.
                </span>
              </div>
            </div>

            <div className="upload-process-line" />

            <div className="upload-process-item">
              <div className="upload-process-number">
                04
              </div>

              <div>
                <strong>
                  QC-result
                </strong>

                <span>
                  PASS, FAIL или
                  CANNOT_ASSESS
                  с объяснением.
                </span>
              </div>
            </div>
          </div>


          <div className="upload-security-note">
            <div className="upload-security-icon">
              ✓
            </div>

            <div>
              <strong>
                Контроль качества,
                не диагностика
              </strong>

              <span>
                BoneQC не ставит
                медицинский диагноз и
                не интерпретирует
                остеопороз.
              </span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}