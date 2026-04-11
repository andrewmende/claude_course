# LMS Chat UI

Browser-based AI tutor chat for the LMS course. Streams responses from Claude via WebSocket.

## Prerequisites

The `lms_server` must be running before you start the UI:

```bash
# Terminal 1 — start the server
cd ../lms_server
pip3 install -r requirements.txt
python3 server.py
```

## Start the UI

```bash
# Terminal 2 — start the dev server
npm install       # first time only
npm run dev
```

Open **http://localhost:5173** in your browser.

## Usage

1. Enter any learner ID on the login screen and click **Start**
2. Chat naturally — the AI tutor will guide you through the course tasks
3. The tutor tracks your progress and advances you to the next task automatically

## How it works

- Messages are sent over a persistent WebSocket at `ws://localhost:8000/ws/{learner_id}`
- The server drives Claude with a tutor system prompt and the `get_current_task` / `submit_answer` tools
- Responses stream token-by-token back to the browser
- The MCP endpoint (`/mcp`) remains available for Claude Code sessions in parallel
