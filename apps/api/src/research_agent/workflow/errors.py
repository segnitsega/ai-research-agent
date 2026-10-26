"""Turn raw run failures into short, client-safe messages."""

from __future__ import annotations


def describe_run_failure(exc: BaseException) -> str:
    text = " ".join(part for part in (type(exc).__name__, str(exc)) if part).lower()
    if _mentions(text, "401", "unauthorized", "invalid api key", "incorrect api key", "authentication", "api_key", "api key"):
        if _mentions(text, "xai", "grok"):
            return "The xAI/Grok API key is missing, invalid, or expired. Check XAI_API_KEY on the API service."
        if _mentions(text, "google", "gemini"):
            return "The Google/Gemini API key is missing, invalid, or expired. Check GOOGLE_API_KEY or GEMINI_API_KEY on the API service."
        if _mentions(text, "tavily"):
            return "The Tavily API key is missing, invalid, or expired. Check TAVILY_API_KEY on the API service."
        return "A provider rejected the API key (missing, invalid, or expired). Check provider keys on the API service."
    if _mentions(text, "403", "forbidden", "permission denied"):
        return "A provider refused access. Check that the API key can use the configured models."
    if _mentions(text, "404", "not_found", "not found", "model_not_found"):
        return "The configured model was not found. Check the MODEL_* settings on the API service."
    if _mentions(text, "429", "rate limit", "rate_limit", "quota", "resource_exhausted"):
        return "A provider rate-limited or quota-exhausted this request. Wait a moment or check billing/quota."
    if _mentions(text, "503", "unavailable", "overloaded", "high demand"):
        return "A model provider is temporarily unavailable. Try again in a few minutes."
    if _mentions(text, "timeout", "timed out", "deadline"):
        return "A model or network call timed out before the run could finish."
    if _mentions(text, "budget"):
        return "The run hit a budget limit before it could finish."
    if _mentions(text, "tavily"):
        return "Tavily search failed. Check TAVILY_API_KEY and that the key is still valid."
    return "The research run failed unexpectedly. Check the API service logs for details."


def _mentions(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)
