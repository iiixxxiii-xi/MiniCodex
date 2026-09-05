"""Task model."""
from dataclasses import dataclass


@dataclass
class Task:
    id: str
    priority: int
    max_retries: int = 2
    failures: int = 0
