import { cookies } from "next/headers";


export type UserRole =
  | "ADMIN"
  | "DOCTOR"
  | "OPERATOR";


export interface CurrentUser {
  id: string;
  username: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}


export function apiBase(): string {
  return (
    process.env.BONEQC_API_INTERNAL_URL
    ?? "http://api:8000"
  );
}


export async function getToken(): Promise<
  string | undefined
> {
  const store = await cookies();

  return store.get(
    "boneqc_access_token"
  )?.value;
}


export async function getCurrentUser():
  Promise<CurrentUser | null> {
  const token = await getToken();

  if (!token) {
    return null;
  }

  try {
    const response = await fetch(
      `${apiBase()}/api/v1/auth/me`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      },
    );

    if (!response.ok) {
      return null;
    }

    return await response.json();
  } catch {
    return null;
  }
}
