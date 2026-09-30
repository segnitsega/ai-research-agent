import { apiFetch } from "@/lib/env";

export async function GET() {
  const response = await apiFetch("/v1/memories");
  return new Response(await response.text(), { status: response.status, headers: { "Content-Type": "application/json" } });
}

export async function POST(request: Request) {
  const response = await apiFetch("/v1/memories", { method: "POST", body: await request.text() });
  return new Response(await response.text(), { status: response.status, headers: { "Content-Type": "application/json" } });
}

export async function DELETE(request: Request) {
  const url = new URL(request.url);
  const response = await apiFetch(`/v1/memories?confirm=${url.searchParams.get("confirm") ?? "false"}`, { method: "DELETE" });
  return new Response(await response.text(), { status: response.status });
}
