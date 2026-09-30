export type ApiConfig = {
  baseUrl: string;
  apiKey: string;
};

export function apiConfig(): ApiConfig {
  return {
    baseUrl: process.env.API_BASE_URL || "http://localhost:8000",
    apiKey: process.env.API_KEY || "",
  };
}

export async function apiFetch(pathname: string, init: RequestInit = {}): Promise<Response> {
  const config = apiConfig();
  const headers = new Headers(init.headers);
  if (config.apiKey) headers.set("X-API-Key", config.apiKey);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  return fetch(`${config.baseUrl}${pathname}`, { ...init, headers, cache: "no-store" });
}
