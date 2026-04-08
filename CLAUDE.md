# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## LMS Server (external)

The MCP server lives at `/Users/amende/PycharmProjects/lms_server/` — it is a separate project, not part of this repo.

Start it before opening a course session:

```bash
cd /Users/amende/PycharmProjects/lms_server
pip install -r requirements.txt
python server.py
```

It runs on `http://localhost:8000`. Claude connects via streamable-http at `/mcp`; REST endpoints are at `/api/*`.

## MCP connection

`local_course_files/.mcp.json` points Claude at `http://localhost:8000/mcp` (streamable-http transport). No credentials required for localhost.

## Course Files

`local_course_files/` contains:
- `CLAUDE.md` — tutor persona and session behavior rules for the AI tutor role
- `progress.md` — per-session learner state (learner_id, current task, hint index, completed tasks); written by the tutor, not the MCP server
- `.mcp.json` — MCP server connection config
- `.claude/commands/` — slash command definitions (`/start`, `/task`, `/check`, `/next`)
