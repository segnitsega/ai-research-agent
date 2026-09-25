from pydantic import BaseModel, ConfigDict, Field

from research_agent.schemas.enums import Depth


class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_iterations: int = Field(ge=1, le=6)
    max_fetches: int = Field(ge=1, le=200)
    max_cost_usd: float = Field(gt=0, le=20)
    max_tokens: int = Field(gt=0)
    max_wall_seconds: int = Field(gt=0)


class BudgetOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_iterations: int | None = Field(default=None, ge=1, le=6)
    max_fetches: int | None = Field(default=None, ge=1, le=200)
    max_cost_usd: float | None = Field(default=None, gt=0, le=20)
    max_tokens: int | None = Field(default=None, gt=0)
    max_wall_seconds: int | None = Field(default=None, gt=0)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question: str = Field(min_length=8, max_length=2000)
    depth: Depth = Depth.STANDARD
    use_memory: bool = True
    budget: BudgetOverrides | None = None
    language: str = "en"


DEPTH_PRESETS: dict[Depth, dict[str, int | float]] = {
    Depth.QUICK: {
        "sub_questions": 3,
        "max_iterations": 1,
        "max_fetches": 10,
        "max_cost_usd": 0.25,
        "max_tokens": 300_000,
        "max_wall_seconds": 180,
    },
    Depth.STANDARD: {
        "sub_questions": 5,
        "max_iterations": 2,
        "max_fetches": 30,
        "max_cost_usd": 0.75,
        "max_tokens": 1_000_000,
        "max_wall_seconds": 420,
    },
    Depth.DEEP: {
        "sub_questions": 8,
        "max_iterations": 4,
        "max_fetches": 80,
        "max_cost_usd": 2.50,
        "max_tokens": 3_000_000,
        "max_wall_seconds": 900,
    },
}
