import { apiFetch } from "@/lib/env";

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.get("q") ?? "";
  const response = await apiFetch(`/v1/memories/search?q=${encodeURIComponent(query)}`);
  return new Response(await response.text(), {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
  });
}
