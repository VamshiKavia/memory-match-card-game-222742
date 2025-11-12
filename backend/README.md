# Memory Flip Card Game - Backend (FastAPI)

This backend implements a Memory Flip Card game API using FastAPI. It manages in-memory game sessions and exposes endpoints for creating games, flipping cards, retrieving game state, and resetting a game.

- Framework: FastAPI
- Language: Python 3.11+
- Docs:
  - Interactive Swagger UI: http://localhost:3001/docs
  - OpenAPI JSON: http://localhost:3001/openapi.json

## Quick Start

1) Create and activate a virtual environment (recommended)

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

2) Install dependencies

pip install -r requirements.txt

3) Run the development server

uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload

4) Open API docs

- Swagger UI: http://localhost:3001/docs
- Raw spec: http://localhost:3001/openapi.json

## Environment Variables

This service does not require any secrets. You can optionally control the CORS origins and default port when running with a process manager/container.

- PORT: Port for the server to bind (default used in examples: 3001). Note: uvicorn flag --port takes precedence when you run via CLI.
- CORS_ALLOWED_ORIGINS: Comma-separated list of allowed origins for CORS (default is "*" for development). For production, set this to your frontend origin(s).

To use environment variables, create a .env file at the project root and load it via your process manager or shell export before starting uvicorn. Do not commit real .env files; create a .env.example for sharing required keys.

Example .env.example:

PORT=3001
CORS_ALLOWED_ORIGINS=http://localhost:3000

Note: The current app defaults to permissive CORS ("*") during development. For production, you should configure CORS_ALLOWED_ORIGINS and update middleware accordingly if you decide to enforce it.

## API Overview

Base URL: http://localhost:3001

Health
- GET / 
  - Summary: Health Check
  - Description: Verify the API is running
  - 200: {"message": "Healthy"}

Game Endpoints (tag: Game)
- POST /api/game
  - Summary: Create a new game session
  - Body: { "size": "4x4" | "6x6" } (default "4x4")
  - 201: GameSessionView

- GET /api/game/{gameId}
  - Summary: Get game state
  - Path params: gameId (UUID)
  - 200: GameSessionView
  - 404: ErrorResponse (not found/expired)

- POST /api/game/{gameId}/flip
  - Summary: Flip a card
  - Path params: gameId (UUID)
  - Body: { "index": number >= 0 }
  - 200: FlipResult
  - 400: ErrorResponse (invalid operation)
  - 404: ErrorResponse (not found/expired)

- POST /api/game/{gameId}/reset
  - Summary: Reset game session
  - Path params: gameId (UUID)
  - 200: { "session": GameSessionView }
  - 404: ErrorResponse (not found/expired)

## Models (Schemas)

- BoardSize: "4x4" | "6x6"
- CardView: { index: number, isFaceUp: boolean, isMatched: boolean, value?: number | null }
- GameSessionView:
  - session_id: UUID
  - size: BoardSize
  - moveCount: number
  - gameOver: boolean
  - cards: CardView[]
  - firstSelection?: number | null
  - matchedCount: number
  - updatedAt: number (Unix timestamp seconds)
  - createdAt: number (Unix timestamp seconds)
- FlipResult: { session: GameSessionView, turnResolved: boolean, wasMatch?: boolean | null }
- ErrorResponse: { code: string, message: string, details?: object | null }
- NewGameRequest: { size?: BoardSize }
- ResetGameResponse: { session: GameSessionView }

## Regenerating the OpenAPI spec (interfaces/openapi.json)

After changing routes or models:

- Ensure dependencies are installed and the app imports correctly
- Run the generation script from the backend directory:

python -m src.api.generate_openapi

This writes the OpenAPI spec to:
interfaces/openapi.json

The generated file is used by other containers or tools that need the API contract.

## Project Structure

backend/
├── interfaces/
│   └── openapi.json        # Generated OpenAPI spec
├── requirements.txt
└── src/
    └── api/
        ├── __init__.py
        ├── game_routes.py  # FastAPI routes for /api/game
        ├── game_service.py # In-memory game logic and session store
        ├── generate_openapi.py # Script to emit interfaces/openapi.json
        ├── main.py         # FastAPI app, includes CORS and health
        └── models.py       # Pydantic models and enums

## Notes

- Session data is in-memory and ephemeral; restarting the server resets sessions.
- Default session TTL is 120 minutes; expired sessions are evicted on access.
- Deck generation:
  - 4×4 boards (size=16) use a fixed glyph set exactly: [🍎, 🍌, 🍇, 🍉, 🍒, 🥝, 🍑, 🍍]. Each appears twice, then the deck is shuffled.
  - Other sizes (e.g., 6×6) preserve existing behavior where pair IDs are generated as 0..(pairs-1), duplicated, and shuffled.

## Troubleshooting

- Import errors when generating OpenAPI:
  - Run the script from the backend directory: python -m src.api.generate_openapi
  - Ensure virtual environment is activated and dependencies installed.

- 404 on game endpoints:
  - Confirm you are using the correct base path (/api), e.g., POST /api/game, not /game.

- CORS issues:
  - In development, CORS is permissive. If you set CORS_ALLOWED_ORIGINS, ensure it includes your frontend origin.
