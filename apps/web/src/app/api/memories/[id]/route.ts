import { apiFetch } from "@/lib/env";

export async function PATCH(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const response = await apiFetch(`/v1/memories/${id}`, { method: "PATCH", body: await request.text() });
  return new Response(await response.text(), {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
  });
}

export async function DELETE(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const response = await apiFetch(`/v1/memories/${id}`, { method: "DELETE" });
  return new Response(null, { status: response.status });
}
