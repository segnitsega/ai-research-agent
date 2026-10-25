import { apiFetch } from "@/lib/env";

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const response = await apiFetch(`/v1/runs/${id}/feedback`, { method: "POST", body: await request.text() });
  return new Response(await response.text(), {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
  });
}
