# ALTO

ALTO is a skyline-view visualization and synthesis platform.

## Monorepo Structure

- `backend/` FastAPI (Python 3.12+) service with async orchestration and Google AI/Maps adapters.
- `frontend/` Next.js App Router experience implementing the Horizon Interface.

## Backend Setup

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Required Environment Variables

### Backend

- `MOCK_MODE` to disable real Google calls for deterministic local testing.
- `GEMINI_API_KEY` for Gemini/Nano Banana model calls.
- `GEMINI_MODEL` default `gemini-3`.
- `NANO_BANANA_MODEL` default `gemini-flash-image-3`.
- `GOOGLE_MAPS_API_KEY` for Static Maps, Places, Geocoding.
- `GOOGLE_MAPS_BROWSER_API_KEY` optional browser-facing Maps key.
- `GOOGLE_MAP_ID` optional photorealistic map style.
- `FAR_STREETVIEW_ENABLED` toggles far-anchor Street View probing (default `true`).
- `FAR_STREETVIEW_PROBE_RADIUS_M` metadata probe radius for far anchors (default `120`).
- `PUBLIC_BASE_URL` optional base URL behind reverse proxy.

### Frontend

- `GOOGLE_MAPS_BROWSER_API_KEY` (falls back to `GOOGLE_MAPS_API_KEY` if unset)
- `PUBLIC_BASE_URL` for API base URL (default `http://127.0.0.1:8000`)

## Core Endpoint

- `POST /api/v1/preview`
- Request:

```json
{
  "address": "181 Fremont St, San Francisco, CA",
  "lat": 37.79061,
  "lng": -122.39695,
  "storey_level": 18,
  "heading": 150,
  "time_of_day": "GoldenHour"
}
```

The backend concurrently fetches Street View, satellite imagery, elevation, and location context, derives LumenEngine lighting physics, and runs parallel AI synthesis for a skyline narrative plus final render.
