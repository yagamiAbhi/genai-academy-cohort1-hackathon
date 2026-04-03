# Multi-Agent Task Orchestrator (Cloud Run Ready)

This project follows the Google ADK multi-agent + MCP codelab patterns to deliver a production-ready, API-based assistant that manages tasks, schedules, and notes. It coordinates multiple agents, persists structured data in a database, and talks to external tools through MCP, making it easy to deploy on Cloud Run.

## Features (mapped to the problem statement)
- Primary coordinator agent that routes work to sub-agents (planner, executor, summarizer).
- Structured data stored in SQLite/Postgres via SQLAlchemy; CRUD for tasks, events, and notes.
- MCP integrations wired exactly like the ADK codelabs (BigQuery + Maps scaffolding; easy to swap for calendar/task/notes MCPs).
- Multi-step workflows using `SequentialAgent` from Google ADK.
- FastAPI HTTP API, ready for Cloud Run deployment with provided Dockerfile.

## Repo layout
- `app/agent.py` – Agent graph (root + sub-agents) mirroring the codelab flow.
- `app/tools/db_tools.py` – Database models and tool functions for tasks/events/notes.
- `app/tools/mcp_tools.py` – MCP toolset wiring (BigQuery + Maps style) per codelabs.
- `app/main.py` – FastAPI entrypoint exposing `/api/agent`.
- `app/config.py` – Environment + logging configuration.
- `app/models.py` – SQLAlchemy models.
- `requirements.txt` – Dependencies matching the codelab stack.
- `Dockerfile` – Cloud Run–ready image.

## Quickstart (local)
1) Python 3.11 recommended.
2) Create a `.env` based on `.env.example`:
```
MODEL=gemini-3.1-pro-preview
DATABASE_URL=sqlite:///./data/app.db
GOOGLE_CLOUD_PROJECT=your-gcp-project
MAPS_API_KEY=your-maps-api-key
```
3) Install deps:
```
python -m venv .venv
. .venv/Scripts/Activate.ps1   # or source .venv/bin/activate
pip install -r requirements.txt
```
4) Run locally:
```
uvicorn app.main:app --reload --port 8080
```
5) Test:
```
curl -X POST http://localhost:8080/api/agent -H "Content-Type: application/json" -d "{\"message\":\"Create a meeting with Alice tomorrow and add a follow-up task\"}"
```

## Deploy to Cloud Run (mirrors the codelab)
```
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/multi-agent
gcloud run deploy multi-agent \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/multi-agent \
  --platform managed --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars MODEL=gemini-3.1-pro-preview,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,MAPS_API_KEY=$MAPS_API_KEY
```

## MCP endpoints
- BigQuery MCP: `https://bigquery.googleapis.com/mcp`
- Maps MCP: `https://mapstools.googleapis.com/mcp`
Swap these with task/calendar/notes MCP servers if available; the wiring stays identical.

## Notes
- The agents and tools follow the codelab style closely (function tools with `ToolContext`, `SequentialAgent` orchestration).
- SQLite is default for simplicity; set `DATABASE_URL` to Postgres for Cloud Run.
- Logging is routed to Cloud Logging when available.

