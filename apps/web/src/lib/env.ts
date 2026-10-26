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
  try {
    return await fetch(`${config.baseUrl}${pathname}`, { ...init, headers, cache: "no-store" });
  } catch {
    return Response.json(
      {
        type: "about:blank",
        title: "API unreachable",
        status: 502,
        detail: `Could not reach the API at ${config.baseUrl}. Check API_BASE_URL and that the API service is running.`,
      },
      { status: 502, headers: { "Content-Type": "application/problem+json" } },
    );
  }
}
