# Project Plan

## What this is
An AI-powered LMS (Learning Management System) where a Claude tutor guides product managers through hands-on coding exercises.

## Components

### `lms_server/` — Backend (FastAPI + MCP)
- Serves MCP tools at `/mcp` for Claude Code CLI sessions
- Serves a WebSocket chat endpoint at `/ws/{learner_id}` for the browser UI
- Claude acts as AI tutor: loads tasks, tracks progress, submits answers automatically
- Notifies the chat UI in real time when a task is loaded or completed

### `chat_ui/` — Frontend (React + Vite)
- Browser-based chat interface for learners
- Connects to the WebSocket backend, streams Claude's responses token-by-token
- Shows blue notification banners when tasks are assigned or completed

### `local_course_files/` — Claude Code tutor config
- `CLAUDE.md` — tutor persona and session rules
- `.claude/commands/` — slash commands (`/start`, `/task`, `/check`, `/next`)
- `.mcp.json` — points Claude Code at the local MCP server

### `lms_server/tasks/` — Course content
- Markdown files (`task_1.md` … `task_N.md`) with task descriptions and completion criteria
- Loaded and served dynamically by the server

---

## Roadmap

### Done
- [x] MCP server with `get_current_task` and `submit_answer` tools
- [x] WebSocket chat endpoint with streaming Claude responses
- [x] React chat UI with learner ID gate and streaming display
- [x] Real-time notifications pushed to chat UI on task load and task completion

### Up next
- [ ] Test that when the student does wrong actions that Claude refuses to call `submit_answer` and move to the next task
- [ ] Multi-learner support improvements (e.g. one WebSocket per tab, not per learner ID)
- [ ] Add claude.md to energy tracker repo
- [ ] Update task 4: there should be a csv report which implemented in the repo, but not surfaced to FE. Student must find out why developer thinks it's rolled out, while it's not visible in the UI. 

### Ideas / Backlog
- [ ] Integration with Jira and Confluence learn to pull information from external sources