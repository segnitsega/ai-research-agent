import pytest
from pydantic import SecretStr
from pydantic_ai.models.fallback import FallbackModel

from research_agent.config import DEFAULT_GEMINI_MODEL, DEFAULT_XAI_MODEL, Settings

pytestmark = pytest.mark.unit


def test_prefers_gemini_when_only_google_key() -> None:
    settings = Settings(
        _env_file=None,
        google_api_key=SecretStr("google-key"),
        gemini_api_key=SecretStr(""),
        xai_api_key=SecretStr(""),
        model_planner=DEFAULT_XAI_MODEL,
    )
    assert settings.resolve_llm_model(settings.model_planner) == DEFAULT_GEMINI_MODEL


def test_uses_grok_when_only_xai_key() -> None:
    settings = Settings(
        _env_file=None,
        google_api_key=SecretStr(""),
        gemini_api_key=SecretStr(""),
        xai_api_key=SecretStr("xai-key"),
        model_planner=DEFAULT_GEMINI_MODEL,
    )
    assert settings.resolve_llm_model(settings.model_planner) == DEFAULT_XAI_MODEL


def test_gemini_then_grok_when_both_keys() -> None:
    settings = Settings(
        _env_file=None,
        google_api_key=SecretStr("google-key"),
        gemini_api_key=SecretStr(""),
        xai_api_key=SecretStr("xai-key"),
        model_planner=DEFAULT_GEMINI_MODEL,
    )
    model = settings.resolve_llm_model(settings.model_planner)
    assert isinstance(model, FallbackModel)
    assert [item.model_name for item in model.models] == ["gemini-2.5-flash", "grok-4.7"]
    assert settings.describe_llm_model(settings.model_planner) == "google:gemini-2.5-flash → xai:grok-4.7"
