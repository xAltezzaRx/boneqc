import { NextResponse } from "next/server";


export async function POST() {
  const response = NextResponse.json(
    {
      ok: true,
    },
  );

  response.cookies.set(
    "boneqc_access_token",
    "",
    {
      httpOnly: true,
      sameSite: "strict",
      secure: process.env.BONEQC_COOKIE_SECURE === "true",
      path: "/",
      maxAge: 0,
    },
  );

  return response;
}
