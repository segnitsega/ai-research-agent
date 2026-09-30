import { apiFetch } from "@/lib/env";

export async function DELETE(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const response = await apiFetch(`/v1/memories/${id}`, { method: "DELETE" });
  return new Response(null, { status: response.status });
}
