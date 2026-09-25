import time
from dataclasses import dataclass, field
from typing import Literal

from research_agent.schemas.budget import Budget
from research_agent.schemas.enums import AgentName
from research_agent.schemas.run_state import AgentUsage, RunUsage

ResourceKind = Literal["cost", "fetches", "tokens", "time", "iterations"]


@dataclass
class BudgetTracker:
    budget: Budget
    started_at: float = field(default_factory=time.monotonic)
    iterations_used: int = 0
    fetches: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    cost_usd: float = 0.0
    warned: set[ResourceKind] = field(default_factory=set)
    exhausted: ResourceKind | None = None
    by_agent: dict[AgentName, AgentUsage] = field(default_factory=dict)

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def usage_snapshot(self) -> RunUsage:
        return RunUsage(
            requests=self.requests,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            fetches=self.fetches,
            cost_usd=self.cost_usd,
            by_agent=dict(self.by_agent),
        )

    def record_llm(
        self,
        agent: AgentName,
        *,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        self.requests += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost_usd += cost_usd
        prev = self.by_agent.get(
            agent,
            AgentUsage(requests=0, input_tokens=0, output_tokens=0, cost_usd=0.0),
        )
        self.by_agent[agent] = AgentUsage(
            requests=prev.requests + 1,
            input_tokens=prev.input_tokens + input_tokens,
            output_tokens=prev.output_tokens + output_tokens,
            cost_usd=prev.cost_usd + cost_usd,
        )

    def record_fetch(self) -> None:
        self.fetches += 1

    def record_iteration(self) -> None:
        self.iterations_used += 1

    def check_llm_allowed(self) -> None:
        self._check_limits(exclude_iterations=True)

    def check_fetch_allowed(self) -> None:
        if self.exhausted:
            raise BudgetExhaustedError(self.exhausted)
        if self.fetches >= self.budget.max_fetches:
            self.exhausted = "fetches"
            raise BudgetExhaustedError("fetches")
        self._maybe_warn("fetches", self.fetches, self.budget.max_fetches)

    def check_iteration_allowed(self) -> bool:
        if self.iterations_used >= self.budget.max_iterations:
            self.exhausted = "iterations"
            return False
        return True

    def should_write_only(self) -> bool:
        return self.exhausted is not None

    def _check_limits(self, *, exclude_iterations: bool) -> None:
        if self.exhausted:
            raise BudgetExhaustedError(self.exhausted)
        if self.cost_usd >= self.budget.max_cost_usd:
            self.exhausted = "cost"
            raise BudgetExhaustedError("cost")
        total_tokens = self.input_tokens + self.output_tokens
        if total_tokens >= self.budget.max_tokens:
            self.exhausted = "tokens"
            raise BudgetExhaustedError("tokens")
        if self.elapsed_seconds() >= self.budget.max_wall_seconds:
            self.exhausted = "time"
            raise BudgetExhaustedError("time")
        if not exclude_iterations and self.iterations_used >= self.budget.max_iterations:
            self.exhausted = "iterations"
            raise BudgetExhaustedError("iterations")
        self._maybe_warn("cost", self.cost_usd, self.budget.max_cost_usd)
        self._maybe_warn("tokens", float(total_tokens), float(self.budget.max_tokens))
        self._maybe_warn("time", self.elapsed_seconds(), float(self.budget.max_wall_seconds))

    def _maybe_warn(self, resource: ResourceKind, used: float, limit: float) -> None:
        if resource in self.warned:
            return
        if limit > 0 and used / limit >= 0.8:
            self.warned.add(resource)

    def pending_warnings(self) -> list[tuple[ResourceKind, float, float]]:
        out: list[tuple[ResourceKind, float, float]] = []
        total_tokens = self.input_tokens + self.output_tokens
        checks: list[tuple[ResourceKind, float, float]] = [
            ("cost", self.cost_usd, self.budget.max_cost_usd),
            ("fetches", float(self.fetches), float(self.budget.max_fetches)),
            ("tokens", float(total_tokens), float(self.budget.max_tokens)),
            ("time", self.elapsed_seconds(), float(self.budget.max_wall_seconds)),
        ]
        for resource, used, limit in checks:
            if resource in self.warned and limit > 0 and used / limit >= 0.8:
                out.append((resource, used, limit))
        return out

    def clear_warnings(self) -> None:
        self.warned.clear()


class BudgetExhaustedError(Exception):
    def __init__(self, resource: ResourceKind) -> None:
        self.resource = resource
        super().__init__(resource)
