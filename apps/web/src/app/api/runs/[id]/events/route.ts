import { apiConfig } from "@/lib/env";

export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const config = apiConfig();
  const lastEventId = request.headers.get("last-event-id");
  const upstream = await fetch(`${config.baseUrl}/v1/runs/${id}/events`, {
    headers: {
      "X-API-Key": config.apiKey,
      ...(lastEventId ? { "Last-Event-ID": lastEventId } : {}),
    },
    cache: "no-store",
  });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
