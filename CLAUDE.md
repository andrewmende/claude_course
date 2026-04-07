# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MCP Server

`fastapi_mcp/server.py` is a unified service: FastAPI REST routes and FastMCP tools in one file, sharing in-memory LMS data directly (no HTTP round-trip between layers). It replaces both `lms_mock/` and the old Node.js server.

### Running

```bash
cd fastapi_mcp
pip install -r requirements.txt

# stdio mode — used by Claude Code (registered in .claude/settings.local.json):
python server.py

# HTTP mode — exposes the REST API on :8000:
python server.py --http
# or: uvicorn server:app --reload
```

### Architecture

Core logic lives in plain functions (`_get_task`, `_submit_answer`, etc.). Both layers call them directly:

| Layer | How |
|---|---|
| FastAPI routes | `@app.get/post/patch` — raises `HTTPException` on error |
| FastMCP tools | `@mcp.tool()` — returns `{"error": "..."}` on error |

| Tool / Route | Method | Path |
|---|---|---|
| `get_task(task_id)` | GET | `/api/tasks/:task_id` |
| `submit_answer(task_id, learner_id, answer)` | POST | `/api/submissions` |
| `get_progress(learner_id)` | GET | `/api/progress/:learner_id` |
| `update_progress(learner_id, task_id, status)` | PATCH | `/api/progress/:learner_id` |

To add a tool: add a `_logic_fn` and decorate it with both `@app.<method>` and `@mcp.tool()`.

## Course Files

`local_course_files/` contains:
- `CLAUDE.md` — tutor persona and session behavior rules for the AI tutor role
- `progress.md` — per-session learner state (learner_id, current task, hint index, completed tasks); written by the tutor, not the MCP server
