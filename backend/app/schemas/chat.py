from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 1200
    tool_mode: str = "auto"


class SessionCreateRequest(BaseModel):
    title: str = "New Chat"


class SessionResponse(BaseModel):
    id: str
    title: str


class CompressRequest(BaseModel):
    custom_instructions: str | None = None
