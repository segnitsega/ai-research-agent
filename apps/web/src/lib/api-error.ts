type ProblemBody = {
  detail?: unknown;
  title?: unknown;
  errors?: unknown;
  message?: unknown;
};

export async function readApiError(response: Response, fallback: string): Promise<string> {
  const body = (await response.json().catch(() => null)) as ProblemBody | null;
  return formatApiError(body, response.status, fallback);
}

export function formatApiError(body: ProblemBody | null | undefined, status: number, fallback: string): string {
  const fromBody = firstMessage(body?.detail) || firstMessage(body?.title) || firstMessage(body?.message);
  if (fromBody && !isGenericStatusLabel(fromBody)) return fromBody;

  const validation = formatValidationErrors(body?.errors);
  if (validation) return validation;

  switch (status) {
    case 401:
      return "API key missing or incorrect. Set the same API_KEY on both the web and API services.";
    case 403:
      return "This request was forbidden by the API.";
    case 404:
      return "The API endpoint was not found. Check API_BASE_URL on the web service.";
    case 409:
      return fromBody || "That action conflicts with the current run state.";
    case 422:
      return fromBody || "The request was invalid. Check the question and budget values.";
    case 429:
      return "Too many runs started recently, or another run is already active. Wait and try again.";
    case 502:
    case 503:
    case 504:
      return "The API service is unreachable or still waking up. Retry in a moment.";
    default:
      return fromBody || fallback;
  }
}

export function publicRunError(raw: string | null | undefined): string {
  if (!raw?.trim()) return "The research run failed.";
  const message = raw.trim();
  if (!looksLikeProviderDump(message)) return message;

  const lower = message.toLowerCase();
  if (includesAny(lower, "401", "unauthorized", "invalid api key", "api key")) {
    return "The model provider rejected the API key (missing, invalid, or expired). Check the provider keys on the API service.";
  }
  if (includesAny(lower, "404", "not found", "model_not_found")) {
    return "The configured model was not found. Check the MODEL_* settings on the API service.";
  }
  if (includesAny(lower, "429", "quota", "rate limit", "resource_exhausted")) {
    return "The model provider rate-limited or quota-exhausted this request. Wait a moment or check billing/quota.";
  }
  if (includesAny(lower, "503", "unavailable", "overloaded")) {
    return "The model provider is temporarily unavailable. Try again shortly.";
  }
  return "The research run failed while calling a model provider. Check API keys and model names on the API service.";
}

function firstMessage(value: unknown): string {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (Array.isArray(value)) {
    const parts = value
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item && typeof (item as { msg: unknown }).msg === "string") {
          return (item as { msg: string }).msg;
        }
        return "";
      })
      .filter(Boolean);
    return parts.join("; ");
  }
  return "";
}

function formatValidationErrors(errors: unknown): string {
  if (!Array.isArray(errors) || errors.length === 0) return "";
  const parts = errors
    .map((item) => {
      if (!item || typeof item !== "object") return "";
      const msg = "msg" in item && typeof item.msg === "string" ? item.msg : "";
      const loc =
        "loc" in item && Array.isArray(item.loc)
          ? item.loc.filter((part: unknown) => part !== "body").join(".")
          : "";
      if (msg && loc) return `${loc}: ${msg}`;
      return msg;
    })
    .filter(Boolean);
  return parts.length > 0 ? `Validation failed — ${parts.join("; ")}` : "";
}

function isGenericStatusLabel(value: string): boolean {
  return /^(unauthorized|not found|request failed|validation failed)$/i.test(value.trim());
}

function looksLikeProviderDump(value: string): boolean {
  return /status_code\s*:/i.test(value) || /model_name\s*:/i.test(value) || /body:\s*\{/i.test(value) || /"error"\s*:\s*\{/.test(value);
}

function includesAny(text: string, ...needles: string[]): boolean {
  return needles.some((needle) => text.includes(needle));
}
