# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## LMS Server

The server lives at `lms_server/`. Start it before opening a course session or using the chat UI:

```bash
cd lms_server
pip3 install -r requirements.txt
python3 server.py
```

It runs on `http://localhost:8000`.
- Claude Code connects via streamable-http at `/mcp`
- The chat UI connects via WebSocket at `ws://localhost:8000/ws/{learner_id}`

## Chat UI

A browser-based AI tutor chat lives at `chat_ui/`. Start it in a second terminal:

```bash
cd chat_ui
npm install       # first time only
npm run dev
```

Open `http://localhost:5173`, enter a learner ID, and start chatting.

> The server must be running first — the UI connects to it on load.

## MCP connection

`local_course_files/.mcp.json` points Claude at `http://localhost:8000/mcp` (streamable-http transport). No credentials required for localhost.

## Course Files

`local_course_files/` contains:
- `CLAUDE.md` — tutor persona and session behavior rules for the AI tutor role
- `progress.md` — per-session learner state (learner_id, current task, hint index, completed tasks); written by the tutor, not the MCP server
- `.mcp.json` — MCP server connection config
- `.claude/commands/` — slash command definitions (`/start`, `/task`, `/check`, `/next`)
