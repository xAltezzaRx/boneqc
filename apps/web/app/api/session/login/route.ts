import { NextRequest, NextResponse } from "next/server";

import { apiBase } from "@/lib/api";


export async function POST(
  request: NextRequest,
) {
  const body = await request.json();

  const username =
    typeof body.username === "string"
      ? body.username.trim()
      : "";

  const password =
    typeof body.password === "string"
      ? body.password
      : "";

  if (!username || !password) {
    return NextResponse.json(
      {
        detail: "Введите логин и пароль.",
      },
      {
        status: 400,
      },
    );
  }

  const form = new URLSearchParams();

  form.set("username", username);
  form.set("password", password);

  let loginResponse: Response;

  try {
    loginResponse = await fetch(
      `${apiBase()}/api/v1/auth/login`,
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/x-www-form-urlencoded",
        },
        body: form,
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(
      {
        detail: "API BoneQC недоступен.",
      },
      {
        status: 503,
      },
    );
  }

  if (!loginResponse.ok) {
    return NextResponse.json(
      {
        detail:
          loginResponse.status === 401
            ? "Неверный логин или пароль."
            : "Не удалось выполнить вход.",
      },
      {
        status: loginResponse.status,
      },
    );
  }

  const tokenData = await loginResponse.json();

  const token = tokenData.access_token;

  if (typeof token !== "string") {
    return NextResponse.json(
      {
        detail: "API вернул некорректный токен.",
      },
      {
        status: 502,
      },
    );
  }

  const response = NextResponse.json(
    {
      ok: true,
    },
  );

  response.cookies.set(
    "boneqc_access_token",
    token,
    {
      httpOnly: true,
      sameSite: "strict",
      secure: process.env.BONEQC_COOKIE_SECURE === "true",
      path: "/",
      maxAge: 60 * 30,
    },
  );

  return response;
}
