"""
LMS MCP server — serves two tools over HTTP/SSE on port 8000.

  Run:  python server.py
  MCP:  http://localhost:8000/mcp
"""

from datetime import date
from pathlib import Path

import uvicorn
from mcp.server.fastmcp import FastMCP

TASKS_DIR = Path(__file__).parent / "tasks"

PROGRESS: dict[str, dict[str, str]] = {}
SESSIONS: dict[str, dict] = {}


def _task_order() -> list[str]:
    return sorted(p.stem for p in TASKS_DIR.glob("task_*.md"))


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


mcp = FastMCP("LMS Tutor")


@mcp.tool()
def get_current_task(learner_id: str) -> dict:
    """
    Return the learner's current task and session state.

    Response includes:
      - task: id, content
      - completed_tasks: map of task_id -> status for this learner
      - all_done: true if the learner has completed all tasks
    """
    session = _get_session(learner_id)
    task_id = session["current_task_id"]
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

    On pass: marks the task completed and advances to the next task.
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

    passed = True
    result = {
        "passed": passed,
        "score": 100 if passed else 0,
        "feedback": "Good job!",
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


if __name__ == "__main__":
    mcp.settings.host = "127.0.0.1"
    mcp.settings.port = 8000
    mcp.run(transport="streamable-http")
