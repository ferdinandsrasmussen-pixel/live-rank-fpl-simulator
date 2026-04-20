# From Prototype to Product: What I Changed and Why It Mattered

*Ferdinand Rasmussen — ESADE Prototyping with Data and AI — Assignment 3*

---

After getting the feedback on A2, I sat with it for a bit. The professor's note — "deploy live, show concrete example outputs, validate with real FPL players, add feedback so users can vote on suggestions and improve the model" — landed less as a checklist and more as a diagnosis. The A2 grade of 8.5 was for the idea and the mechanics. The 1.5 points I left on the table were for **realness**: could another person use this, find it immediately useful, and make the AI smarter over time? The answer was no, and that's what v2 is about.

## What I rebuilt and why

**Moving off Streamlit.** The A2 prototype was a local tool dressed up as a product. Streamlit is excellent for showing something quickly, but it carries a ceiling — users have to paste API keys, there's no persistent state, and the URL is localhost. The professor said "deploy live" and I took that seriously. I rebuilt the frontend in Next.js 14 with TypeScript and Tailwind, and split the backend into a proper FastAPI service. The simulation engine — the Poisson goals, Bernoulli clean sheets, the rank distribution stacking — didn't change at all. It just moved from running in the Streamlit process to a FastAPI endpoint that persists results under a UUID (`run_id`) so the advisor call doesn't have to re-simulate 10,000 iterations.

The key improvement here was vectorising the Monte Carlo. In A2, each player-sim combination looped in Python. In v2, each player's goals and assists are drawn as numpy arrays of shape `(n_sims,)` in a single call — `rng.poisson(lambda, n_sims)` — which runs roughly 20x faster. The statistical model is identical; I just stopped making Python do work numpy was built for.

**The Cohere key went into the backend environment.** In A2, users had to paste their own Cohere API key into a sidebar text box. That was fine when the app was local, but for a live deployment it's a user experience anti-pattern — nobody who lands on a URL from a link is going to create a Cohere account first. The A3 version stores the key server-side in a Railway environment variable. Users get the advisor for free. The free tier's rate limits cap any abuse risk, and this was the right call for what the professor was actually asking for: a demo someone else can use.

**A real database replaced session state.** The biggest structural change. A2 stored everything in `st.session_state` — the simulation results, the advisor outputs, all of it. Fine for one person on one browser tab. But the professor's feedback loop ask — votes → model improvement — is inherently multi-user and persistent. So I added Postgres (SQLite locally, Postgres on Railway) with four tables:

- `suggestions` — keyed on `(gameweek, player_out_id, player_in_id)`. This was the critical design decision. When ten different users get the same "Salah → Mbappé" recommendation, they all vote on *the same row*. The signal compounds rather than scattering.
- `votes` — keyed on `(suggestion_id, session_id)`. One vote per user per suggestion, using a UUID stored in localStorage. No auth required.
- `meta_analyses` — stores LLM-generated community summaries.
- `advisor_runs` — lightweight usage log.

## The three-layer feedback loop

This was the part I was most interested in building, because it's the piece that makes the system actually learn. I'll describe what each layer does and how it's implemented, because "add feedback" in the brief could mean many things.

**Layer 1 is collection.** Every suggestion card has thumbs up/down buttons. A vote hits `/api/votes` and updates the shared `votes` table. The UI updates optimistically — the count changes immediately, the server confirms asynchronously. There's no login, no friction. The session ID is a UUID generated on first visit and persisted in localStorage.

**Layer 2 is injection.** Before the second LLM call (the transfer recommendations), the advisor router queries the votes table for suggestions with net votes ≤ −2 in the last five gameweeks. It builds a prose context block: *"Transfers the community previously rejected: Salah → Mbappé (GW31, MID): community downvoted this..."* and prepends it to the Call 2 prompt. The LLM sees this and is instructed to lower its confidence on similar patterns. This is what I'd call lightweight RAG — the retrieval is a SQL query rather than an embedding search, but the mechanism is the same: past human signals shape the next generation.

When a user's advisor session has been informed by community votes, the UI shows a badge: *"Community-informed — this advice was shaped by N past community votes. Rejected patterns were injected into the LLM prompt."* The professor asked for the loop to be visible, so I made it explicit.

**Layer 3 is summarisation.** In the Community tab there's a "Refresh analysis" button that calls `/api/meta/run`. This endpoint pulls all voted suggestions, builds a structured JSON of liked and rejected patterns, and sends it to Cohere with a prompt asking for a 3-4 sentence community insight plus pattern labels. The result is stored in `meta_analyses` and displayed as "What the community thinks." In the 2-pager I'd describe this as "on-demand meta-analysis designed to run nightly in production" — the architecture is there, the button just exposes it for the demo.

## Demo mode

The professor asked for concrete example outputs. So when anyone lands on the deployed URL, the app auto-loads my team (entry ID 860655, league ID 130708) and fires the simulation immediately. The result is visible without any interaction — rank distribution chart, P10/P50/P90 reference lines, rivals table, player projections. A banner explains what's happening and offers a one-click exit to use your own team.

The rank chart is the one visual I spent the most time on. A2 had a `st.bar_chart` which is fine, but the whole story of the model — that it produces a distribution, not a point estimate — deserves a proper visualisation. The Recharts `BarChart` has vertical `ReferenceLine` overlays at P10, P50, and P90, labelled in green/blue/red. Single colour bars, no rainbow. It makes the "you're not getting a rank, you're getting a range of probable ranks" point in one glance.

## What I didn't change

The Monte Carlo engine's statistical model is identical to A2 — Poisson goals, Poisson assists, Bernoulli clean sheets, historical per-90 rates from the FPL bootstrap. The two-call LLM architecture is the same: risk analysis first, recommendations second, Monte Carlo validation per recommendation. I made these choices deliberately. The professor's feedback was about deployment and feedback, not about the core model being wrong. I improved what needed improving and left what was already working alone.

---

*Word count: ~950 words*
