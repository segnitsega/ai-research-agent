import { apiFetch } from "@/lib/env";

export async function GET() {
  const response = await apiFetch("/v1/config");
  return new Response(await response.text(), {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
  });
}
