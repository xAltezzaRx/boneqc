import Link from "next/link";
import {
  redirect,
} from "next/navigation";

import {
  LogoutButton,
} from "@/components/logout-button";

import {
  getCurrentUser,
} from "@/lib/api";


export default async function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const user =
    await getCurrentUser();

  if (!user) {
    redirect("/login");
  }


  const roleLabel =
    user.role === "ADMIN"
      ? "Администратор"
      : (
          user.role === "DOCTOR"
            ? "Эксперт"
            : "Оператор"
        );


  const userInitial =
    user.username
      .trim()
      .slice(0, 1)
      .toUpperCase()
    || "B";


  return (
    <div className="shell app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <Link
            className="app-brand"
            href="/studies"
            aria-label="BoneQC"
          >
            <img
              src="/brand/boneqc-logo.png"
              alt="BoneQC"
            />
          </Link>

          <div
            className="app-header-divider"
            aria-hidden="true"
          />

          <nav
            className="app-nav"
            aria-label="Основная навигация"
          >
            <Link href="/studies">
              Исследования
            </Link>

            {(user.role === "ADMIN"
              || user.role
                === "OPERATOR") && (
              <Link href="/studies/new">
                Загрузить DICOM
              </Link>
            )}

            {user.role === "ADMIN"
              && (
                <Link href="/admin">
                  Администрирование
                </Link>
              )}
          </nav>

          <div className="app-user">
            <div
              className="app-user-avatar"
              aria-hidden="true"
            >
              {userInitial}
            </div>

            <div className="app-user-copy">
              <strong>
                {user.username}
              </strong>

              <span>
                {roleLabel}
              </span>
            </div>

            <LogoutButton />
          </div>
        </div>
      </header>

      <main className="main app-main">
        {children}
      </main>
    </div>
  );
}