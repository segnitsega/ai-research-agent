from research_agent.schemas.enums import Phase
from research_agent.schemas.run_state import RunState

PHASE_ORDER: list[Phase] = [
    Phase.RECALL,
    Phase.PLAN,
    Phase.SEARCH,
    Phase.READ,
    Phase.CRITIQUE,
    Phase.WRITE,
    Phase.MEMORIZE,
]


def next_incomplete_phase(state: RunState) -> Phase | None:
    for phase in PHASE_ORDER:
        if phase not in state.phase_done:
            return phase
    return None


def mark_phase_done(state: RunState, phase: Phase) -> RunState:
    if phase not in state.phase_done:
        state.phase_done.append(phase)
    return state
