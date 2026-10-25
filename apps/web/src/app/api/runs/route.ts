import { apiFetch } from "@/lib/env";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams.toString();
  const response = await apiFetch(`/v1/runs${params ? `?${params}` : ""}`);
  return new Response(await response.text(), { status: response.status, headers: { "Content-Type": "application/json" } });
}

export async function POST(request: Request) {
  const response = await apiFetch("/v1/runs", { method: "POST", body: await request.text() });
  return new Response(await response.text(), { status: response.status, headers: { "Content-Type": "application/json" } });
}
