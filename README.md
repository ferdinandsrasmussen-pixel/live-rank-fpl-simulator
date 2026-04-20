# FPL Mini-League Rank Simulator v2

Assignment 3 — ESADE Prototyping with Data and AI  
Upgrade of the A2 Streamlit prototype (8.5/10) into a deployed full-stack application.

**Live demo:** `deployment.txt`  
**Repository:** `repository.txt`

---

## What's new in v2

| Feature | A2 | v2 |
|---|---|---|
| Frontend | Streamlit (local only) | Next.js 14, TypeScript, Tailwind, shadcn/ui |
| Backend | In-process Python | FastAPI (Railway) |
| Database | Session state (in-memory) | Postgres / SQLite — suggestions, votes, meta-analyses |
| LLM key | User pastes in UI | Backend env var — real users never touch it |
| Feedback loop | None | 3-layer: vote → RAG injection → community meta-analysis |
| Deployment | `streamlit run` | Vercel (frontend) + Railway (backend + Postgres) |
| Demo mode | Manual ID entry | Auto-loads team 860655 on landing |

---

## Local development

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free Cohere API key (dashboard.cohere.com)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set COHERE_API_KEY

uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install

cp .env.local.example .env.local
# Edit .env.local — NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
```

Open `http://localhost:3000`

---

## Deployment

### Backend → Railway

1. Create a new Railway project, connect this repo.
2. Set the **root directory** to `v2/backend`.
3. Railway auto-detects the `Procfile` (`uvicorn main:app --host 0.0.0.0 --port $PORT`).
4. Add a **Postgres** plugin in Railway — the `DATABASE_URL` env var is injected automatically.
5. Set env vars: `COHERE_API_KEY=your-key`.
6. Deploy. Copy the Railway public URL.

**Known gotcha:** Railway provides `postgres://` URLs. The backend rewrites these to `postgresql://` automatically in `database.py`.

### Frontend → Vercel

1. Import the repo to Vercel. Set **root directory** to `v2/frontend`.
2. Set env var: `NEXT_PUBLIC_API_URL=https://your-railway-app.up.railway.app`
3. Deploy.

---

## Architecture overview

```
Browser (Vercel)                   Railway
┌─────────────────┐                ┌────────────────────────────┐
│  Next.js 14 App │  REST (HTTPS)  │  FastAPI                   │
│  ─────────────  │ ────────────►  │  ─────────────             │
│  SimulatorPanel │                │  /api/simulate             │
│  AdvisorPanel   │                │    → Monte Carlo engine     │
│  SuggestionCard │                │    → run_store (in-memory)  │
│  MetaAnalysis   │                │                            │
│  (vote buttons) │                │  /api/advisor              │
└─────────────────┘                │    → LLM Call 1 (risk)     │
                                   │    → LLM Call 2 (recs)     │
                                   │    → MC validation         │
                                   │    → community RAG inject  │
                                   │                            │
                                   │  /api/votes                │
                                   │  /api/meta                 │
                                   │                            │
                                   │  Postgres                  │
                                   │  ─────────                 │
                                   │  suggestions (GW×out×in)   │
                                   │  votes (suggestion×session)│
                                   │  meta_analyses             │
                                   │  advisor_runs              │
                                   └────────────────────────────┘
```

## Three-layer feedback loop

**Layer 1 — Collection** (`SuggestionCard.tsx`)  
Thumbs up/down on each suggestion. Stored in `votes` table, unique per `(suggestion_id, session_id)`. Same suggestion across different users accumulates on the same row.

**Layer 2 — RAG injection** (`routers/advisor.py → llm.py`)  
Before LLM Call 2, suggestions with net votes ≤ −2 are fetched and prepended to the prompt: *"The community previously rejected these transfers — factor this into your confidence scoring."*

**Layer 3 — Meta-analysis** (`MetaAnalysis.tsx → /api/meta/run`)  
On-demand button triggers a Cohere call that reads all vote patterns, identifies liked/rejected archetypes, and stores a prose summary shown in the Community tab.
