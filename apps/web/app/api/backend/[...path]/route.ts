import { NextRequest, NextResponse } from "next/server";

import {
  apiBase,
  getToken,
} from "@/lib/api";


interface RouteContext {
  params: Promise<{
    path: string[];
  }>;
}


async function proxy(
  request: NextRequest,
  context: RouteContext,
) {
  const token = await getToken();

  if (!token) {
    return NextResponse.json(
      {
        detail: "Not authenticated",
      },
      {
        status: 401,
      },
    );
  }

  const params = await context.params;

  const path = params.path.join("/");

  const query =
    request.nextUrl.searchParams.toString();

  const target =
    `${apiBase()}/api/v1/${path}`
    + (query ? `?${query}` : "");

  const headers = new Headers();

  headers.set(
    "Authorization",
    `Bearer ${token}`,
  );

  const contentType =
    request.headers.get("content-type");

  if (contentType) {
    headers.set(
      "Content-Type",
      contentType,
    );
  }

  const accept =
    request.headers.get("accept");

  if (accept) {
    headers.set(
      "Accept",
      accept,
    );
  }

  let body:
    ArrayBuffer | undefined;

  if (
    request.method !== "GET"
    && request.method !== "HEAD"
  ) {
    body = await request.arrayBuffer();
  }

  let backendResponse: Response;

  try {
    backendResponse = await fetch(
      target,
      {
        method: request.method,
        headers,
        body,
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(
      {
        detail: "BoneQC API unavailable",
      },
      {
        status: 503,
      },
    );
  }

  const responseHeaders =
    new Headers();

  const responseType =
    backendResponse.headers.get(
      "content-type",
    );

  if (responseType) {
    responseHeaders.set(
      "Content-Type",
      responseType,
    );
  }

  const cacheControl =
    backendResponse.headers.get(
      "cache-control",
    );

  if (cacheControl) {
    responseHeaders.set(
      "Cache-Control",
      cacheControl,
    );
  }

  return new NextResponse(
    backendResponse.body,
    {
      status: backendResponse.status,
      headers: responseHeaders,
    },
  );
}


export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
