"use client";

import {
  FormEvent,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";


export default function LoginPage() {
  const router = useRouter();

  const [username, setUsername] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(false);


  async function submit(
    event: FormEvent,
  ) {
    event.preventDefault();

    setLoading(true);
    setError("");

    try {
      const response =
        await fetch(
          "/api/session/login",
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              username,
              password,
            }),
          },
        );

      const data =
        await response.json();

      if (!response.ok) {
        setError(
          data.detail
          ?? "Ошибка авторизации",
        );

        return;
      }

      router.replace("/studies");
      router.refresh();
    } catch {
      setError(
        "Не удалось связаться с сервером.",
      );
    } finally {
      setLoading(false);
    }
  }


  return (
    <main className="boneqc-login">
      <section className="login-brand-panel">
        <div className="login-brand-content">
          <div className="login-brand-header">
            <img
              className="login-wordmark"
              src="/brand/boneqc-logo.png"
              alt="BoneQC"
            />

            <span className="login-prototype-badge">
              Research prototype
            </span>
          </div>

          <div className="login-hero-copy">
            <div className="login-eyebrow">
              QUALITY INTELLIGENCE
              FOR DXA
            </div>

            <h1>
              Контроль качества
              денситометрических
              исследований
            </h1>

            <p>
              BoneQC помогает
              автоматически выявлять
              технические нарушения
              исследования и формирует
              объяснимый QC-результат
              для дальнейшей проверки.
            </p>
          </div>

          <div className="login-flow">
            <div className="login-flow-step">
              <span className="login-flow-number">
                01
              </span>

              <div>
                <strong>DICOM</strong>

                <span>
                  Безопасная обработка
                  исследования
                </span>
              </div>
            </div>

            <div
              className="login-flow-arrow"
              aria-hidden="true"
            >
              →
            </div>

            <div className="login-flow-step">
              <span className="login-flow-number">
                02
              </span>

              <div>
                <strong>AI QC</strong>

                <span>
                  Автоматический
                  анализ качества
                </span>
              </div>
            </div>

            <div
              className="login-flow-arrow"
              aria-hidden="true"
            >
              →
            </div>

            <div className="login-flow-step">
              <span className="login-flow-number">
                03
              </span>

              <div>
                <strong>Result</strong>

                <span>
                  PASS, FAIL или
                  CANNOT_ASSESS
                </span>
              </div>
            </div>
          </div>

          <div className="login-capabilities">
            <div className="login-capability">
              <span
                className="login-capability-icon"
                aria-hidden="true"
              >
                ✓
              </span>

              <div>
                <strong>
                  Контроль укладки
                </strong>

                <span>
                  Позвоночник и
                  проксимальный отдел
                  бедра
                </span>
              </div>
            </div>

            <div className="login-capability">
              <span
                className="login-capability-icon"
                aria-hidden="true"
              >
                ✓
              </span>

              <div>
                <strong>
                  Объяснимый результат
                </strong>

                <span>
                  Конкретные типы
                  нарушений качества
                </span>
              </div>
            </div>

            <div className="login-capability">
              <span
                className="login-capability-icon"
                aria-hidden="true"
              >
                ✓
              </span>

              <div>
                <strong>
                  BoneQC Expert
                </strong>

                <span>
                  Независимый
                  экспертный review
                </span>
              </div>
            </div>
          </div>

          <div className="login-brand-footer">
            ХМ ЛАБ
            <span aria-hidden="true">
              ·
            </span>
            BoneQC 2026
          </div>
        </div>
      </section>

      <section className="login-form-panel">
        <form
          className="login-form-card"
          onSubmit={submit}
        >
          <div className="login-form-mark-shell">
            <img
              className="login-form-mark"
              src="/brand/boneqc-mark.png"
              alt=""
              aria-hidden="true"
            />
          </div>

          <div className="login-form-heading">
            <span>
              Защищённый контур
            </span>

            <h2>
              Вход в BoneQC
            </h2>

            <p>
              Авторизуйтесь для работы
              с исследованиями и
              контролем качества.
            </p>
          </div>

          {error && (
            <div
              className="error auth-error"
              role="alert"
              aria-live="polite"
            >
              {error}
            </div>
          )}

          <div className="login-form-fields">
            <label className="label">
              Логин

              <input
                className="input"
                value={username}
                onChange={(event) =>
                  setUsername(
                    event.target.value,
                  )
                }
                autoComplete="username"
                autoFocus
                placeholder="Введите логин"
                required
              />
            </label>

            <label className="label">
              Пароль

              <input
                className="input"
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(
                    event.target.value,
                  )
                }
                autoComplete="current-password"
                placeholder="Введите пароль"
                required
              />
            </label>
          </div>

          <button
            className="button login-submit"
            type="submit"
            disabled={loading}
            aria-busy={loading}
          >
            {loading
              ? "Выполняется вход..."
              : "Войти в систему"}
          </button>

          <div className="login-form-note">
            Сервис предназначен для
            контроля технического
            качества исследования и
            не выполняет медицинскую
            диагностику.
          </div>
        </form>
      </section>
    </main>
  );
}