from __future__ import annotations

import asyncio
from datetime import datetime


class ResearchService:
    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}

    def create_job(self, job_id: str, payload: dict) -> dict:
        job = {
            "job_id": job_id,
            "status": "queued",
            "query": payload["query"],
            "step": 0,
            "max_steps": payload["max_steps"],
            "progress": 0,
            "budget_used": {"tool_calls": 0, "tokens": 0, "elapsed_sec": 0},
            "result": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.jobs[job_id] = job
        asyncio.create_task(self._run(job_id))
        return job

    def get_job(self, job_id: str) -> dict | None:
        return self.jobs.get(job_id)

    async def _run(self, job_id: str):
        job = self.jobs[job_id]
        job["status"] = "planning"
        for i in range(1, job["max_steps"] + 1):
            await asyncio.sleep(0.2)
            job["step"] = i
            job["status"] = "searching" if i < job["max_steps"] else "synthesizing"
            job["progress"] = int(i / job["max_steps"] * 100)
            job["budget_used"]["tool_calls"] += 2
            job["budget_used"]["tokens"] += 1200
            job["budget_used"]["elapsed_sec"] += 1

        job["status"] = "completed"
        job["result"] = {
            "summary": f"关于“{job['query']}”的研究已完成。",
            "key_findings": ["发现A", "发现B"],
            "limitations": ["样本有限"],
            "citations": [{"type": "web", "title": "Demo", "url": "https://example.com"}],
        }
