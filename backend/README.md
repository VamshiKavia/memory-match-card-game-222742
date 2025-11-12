# Memory Flip Card Backend (FastAPI)

FastAPI backend for the Memory Flip Card game. Provides APIs to create/reset game sessions, flip cards with deterministic shuffling, and a simple health endpoint.

## Run locally

- Python 3.11+
- Install deps:
  pip install -r requirements.txt

- Start server:
  uvicorn src.api.main:app --host 0.0.0.0 --port 3001

The OpenAPI docs will be at http://localhost:3001/docs

## Environment

CORS will allow typical localhost origins by default. If you need to set a specific origin:
- FRONTEND_ORIGIN (optional): e.g., http://localhost:3000

Note: Do not put secrets in these env vars.

## API Summary

- GET /           Health check
- POST /api/game  Create a new game session
  Body: { "size": "4x4" | "6x6" }
  Returns: GameSessionView

- GET /api/game/{gameId}  Get session snapshot
- POST /api/game/{gameId}/flip  Flip a card index within the session
  Body: { "index": number }
  Returns: FlipResult { session, turnResolved, wasMatch }

- POST /api/game/{gameId}/reset  Reset session to a fresh game preserving size

See /openapi.json for full schema.

## Tests

A small test exists for deck and masking logic and uses the internal service:
  pytest

