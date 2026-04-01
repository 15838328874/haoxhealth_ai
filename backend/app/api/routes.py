from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.schemas.tools import ToolExecuteRequest, ResearchCreateRequest
from app.services.conversation import ConversationEngine
from app.services.llm import DashScopeClient
from app.services.research import ResearchService
from app.services.tooling import ToolRegistry, ToolExecutor

router = APIRouter(prefix="/api")
registry = ToolRegistry()
tool_executor = ToolExecutor(registry)
llm_client = DashScopeClient()
engine = ConversationEngine(tool_executor, llm_client)
research_service = ResearchService()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/tools")
async def list_tools():
    tools = [tool.__dict__ for tool in registry.list_tools()]
    return {"data": {"tools": tools}}


@router.post("/tools/execute")
async def execute_tool(request: ToolExecuteRequest):
    try:
        result = await tool_executor.execute(request.tool_name, request.arguments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"request_id": request.idempotency_key, "data": result}


@router.post("/chat/{session_id}/stream")
async def chat_stream(session_id: str, request: ChatRequest):
    async def event_generator():
        async for event in engine.stream_reply(
            request.message,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/research/jobs")
async def create_research_job(payload: ResearchCreateRequest):
    job_id = f"rj_{uuid.uuid4().hex[:10]}"
    job = research_service.create_job(job_id, payload.model_dump())
    return {"data": job}


@router.get("/research/jobs/{job_id}")
async def get_research_job(job_id: str):
    job = research_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
    return {"data": job}


@router.get("/research/jobs/{job_id}/result")
async def get_research_result(job_id: str):
    job = research_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="JOB_NOT_COMPLETED")
    return {"data": job.get("result")}
