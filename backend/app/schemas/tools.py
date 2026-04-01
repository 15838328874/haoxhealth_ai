from pydantic import BaseModel, Field


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: dict
    session_id: str
    idempotency_key: str


class ResearchCreateRequest(BaseModel):
    session_id: str
    query: str
    max_steps: int = Field(default=6, ge=1, le=12)
    max_tool_calls: int = Field(default=20, ge=1, le=100)
    max_tokens: int = Field(default=40000, ge=1000, le=200000)
    timeout_sec: int = Field(default=120, ge=10, le=900)
