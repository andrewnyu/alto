# ALTO Frontend (Next.js + Tailwind)

## Quick Start

1. Install dependencies:

```bash
npm install
```

2. Configure environment variables:

```bash
cp .env.example .env.local
```

3. Run development server:

```bash
npm run dev
```

## Notes

- Uses App Router and Tailwind CSS.
- Google Maps requires `GOOGLE_MAPS_BROWSER_API_KEY`.
- API base URL comes from `PUBLIC_BASE_URL`.
- Vantage control uses storey levels (`Ground` through `L50`) and sends `storey_level` to backend preview API.
