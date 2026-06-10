from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    text: str
    source: str
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None
