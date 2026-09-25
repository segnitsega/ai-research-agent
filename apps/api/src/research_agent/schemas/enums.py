from enum import StrEnum


class Depth(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Phase(StrEnum):
    RECALL = "recall"
    PLAN = "plan"
    SEARCH = "search"
    READ = "read"
    CRITIQUE = "critique"
    WRITE = "write"
    MEMORIZE = "memorize"


class AgentName(StrEnum):
    PLANNER = "planner"
    SEARCHER = "searcher"
    READER = "reader"
    CRITIC = "critic"
    WRITER = "writer"
    CURATOR = "curator"
    SYSTEM = "system"


class FindingStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class MemoryKind(StrEnum):
    PREFERENCE = "preference"
    FACT = "fact"
    EPISODE = "episode"
