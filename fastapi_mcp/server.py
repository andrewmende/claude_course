"""
Unified LMS service: FastAPI REST routes + FastMCP tools in one process.

  Claude Code (stdio):  python server.py
  REST API:             uvicorn server:app --reload
"""

from datetime import date
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Task loading — each task is a .md file in the tasks/ directory
# ---------------------------------------------------------------------------

TASKS_DIR = Path(__file__).parent / "tasks"


def _task_order() -> list[str]:
    return sorted(p.stem for p in TASKS_DIR.glob("task_*.md"))



# learner_id -> { task_id -> status }
PROGRESS: dict[str, dict[str, str]] = {}

# learner_id -> { current_task_id, session_started }
SESSIONS: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_session(learner_id: str) -> dict:
    if learner_id not in SESSIONS:
        SESSIONS[learner_id] = {
            "learner_id": learner_id,
            "current_task_id": _task_order()[0],
            "session_started": date.today().isoformat(),
        }
    return SESSIONS[learner_id]


def _next_task_id(current_task_id: str) -> str | None:
    order = _task_order()
    idx = order.index(current_task_id) if current_task_id in order else -1
    next_idx = idx + 1
    return order[next_idx] if next_idx < len(order) else None


# ---------------------------------------------------------------------------
# FastAPI REST routes (for debugging / external tooling)
# ---------------------------------------------------------------------------

app = FastAPI(title="LMS")


class SubmissionRequest(BaseModel):
    task_id: str
    learner_id: str
    answer: str


class ProgressUpdate(BaseModel):
    task_id: str
    status: Literal["completed", "in_progress"]


class SessionUpdate(BaseModel):
    current_task_id: str | None = None


@app.get("/api/tasks/{task_id}")
def route_get_task(task_id: str):
    path = TASKS_DIR / f"{task_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"id": task_id, "content": path.read_text()}


@app.post("/api/submissions")
def route_submit_answer(body: SubmissionRequest):
    if not (TASKS_DIR / f"{body.task_id}.md").exists():
        raise HTTPException(status_code=404, detail=f"Task '{body.task_id}' not found")
    passed = True
    return {
        "task_id": body.task_id,
        "learner_id": body.learner_id,
        "passed": passed,
        "score": 100 if passed else 0,
        "feedback": "Great job!"
    }


@app.get("/api/progress/{learner_id}")
def route_get_progress(learner_id: str):
    return {"learner_id": learner_id, "tasks": PROGRESS.get(learner_id, {})}


@app.patch("/api/progress/{learner_id}")
def route_update_progress(learner_id: str, body: ProgressUpdate):
    PROGRESS.setdefault(learner_id, {})[body.task_id] = body.status
    return {"learner_id": learner_id, "task_id": body.task_id, "status": body.status}


@app.get("/api/sessions/{learner_id}")
def route_get_session(learner_id: str):
    return _get_session(learner_id)


@app.patch("/api/sessions/{learner_id}")
def route_update_session(learner_id: str, body: SessionUpdate):
    session = _get_session(learner_id)
    if body.current_task_id is not None:
        session["current_task_id"] = body.current_task_id
    return session


# ---------------------------------------------------------------------------
# MCP tools — the only two Claude needs
# ---------------------------------------------------------------------------

mcp = FastMCP("LMS Tutor")


@mcp.tool()
def get_current_task(learner_id: str) -> dict:
    """
    Return the learner's current task and session state.

    Response includes:
      - task: id, title, content
      - completed_tasks: map of task_id -> status for this learner
      - all_done: true if the learner has completed all tasks
    """
    session = _get_session(learner_id)
    task_id = 'task_2' # session["current_task_id"]
    path = TASKS_DIR / f"{task_id}.md"
    if not path.exists():
        return {"error": f"Task '{task_id}' not found"}
    return {
        "task": {"id": task_id, "content": path.read_text()},
        "completed_tasks": PROGRESS.get(learner_id, {}),
        "all_done": False,
    }


@mcp.tool()
def submit_answer(learner_id: str, answer: str) -> dict:
    """
    Grade the learner's answer for their current task.

    On pass: marks the task completed and advances to the next task automatically.
    On fail: returns feedback; the learner should try again.

    Response includes:
      - passed: bool
      - score: 0 or 100
      - feedback: grading message
      - next_task_id: id of the next task (if passed and one exists), else null
      - all_done: true if the learner just completed the final task
    """
    session = _get_session(learner_id)
    task_id = session["current_task_id"]

    if not (TASKS_DIR / f"{task_id}.md").exists():
        return {"error": f"Task '{task_id}' not found"}

    passed = "def " in answer and "return" in answer
    result = {
        "passed": passed,
        "score": 100 if passed else 0,
        "feedback": "Looks good!" if passed else "Make sure your answer defines a function and returns a value.",
        "next_task_id": None,
        "all_done": False,
    }

    if passed:
        PROGRESS.setdefault(learner_id, {})[task_id] = "completed"
        next_id = _next_task_id(task_id)
        if next_id:
            session["current_task_id"] = next_id
            result["next_task_id"] = next_id
        else:
            result["all_done"] = True

    return result


# ---------------------------------------------------------------------------
# Entrypoints
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if "--http" in sys.argv:
        uvicorn.run(app, host="127.0.0.1", port=8000)
    else:
        mcp.run()  # stdio for Claude Code
