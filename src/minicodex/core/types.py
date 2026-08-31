from dataclasses import dataclass


@dataclass
class StepOutput:
    thought: str = ""
    action: dict | None = None
    observation: dict | None = None
    done: bool = False
    exit_status: str = ""
    submission: str = ""
