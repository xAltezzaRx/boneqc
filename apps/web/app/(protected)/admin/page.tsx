import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/lib/api";


export default async function AdminPage() {
  const user =
    await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  if (user.role !== "ADMIN") {
    redirect("/studies");
  }

  return (
    <div className="stack">
      <div>
        <h1 className="page-title">
          Администрирование
        </h1>

        <div className="muted">
          Служебный контур BoneQC.
          Клинический интерфейс
          отделён от ML и системных
          функций.
        </div>
      </div>

      <section className="admin-grid">
        <Link
          className="card admin-card"
          href="/dataset"
        >
          <div>
            <strong>
              Данные и датасеты
            </strong>

            <div className="muted">
              Разметка, consensus,
              readiness и версии
              обучающих данных.
            </div>
          </div>

          <span aria-hidden="true">
            →
          </span>
        </Link>

        <div className="card admin-card">
          <div>
            <strong>
              Модели
            </strong>

            <div className="muted">
              Версии моделей,
              provenance и метрики.
            </div>
          </div>
        </div>

        <div className="card admin-card">
          <div>
            <strong>
              Система
            </strong>

            <div className="muted">
              Audit, очереди,
              ошибки и состояние
              сервисов.
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
