# 🌊 Samudra Rakshak

**Maritime logistics and deep-sea preservation dashboard**
Built for Bit N Build '26 — problem statement: *Maritime Logistics & Deep-Sea Preservation*

A dashboard for a maritime authority such as the Coast Guard. Three AI agents
watch a stretch of ocean and answer three different questions: *who is hiding*,
*what is the cheapest way there*, and *how do we clean it up*.

---

## What it does

| Agent | Question it answers | Entry point |
|---|---|---|
| 🛰️ **Dark-Vessel Agent** | Which ships have stopped broadcasting their position near a fishing zone? A vessel going dark can mean a broken radio — or someone switching it off to fish illegally. | `find_dark_vessels()` |
| 🧭 **Route Optimization Agent** | Given a start and an end point, what is the most fuel-efficient route? | `optimize_route()` |
| 🧹 **Debris Cleanup Agent** | Given a list of ocean debris sightings, what is the shortest route for a cleanup boat to collect all of them? | `plan_cleanup_route()` |

An **orchestrator** ties the three together, keeps a small memory of what it has
already flagged, and hands one combined result to a Streamlit dashboard with a
live map.

There is deliberately **no agent framework** — no CrewAI, no LangGraph. Every
agent is a plain Python function. That was a conscious choice: faster to build,
far easier to debug under time pressure, and much easier to explain.

---

## Quick start

**1. Install** (Python 3.10+; tested on 3.13)

```bash
pip install -r requirements.txt
```

**2. Add your API keys**

Copy `.env.example` to `.env` and fill in two free keys:

```
GROQ_API_KEY=      # free from https://console.groq.com/keys
GFW_API_TOKEN=     # free from https://globalfishingwatch.org/our-apis/
```

`.env` is gitignored — never commit it.

**3. Check the foundation layer works**

```bash
python test_person_a.py
```

This passes **without** any keys. With no keys it falls back to sample vessels
and templated explanations, and tells you clearly which one you are looking at.

**4. Run the dashboard**

```bash
python -m streamlit run app.py
```

> Use `python -m streamlit`, not bare `streamlit` — on a default Windows install
> `streamlit.exe` is not on PATH.

---

## The honest bit: live data vs demo data

This is worth understanding before you judge the severity levels.

The **public** Global Fishing Watch API does not serve live AIS tracking. It
serves **daily-batch fishing events**, which are hours or days old. Our
dark-vessel severity bands are based on how long a vessel has been silent:

| Silent for | Severity |
|---|---|
| 30 – 90 minutes | `low` |
| 90 minutes – 4 hours | `medium` |
| 4+ hours | `high` |

Against real GFW data, *every* vessel is already days stale — so live data can
only ever produce `high`. Never `low`, never `medium`.

We chose to **show that rather than hide it**. The dashboard has a data-source
toggle, and a badge that reports which source *actually* ran:

| Badge | Meaning |
|---|---|
| 🟢 Live Data | Positions came from the live GFW feed |
| 🟡 Demo Data | Sample data, chosen deliberately |
| 🟠 Demo Data (live call failed) | Live was requested, the call failed, sample data is shown instead |

That third state is the important one. GFW's public API is genuinely flaky and
many ocean areas contain no fishing events at all, so a live request often
cannot be served. Rather than quietly substituting fake vessels and passing them
off as real, the page says so.

**Demo mode** uses a generated spread of staleness, so all three severity bands
appear and the logic is actually visible.

---

## Function contracts

Everything below is stable — the dashboard and orchestrator depend on these
exact shapes.

### `utils/llm_client.py`

```python
ask_ai(prompt: str) -> str
```

One shared entry point to Groq (`openai/gpt-oss-120b`). Raises `ValueError` if
`GROQ_API_KEY` is missing, so a misconfigured `.env` is impossible to miss.

### `utils/gfw_client.py`

```python
get_vessel_positions(area: dict) -> list[dict]    # real data; RAISES on failure
generate_sample_vessels(area: dict) -> list[dict] # demo data; never raises
```

`area` is always:

```python
{"min_lat": float, "max_lat": float, "min_lon": float, "max_lon": float}
```

Both return a list of:

```python
{"vessel_id": str, "lat": float, "lon": float, "last_position_time": "2026-09-12T08:30:00Z"}
```

There is **no hidden fallback** between them. `get_vessel_positions` raises on a
missing token, a network failure, or an empty area, and the *caller* decides
what to do — which is why the dashboard can always tell you what really ran.

### `agents/dark_vessel_agent.py`

```python
find_dark_vessels(vessel_list: list[dict]) -> list[dict]
```

Takes the list above, returns only the suspicious ones:

```python
{"vessel_id": str, "lat": float, "lon": float,
 "flagged_reason": str, "severity": "low" | "medium" | "high"}
```

`flagged_reason` is one plain-English sentence. `medium` and `high` get an
AI-written sentence; `low` gets a fast templated one, so a busy scan stays
responsive.

### `agents/route_agent.py`

```python
optimize_route(start: dict, end: dict) -> dict
# -> {"waypoints": [...], "distance_km": float,
#     "baseline_fuel_liters": float, "estimated_fuel_liters": float}
```

### `agents/debris_agent.py`

```python
plan_cleanup_route(start: dict, debris_list: list[dict]) -> dict
# -> {"visit_order": [...], "waypoints": [...], "total_distance_km": float}
```

Debris sightings come from `data/sample_debris.json`:

```python
{"debris_id": "D1", "lat": 9.32, "lon": 79.35, "description": "Cluster of plastic bottles"}
```

### `agents/orchestrator.py`

```python
check_dark_vessels(area: dict = None, use_demo_data: bool = False) -> dict
# -> {"vessels": [...each with an extra "is_new": bool...],
#     "data_source": "live" | "demo" | "demo (live call failed)"}

get_optimized_route(start: dict, end: dict) -> dict
get_cleanup_plan(start: dict) -> dict
```

The orchestrator keeps a small memory in `data/flagged_history.json` (gitignored
— it is a runtime artifact).

**Memory changes how a vessel is *presented*, never whether it appears.** Every
currently-flagged vessel is returned on every scan; memory only sets `is_new`,
so newly flagged or escalated vessels can be highlighted without ever hiding one
that is still genuinely dark. An earlier version returned only new vessels,
which blanked the map on a second scan and looked broken.

---

## Project layout

```
SamudraRakshak/
├── app.py                      Streamlit dashboard
├── agents/
│   ├── dark_vessel_agent.py    Agent 1 - AIS silence detection
│   ├── route_agent.py          Agent 2 - fuel-efficient routing
│   ├── debris_agent.py         Agent 3 - cleanup route planning
│   └── orchestrator.py         Ties the three together + memory
├── utils/
│   ├── llm_client.py           Shared Groq client
│   └── gfw_client.py           Global Fishing Watch client + demo generator
├── data/
│   └── sample_debris.json      Sample debris sightings
├── test_person_a.py            Foundation layer checks
├── test_person_b.py            Route + debris agent checks
├── requirements.txt
└── .env.example
```

---

## Known limitations

Things we would fix with more time, stated plainly rather than hidden:

- **Live scans are slow.** Each `medium`/`high` vessel costs one AI call, and
  real GFW data is always `high` severity — so a busy area of 17 vessels takes
  roughly 60 seconds. Demo mode is about 6 seconds. `MAX_RESULTS` in
  `gfw_client.py` caps this at 20 vessels; the next step would be capping how
  many vessels get an AI sentence at all.
- **Severity bands cannot be exercised by live data**, for the batch-data reason
  explained above.
- **The default area (Gulf of Mannar) has no live GFW coverage.** It returns zero
  fishing events, so it always falls back to demo. The dashboard's *North Sea*
  preset is there to demonstrate the live feed actually working.
- **`streamlit` and `folium` are intentionally unpinned** (floors only). The
  previously pinned `streamlit==1.32.0` requires `numpy<2`, which has no Python
  3.13 wheel — pip tried to compile numpy from source and failed with
  `NumPy requires GCC >= 8.4`, making the project impossible to install. Please
  do not re-pin them without checking Python 3.13 first.
- **Route and debris sections of the dashboard** are still to be wired into
  `app.py`; both agents and their orchestrator entry points are ready.

---

## Team

| | Component |
|---|---|
| **Thanush J** | Foundation layer — Groq client, GFW client, Dark-Vessel Agent, `test_person_a.py` |
| **Vishesh Poojary** | Route Optimization Agent, Debris Cleanup Agent, Streamlit dashboard, `test_person_b.py` |
| **Rakshan** | Orchestrator, sample debris data |
