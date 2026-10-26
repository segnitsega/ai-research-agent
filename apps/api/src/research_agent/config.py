import os
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from research_agent.schemas.budget import DEPTH_PRESETS, Budget, BudgetOverrides, Depth

DEFAULT_GEMINI_MODEL = "google:gemini-2.5-flash"
DEFAULT_XAI_MODEL = "xai:grok-4.7"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_key: SecretStr = SecretStr("change-me-dev-key")
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://research:research@localhost:5433/research"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if not isinstance(value, str) or not value.strip():
            return value
        url = value.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url.removeprefix("postgres://")
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
        # Managed Postgres (e.g. Render) usually requires TLS.
        local = "localhost" in url or "127.0.0.1" in url
        if not local and "ssl=" not in url:
            url = f"{url}&ssl=require" if "?" in url else f"{url}?ssl=require"
        return url

    model_planner: str = DEFAULT_GEMINI_MODEL
    model_searcher: str = DEFAULT_GEMINI_MODEL
    model_reader: str = DEFAULT_GEMINI_MODEL
    model_critic: str = DEFAULT_GEMINI_MODEL
    model_writer: str = DEFAULT_GEMINI_MODEL
    model_curator: str = DEFAULT_GEMINI_MODEL

    google_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    xai_api_key: SecretStr | None = None

    embedder: Literal["hash", "gemini"] = "hash"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    search_provider: Literal["fake", "tavily", "duckduckgo", "arxiv"] = "fake"
    tavily_api_key: SecretStr | None = None
    brave_api_key: SecretStr | None = None

    max_active_runs_per_user: int = 2
    max_concurrent_searches: int = 4
    max_concurrent_fetches: int = 5
    max_concurrent_llm_calls: int = 8

    fetch_timeout_s: int = 15
    fetch_max_bytes: int = 2_000_000
    fetch_max_bytes_pdf: int = 10_000_000
    source_ttl_days: int = 14
    respect_robots: bool = True

    server_max_cost_usd: float = 5.0
    server_max_fetches: int = 150
    server_max_iterations: int = 6
    server_max_tokens: int = 5_000_000
    server_max_wall_seconds: int = 3600

    recall_min_similarity: float = 0.55
    memory_dedupe_similarity: float = 0.88
    max_memories_per_user: int = 500
    memory_content_max_chars: int = 300

    quote_fuzzy_match: bool = False
    quote_fuzzy_threshold: int = 97

    blocked_domains: str = ""
    allowed_domains: str = ""

    allow_model_requests: bool = False

    logfire_token: SecretStr | None = None
    otel_exporter_otlp_endpoint: str | None = None

    seeded_user_id: str = "00000000-0000-0000-0000-000000000001"

    user_agent: str = "ResearchAgent/0.1 (+https://example.com/bot)"

    @field_validator("cors_origins")
    @classmethod
    def split_cors(cls, v: str) -> str:
        return v

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def blocked_domain_set(self) -> set[str]:
        return {d.strip().lower() for d in self.blocked_domains.split(",") if d.strip()}

    def allowed_domain_set(self) -> set[str]:
        if not self.allowed_domains.strip():
            return set()
        return {d.strip().lower() for d in self.allowed_domains.split(",") if d.strip()}

    def depth_sub_questions(self, depth: Depth) -> int:
        return int(DEPTH_PRESETS[depth]["sub_questions"])

    def resolve_budget(self, depth: Depth, overrides: BudgetOverrides | None) -> Budget:
        preset = DEPTH_PRESETS[depth]
        base = Budget(
            max_iterations=int(preset["max_iterations"]),
            max_fetches=int(preset["max_fetches"]),
            max_cost_usd=float(preset["max_cost_usd"]),
            max_tokens=int(preset["max_tokens"]),
            max_wall_seconds=int(preset["max_wall_seconds"]),
        )
        if overrides is None:
            return self._cap_budget(base)
        merged = Budget(
            max_iterations=overrides.max_iterations or base.max_iterations,
            max_fetches=overrides.max_fetches or base.max_fetches,
            max_cost_usd=overrides.max_cost_usd or base.max_cost_usd,
            max_tokens=overrides.max_tokens or base.max_tokens,
            max_wall_seconds=overrides.max_wall_seconds or base.max_wall_seconds,
        )
        return self._cap_budget(merged)

    def _cap_budget(self, budget: Budget) -> Budget:
        if budget.max_cost_usd > self.server_max_cost_usd:
            msg = f"max_cost_usd exceeds server maximum {self.server_max_cost_usd}"
            raise ValueError(msg)
        if budget.max_fetches > self.server_max_fetches:
            msg = f"max_fetches exceeds server maximum {self.server_max_fetches}"
            raise ValueError(msg)
        if budget.max_iterations > self.server_max_iterations:
            msg = f"max_iterations exceeds server maximum {self.server_max_iterations}"
            raise ValueError(msg)
        if budget.max_tokens > self.server_max_tokens:
            msg = f"max_tokens exceeds server maximum {self.server_max_tokens}"
            raise ValueError(msg)
        if budget.max_wall_seconds > self.server_max_wall_seconds:
            msg = f"max_wall_seconds exceeds server maximum {self.server_max_wall_seconds}"
            raise ValueError(msg)
        return budget

    def apply_provider_env(self) -> None:
        key = self.resolved_google_api_key()
        if key:
            os.environ["GOOGLE_API_KEY"] = key
            os.environ["GEMINI_API_KEY"] = key
        xai = self.resolved_xai_api_key()
        if xai:
            os.environ["XAI_API_KEY"] = xai
        if self.allow_model_requests:
            os.environ["ALLOW_MODEL_REQUESTS"] = "true"

    def resolved_google_api_key(self) -> str | None:
        if self.google_api_key is not None and self.google_api_key.get_secret_value():
            return self.google_api_key.get_secret_value()
        if self.gemini_api_key is not None and self.gemini_api_key.get_secret_value():
            return self.gemini_api_key.get_secret_value()
        return None

    def resolved_xai_api_key(self) -> str | None:
        if self.xai_api_key is not None and self.xai_api_key.get_secret_value():
            return self.xai_api_key.get_secret_value()
        return None

    def resolve_llm_model(self, configured: str):
        """Pick Gemini first when its key exists, otherwise Grok; fall back across both when possible."""
        from pydantic_ai.models.fallback import FallbackModel

        has_google = bool(self.resolved_google_api_key())
        has_xai = bool(self.resolved_xai_api_key())
        gemini = configured if _is_google_model(configured) else DEFAULT_GEMINI_MODEL
        grok = configured if _is_xai_model(configured) else DEFAULT_XAI_MODEL

        if has_google and has_xai:
            return FallbackModel(gemini, grok)
        if has_google:
            return gemini
        if has_xai:
            return grok
        return configured

    def describe_llm_model(self, configured: str) -> str:
        model = self.resolve_llm_model(configured)
        nested = getattr(model, "models", None)
        if nested:
            parts: list[str] = []
            for item in nested:
                name = getattr(item, "model_name", str(item))
                kind = type(item).__name__.lower()
                if "google" in kind:
                    parts.append(f"google:{name}")
                elif "xai" in kind:
                    parts.append(f"xai:{name}")
                else:
                    parts.append(str(name))
            return " → ".join(parts)
        if isinstance(model, str):
            return model
        return str(getattr(model, "model_name", model))

    def public_config(self) -> dict[str, object]:
        return {
            "depth_presets": {k.value: v for k, v in DEPTH_PRESETS.items()},
            "server_max": {
                "max_cost_usd": self.server_max_cost_usd,
                "max_fetches": self.server_max_fetches,
                "max_iterations": self.server_max_iterations,
                "max_tokens": self.server_max_tokens,
                "max_wall_seconds": self.server_max_wall_seconds,
            },
            "search_providers": [self.search_provider, "arxiv"],
            "models": {
                "planner": self.describe_llm_model(self.model_planner),
                "searcher": self.describe_llm_model(self.model_searcher),
                "reader": self.describe_llm_model(self.model_reader),
                "critic": self.describe_llm_model(self.model_critic),
                "writer": self.describe_llm_model(self.model_writer),
                "curator": self.describe_llm_model(self.model_curator),
            },
        }


def _is_google_model(model: str) -> bool:
    prefix = model.split(":", 1)[0].lower()
    return prefix in {"google", "google-gla", "google-vertex", "gemini"}


def _is_xai_model(model: str) -> bool:
    return model.split(":", 1)[0].lower() == "xai"


@lru_cache
def get_settings() -> Settings:
    return Settings()
