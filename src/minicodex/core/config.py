from pydantic import BaseModel


class AgentConfig(BaseModel):
    step_limit: int = 50
    token_limit: int = 200_000
    cost_limit: float = 5.0
    wall_time_limit_seconds: int = 0
