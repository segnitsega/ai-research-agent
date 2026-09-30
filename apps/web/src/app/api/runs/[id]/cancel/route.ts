import { apiFetch } from "@/lib/env";

export async function POST(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const response = await apiFetch(`/v1/runs/${id}/cancel`, { method: "POST" });
  return new Response(await response.text(), { status: response.status, headers: { "Content-Type": "application/json" } });
}
