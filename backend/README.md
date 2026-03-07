# ALTO Backend (FastAPI)

## Quick Start

1. Create a Python 3.12+ virtual environment.
2. Install dependencies:

```bash
pip install -e .[dev]
```

3. Configure environment variables:

```bash
cp .env.example .env
```

4. Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment

- `MOCK_MODE`: `true` to use deterministic mock providers (no real Google calls)
- `GEMINI_API_KEY`: Gemini API key (used by Google Generative AI SDK)
- `GEMINI_MODEL`: text model name (default `gemini-3`)
- `NANO_BANANA_MODEL`: image model name (default `nano-banana-2`)
- `GOOGLE_MAPS_API_KEY`: Google Maps key for Static Maps + Places + Geocoding
- `GOOGLE_MAPS_BROWSER_API_KEY`: optional browser key if shared across apps
- `GOOGLE_MAP_ID`: Optional map style ID for photorealistic tiles
- `ALLOWED_ORIGINS`: comma-separated list, e.g. `http://localhost:3000`
- `PUBLIC_BASE_URL`: optional base URL behind reverse proxy
