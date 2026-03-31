from __future__ import annotations

import math
from datetime import datetime, UTC


class ResearchService:
    """Lightweight async-like research state machine.

    For local/dev and tests, we advance job state based on elapsed time whenever
    the job is queried, avoiding dependence on background workers.
    """

    STEP_SECONDS = 0.4

    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}

    def create_job(self, job_id: str, payload: dict) -> dict:
        now = datetime.now(UTC)
        job = {
            "job_id": job_id,
            "status": "queued",
            "query": payload["query"],
            "step": 0,
            "max_steps": payload["max_steps"],
            "progress": 0,
            "budget_used": {"tool_calls": 0, "tokens": 0, "elapsed_sec": 0},
            "result": None,
            "created_at": now.isoformat(),
            "started_at": now,
        }
        self.jobs[job_id] = job
        return self._public_job(job)

    def get_job(self, job_id: str) -> dict | None:
        job = self.jobs.get(job_id)
        if not job:
            return None
        self._advance(job)
        return self._public_job(job)

    def _advance(self, job: dict) -> None:
        if job["status"] == "completed":
            return

        elapsed = (datetime.now(UTC) - job["started_at"]).total_seconds()
        completed_steps = min(job["max_steps"], math.floor(elapsed / self.STEP_SECONDS))

        if completed_steps <= 0:
            job["status"] = "planning"
            return

        job["step"] = completed_steps
        job["budget_used"]["tool_calls"] = completed_steps * 2
        job["budget_used"]["tokens"] = completed_steps * 1200
        job["budget_used"]["elapsed_sec"] = int(elapsed)
        job["progress"] = int((completed_steps / job["max_steps"]) * 100)

        if completed_steps >= job["max_steps"]:
            job["status"] = "completed"
            if not job.get("result"):
                job["result"] = {
                    "summary": f"关于“{job['query']}”的研究已完成。",
                    "key_findings": ["发现A", "发现B"],
                    "limitations": ["样本有限"],
                    "citations": [{"type": "web", "title": "Demo", "url": "https://example.com"}],
                }
            return

        job["status"] = "searching" if completed_steps < job["max_steps"] else "synthesizing"

    @staticmethod
    def _public_job(job: dict) -> dict:
        copied = dict(job)
        copied.pop("started_at", None)
        return copied
