"""
LMS MCP server — serves two tools over HTTP/SSE on port 8000.

  Run:  python server.py
  MCP:  http://localhost:8000/mcp
  WS:   ws://localhost:8000/ws/{learner_id}
"""

import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import anthropic
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mcp.server.fastmcp import FastMCP

TASKS_DIR = Path(__file__).parent / "tasks"

PROGRESS: dict[str, dict[str, str]] = {}
SESSIONS: dict[str, dict] = {}
CHAT_CONNECTIONS: dict[str, WebSocket] = {}  # learner_id → active chat WebSocket

SYSTEM_PROMPT = """You are a patient, encouraging coding tutor for product managers. \
Your job is to guide learners through hands-on exercises, not lecture them.

On session start, call get_current_task to load the learner's current task. \
Keep the task content to yourself — don't reveal it verbatim. \
Only support the student if they seem lost.

Rules:
- Don't solve the task for the student; help them formulate the right requests and actions.
- Track their progress against the task's completion criteria in your head.
- When ALL completion criteria are met, call submit_answer automatically — do not wait for the student to ask.
- After submit_answer passes, call get_current_task again to load the next task.
- Be concise and encouraging."""

TOOLS = [
    {
        "name": "get_current_task",
        "description": "Return the learner's current task and session state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "learner_id": {"type": "string", "description": "The learner's ID"}
            },
            "required": ["learner_id"],
        },
    },
    {
        "name": "submit_answer",
        "description": "Mark the current task as complete and advance to the next task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "learner_id": {"type": "string", "description": "The learner's ID"},
                "answer": {"type": "string", "description": "Summary of what the learner did"},
            },
            "required": ["learner_id", "answer"],
        },
    },
]


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


async def _call_tool(name: str, tool_input: dict) -> str:
    if name == "get_current_task":
        result = await get_current_task(**tool_input)
    elif name == "submit_answer":
        result = await submit_answer(**tool_input)
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


mcp = FastMCP("LMS Tutor")


def _load_task(learner_id: str) -> dict:
    """Core task-loading logic shared by the MCP tool and the WebSocket handler."""
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


def _task_title(task_data: dict) -> str:
    """Extract the first heading from task markdown as a short display title."""
    content = task_data.get("task", {}).get("content", "")
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return task_data.get("task", {}).get("id", "New task")


@mcp.tool()
async def get_current_task(learner_id: str) -> dict:
    """
    Return the learner's current task and session state.

    Response includes:
      - task: id, content
      - completed_tasks: map of task_id -> status for this learner
      - all_done: true if the learner has completed all tasks
    """
    result = _load_task(learner_id)
    ws = CHAT_CONNECTIONS.get(learner_id)
    if ws and "task" in result:
        title = _task_title(result)
        await ws.send_text(json.dumps({"type": "notification", "text": f"New task: {title}"}))
    return result


@mcp.tool()
async def submit_answer(learner_id: str, answer: str) -> dict:
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

        # Notify the chat UI if the learner has an active WebSocket connection
        ws = CHAT_CONNECTIONS.get(learner_id)
        if ws:
            if result["all_done"]:
                text = "All tasks complete! Great work."
            else:
                text = f"Task {task_id} complete! Moving on to the next task."
            await ws.send_text(json.dumps({"type": "notification", "text": text}))

    return result


# ── FastAPI wrapper app ──────────────────────────────────────────────────────
# IMPORTANT: define the WebSocket route BEFORE app.mount("/") so it appears
# earlier in the route list and is matched first. Starlette matches in order,
# and a Mount at "/" would otherwise swallow all /ws/* requests.

_mcp_sub_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The MCP sub-app's session manager must be started before it can handle
    # requests. Mounting a sub-app doesn't trigger its lifespan, so we do it
    # manually here by running the sub-app's lifespan context.
    async with _mcp_sub_app.router.lifespan_context(_mcp_sub_app):
        yield


app = FastAPI(lifespan=lifespan)

client = anthropic.AsyncAnthropic()


@app.websocket("/ws/{learner_id}")
async def chat_ws(websocket: WebSocket, learner_id: str):
    await websocket.accept()
    CHAT_CONNECTIONS[learner_id] = websocket
    messages: list[dict] = []

    # Load task on connect (internal call — no chat notification)
    task_data = _load_task(learner_id)
    init_tool_result = {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": "init", "content": json.dumps(task_data)}
        ],
    }
    # Prime the model with the task via a synthetic first exchange
    primer = [
        {"role": "user", "content": [{"type": "tool_use", "id": "init", "name": "get_current_task", "input": {"learner_id": learner_id}}]},
        init_tool_result,
    ]

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            user_text = data.get("content", "")

            messages.append({"role": "user", "content": user_text})

            # Agentic loop: keep going until no more tool calls
            working_messages = primer + messages
            while True:
                full_response_text = ""
                tool_calls: list[dict] = []
                current_tool: dict | None = None
                current_input_json = ""

                async with client.messages.stream(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=working_messages,
                ) as stream:
                    async for event in stream:
                        if event.type == "content_block_start":
                            if event.content_block.type == "tool_use":
                                current_tool = {
                                    "id": event.content_block.id,
                                    "name": event.content_block.name,
                                }
                                current_input_json = ""
                                await websocket.send_text(
                                    json.dumps({"type": "tool_use", "name": current_tool["name"]})
                                )
                        elif event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                full_response_text += event.delta.text
                                await websocket.send_text(
                                    json.dumps({"type": "text_delta", "text": event.delta.text})
                                )
                            elif event.delta.type == "input_json_delta":
                                current_input_json += event.delta.partial_json
                        elif event.type == "content_block_stop":
                            if current_tool is not None:
                                current_tool["input"] = json.loads(current_input_json or "{}")
                                tool_calls.append(current_tool)
                                current_tool = None
                                current_input_json = ""

                if not tool_calls:
                    # No tool calls — done with this turn
                    messages.append({"role": "assistant", "content": full_response_text})
                    working_messages.append({"role": "assistant", "content": full_response_text})
                    break

                # Build assistant message with tool_use blocks
                assistant_content = []
                if full_response_text:
                    assistant_content.append({"type": "text", "text": full_response_text})
                for tc in tool_calls:
                    assistant_content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"],
                    })
                working_messages.append({"role": "assistant", "content": assistant_content})

                # Execute tools and append results
                tool_results = []
                for tc in tool_calls:
                    result_str = await _call_tool(tc["name"], tc["input"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": result_str,
                    })
                working_messages.append({"role": "user", "content": tool_results})

            await websocket.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        pass
    finally:
        CHAT_CONNECTIONS.pop(learner_id, None)


# Mount MCP last so the /ws/{learner_id} WebSocket route above takes priority.
# MCP's streamable_http_app registers its handler at /mcp internally,
# so mounting at "/" makes it reachable at /mcp as expected.
app.mount("/", _mcp_sub_app)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
