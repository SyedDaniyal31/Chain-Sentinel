# ChainSentinel Frontend

Next.js 15 dashboard for ChainSentinel scan operations.

## Setup

```powershell
cd frontend
npm ci
```

Create `.env.local` (optional):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Run

```powershell
npm run dev
```

Open http://localhost:3000

## Pages

| Route | Purpose |
|-------|---------|
| `/` | Dashboard — create scans, view results |
| `/scan/[id]` | Scan detail view |
| `/history` | Paginated scan history |

## Build

```powershell
npm run build
npm start
```

## API client

HTTP calls are in `src/lib/api.ts`. The base URL defaults to `http://localhost:8000` when `NEXT_PUBLIC_API_URL` is unset.
