import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30_000,
});

// Generic helpers
export async function get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const res = await apiClient.get<T>(path, { params });
  return res.data;
}

export async function post<T, B = unknown>(path: string, body: B): Promise<T> {
  const res = await apiClient.post<T>(path, body);
  return res.data;
}

export async function patch<T, B = unknown>(path: string, body: B): Promise<T> {
  const res = await apiClient.patch<T>(path, body);
  return res.data;
}

/** Extract a user-facing message from an API/axios error (e.g. FastAPI detail). */
export function getApiErrorMessage(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const res = (err as { response?: { data?: { detail?: string } } }).response;
    const detail = res?.data?.detail;
    if (typeof detail === "string") return detail;
    if (typeof detail === "object" && detail !== null && "msg" in detail) return String((detail as { msg: unknown }).msg);
  }
  if (err instanceof Error) return err.message;
  return "Request failed";
}
