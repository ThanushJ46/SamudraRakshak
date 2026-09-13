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

## Boundary-aware classification

Early on, the dark-vessel agent treated every silent boat the same. That was
the wrong behaviour twice over: a trawler whose radio died in open water got the
same `high` alert as a foreign vessel sitting inside our waters, and one of our
own fishermen drifting towards the boundary was reported as a threat rather than
as somebody who needs warning.

Every dark vessel is now measured against an illustrative maritime boundary and
sorted into one of four categories:

| Category | Rule | What it means |
|---|---|---|
| 🚩 `foreign_intrusion` | Foreign flag, on our side of the line, any distance | The serious one |
| ⚠️ `border_safety_alert` | Our own flag (`IND`), within 10 km of the line | **Warn a friend, not an accusation** — a local boat may be about to cross |
| ❓ `unidentified_near_zone` | No flag at all, within 15 km, either side | We do not know whose it is |
| ℹ️ `routine_gap` | Everything else, and anything over 200 km away | Almost always just a radio fault |

`routine_gap` vessels are **capped at `low` severity however long they have been
silent, and never cost an AI call.** A boat quiet for ten hours in open water is
a broken radio, not an incident — before the cap it scored `high` and buried the
alerts that actually mattered.

Classification is driven by the vessel's **flag state**, not by its id. Live GFW
ids are meaningless hex strings (`054b3f2fd-d468-e27f-6ba5-03b9b6fefb11`), so an
id-based rule classified every real vessel as unidentified and the whole layer
silently did nothing on live data. GFW does send a `flag` and a real `name`, and
we now keep both — so a live alert reads *Z19 BRIGITTE · Flag: BEL* instead of
hex.

The 200 km cut-off is not cosmetic. The boundary is an infinite line, so without
it every foreign vessel west of that line counted as "on our side" — scanning
the North Sea flagged 17 Belgian and Danish trawlers as intrusions from 9,000 km
away.

> ⚠️ **The boundary is approximate.** `ILLUSTRATIVE_BOUNDARY_LINE` in
> `utils/gfw_client.py` is for demo visualisation only — **not** surveyed or
> legal maritime boundary coordinates. It is drawn dashed on the map and
> labelled as such for exactly that reason. Do not use it for navigation or any
> real enforcement decision.

---

## How the agents work together

The three agents are not three separate tools sharing a page. When the
dark-vessel agent flags something worth responding to, the orchestrator hands
that vessel's position **straight to the route agent** and asks for the fastest
approach from the nearest patrol base:

```
GFW feed -> Dark-Vessel Agent -> classify -> [needs response?]
                                                |
                                                +-- yes -> Route Agent
                                                           -> interception plan
```

The officer gets an action, not a red dot:

> 🚤 **Interception plan** — Nearest patrol base **Rameswaram** · **71.8 km** ·
> ETA **2.1 h** · **211.9 L** fuel

Which vessels get one is decided by category, not by a human pressing a second
button — `foreign_intrusion`, `border_safety_alert` and
`unidentified_near_zone` qualify; a `routine_gap` does not, because dispatching
a boat for a radio fault in open water is a waste. Capped at three per scan, so
a busy area cannot stall the dashboard.

### AI triage: the one decision the model makes

Everywhere else the model writes prose about a conclusion the rules already
reached — delete it and every decision comes out the same. `utils/triage.py` is
different. It hands the model every flagged vessel (flag, category, severity,
distance, times seen before), tells it there is **one** patrol boat available,
and asks for a ranked order **with reasoning**:

> 1. FOR-THA-7719 → 2. IND-TN-1355 → 3. UNK-GHOST-6603 → …
>
> *"The high-severity foreign intrusion is the greatest enforcement priority,
> so I would dispatch the patrol boat to intercept and verify it first. Next,
> the Indian-flagged vessel close to the boundary requires a safety check…"*

That is a judgement across a competing set with no threshold that settles it,
and the reasoning is shown so the officer can disagree with it. If the model is
unavailable the panel falls back to the rule-based order **and says so**, rather
than passing one off as the other.

The division is deliberate: **rules decide anything an enforcement action
depends on** (auditable, reproducible), the **model handles what rules are bad
at** — weighing priorities, and writing Tamil.

### The warning we send our own fishermen

For a `border_safety_alert` the system drafts the message you would actually
radio or text to that boat, **in Tamil and English**:

> TA: நீங்கள் கடல் எல்லையிலிருந்து 6.0 km தொலைவில் இருக்கிறீர்கள். இந்திய
> நீர்நிலைக்கு திரும்பவும், AIS பரிமாற்றியை மீண்டும் இயக்கவும்.
> EN: You are 6.0 km from the boundary. Please turn back toward Indian waters
> and turn AIS on.

Every message ends with a disclaimer appended **in code**, not asked of the
model, so it cannot be separated from the number it qualifies:

```
[DEMO ONLY - distance is measured from an approximate boundary,
 not surveyed coordinates. Not for navigation.]
```

That matters because the distance is measured from a boundary we drew. Sending
an invented number to a real fisherman as fact would be indefensible, so the
caveat travels with the message rather than sitting only in this README.

If Groq is unavailable a fixed bilingual message is used instead, so an officer
always has something to send.

### Memory that affects decisions

`data/flagged_history.json` stores each vessel's last severity, last category,
and how many scans have flagged it. That does two things a severity-only memory
could not:

- **Catches category escalation.** A boat drifting from `routine_gap` into
  `border_safety_alert` is marked as new even though its severity stayed `low` —
  arguably the most important transition there is, and the old check missed it
  entirely.
- **Shows repetition.** "Flagged on 4 scans · escalated from *Routine Gap*" is
  evidence; a single snapshot is not.

Old single-string entries are upgraded on load, so an existing history file
keeps working.

---

## Two apps, on purpose

`app.py` is the coast guard's. `fisherman_app.py` is the crew's. They are
separate applications, not two tabs, and that is a security decision rather
than a styling one.

A fishing crew must **never** see the surveillance picture — which vessels are
flagged, where the patrol boats are, or when one is on its way. An app that
showed them would be a tool for evading enforcement rather than one for
keeping fishermen safe.

The separation is enforced by the import graph, not by a promise. Importing
the fisherman app's dependency chain loads exactly two modules:

```
utils.fisherman_page, utils.zone_utils
```

No `gfw_client`, no `llm_client`, no `triage`, no `orchestrator` — and the GFW
API token is never read into the environment. `ILLUSTRATIVE_BOUNDARY_LINE`
lives in `utils/zone_utils.py` (pure geometry, no network, no secrets) exactly
so the fisherman's app can read the boundary without pulling in the
surveillance client to get it.

The downloadable geofence file inherits the same property: it contains the
boundary and two distance thresholds, and nothing else.

```bash
python -m streamlit run app.py --server.port 8501               # coast guard
python -m streamlit run fisherman_app.py --server.port 8502     # fisherman
```

The coast guard dashboard is organised into three tabs - **Dark Vessel
Monitor** (the default), **Route Optimizer**, and **Debris Cleanup** - so a
demo does not have to scroll. Each app has a link button to the other; they
are separate processes, not two views of one app.

Always pass `--server.port` explicitly. A stray Streamlit process on the
default 8501 will silently block the one you meant to start.

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
{"vessel_id": str,
 "vessel_name": str | None,   # real name from GFW, or the id for demo data
 "flag": str | None,          # ISO-3 flag state, e.g. "IND"; None = unidentified
 "lat": float, "lon": float,
 "last_position_time": "2026-09-12T08:30:00Z"}
```

This module also exports the boundary the classifier measures against:

```python
ILLUSTRATIVE_BOUNDARY_LINE  # [{"lat": 9.0, "lon": 79.6}, {"lat": 10.5, "lon": 80.0}]
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
{"vessel_id": str,
 "vessel_name": str | None,
 "flag": str | None,
 "lat": float, "lon": float,
 "flagged_reason": str,
 "severity": "low" | "medium" | "high",
 "category": "foreign_intrusion" | "border_safety_alert"
            | "unidentified_near_zone" | "routine_gap",
 "distance_to_border_km": float}
```

`flagged_reason` is one plain-English sentence. `medium` and `high` get an
AI-written sentence; `low` and `routine_gap` get a fast templated one, so a busy
scan stays responsive. See **Boundary-aware classification** above for what the
categories mean.

### `utils/zone_utils.py`

```python
distance_point_to_line_km(point: dict, line: list) -> float  # perpendicular, km
which_side(point: dict, line: list) -> "india_side" | "other_side"
vessel_origin(vessel: dict) -> "ours" | "foreign" | "unknown"
classify_vessel(vessel: dict, distance_km: float, side: str) -> str
```

Plain geometry, no dependencies beyond `math`. `distance_point_to_line_km`
measures against the **infinite** line through the two points, not the segment,
so a vessel off the northern end still counts as near the line.
`vessel_origin` prefers the vessel's `flag` and falls back to the `IND-`/`FOR-`/
`UNK-` id prefixes, so older sample data still classifies.

### `utils/sea_route.py`

```python
plan_sea_route(start_port_name: str, end_port_name: str, port_presets: dict) -> list
```

Returns the ordered points a voyage should sail through, including offshore
waypoints. This exists because the route agent computes great-circle lines and
knows nothing about land — asked for Rameswaram → Kochi in one go it drew a
straight line **across Tamil Nadu and Kerala**. The dashboard now calls the
route agent once per short leg and stitches the results, which keeps the path at
sea without changing the agent at all.

> ⚠️ The offshore waypoints are eyeballed approximations for demo
> visualisation — **not** charted shipping lanes or navigational waypoints.

### `agents/route_agent.py`

```python
optimize_route(start: dict, end: dict) -> dict
# -> {"waypoints": [...], "distance_km": float,
#     "baseline_fuel_liters": float, "estimated_fuel_liters": float}
```

**How the saving is earned.** Fuel is charged per kilometre with a wind
penalty — `3.5 L/km x (1 + 0.01 x wind_kmh)` — so rough water genuinely costs
more per km. The agent samples real Open-Meteo wind at five positions offset up
to 30 km either side of the direct line, at three points along the route, picks
the calmest, then **costs both paths and takes the detour only if it actually
comes out cheaper.** If it does not, the direct route is returned and **no
saving is claimed**.

| Route | Straight | Path taken | Baseline | Optimised | Saving |
|---|---|---|---|---|---|
| Rameswaram → Kochi (6 legs) | — | 633.4 km | 2616.5 L | 2552.9 L | 2.4% |
| Rameswaram → Chennai | 434.7 km | 450.4 km | 1809.9 L | 1792.7 L | 0.9% |
| Rameswaram → Tuticorin | 141.9 km | 141.9 km | 576.1 L | 576.1 L | **0.0%** |

The savings are **small — under 1%** — and that is the honest figure. The
0.01 wind coefficient is an approximate demo value, but the saving is
*computed from it and from the path actually chosen*.

> An earlier version applied a fixed 5–15% discount to the baseline regardless
> of the route, and reported "saved 9.9%" on a journey that was 0.2% longer and
> more expensive. That was wrong and has been removed.

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
# -> {"vessels": [...each vessel plus:
#                   "is_new": bool,
#                   "times_flagged": int,
#                   "previous_category": str | None,
#                   "interception": dict | None],
#     "data_source": "live" | "demo" | "demo (live call failed)",
#     "triage": {"ranking": [...], "reasoning": str, "available": bool}}

get_optimized_route(start: dict, end: dict) -> dict
get_cleanup_plan(start: dict) -> dict

plan_interception(vessel: dict) -> dict | None
# -> {"base_name": str, "distance_km": float, "fuel_liters": float,
#     "eta_hours": float, "waypoints": [...]}
```

`PATROL_BASES` (Mandapam, Rameswaram, Tuticorin) and `PATROL_SPEED_KMH` are
approximate demo figures used only to turn a distance into an ETA.

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
├── app.py                      Coast guard dashboard
├── fisherman_app.py            Fisherman's app - SEPARATE on purpose
├── agents/
│   ├── dark_vessel_agent.py    Agent 1 - AIS silence detection
│   ├── route_agent.py          Agent 2 - fuel-efficient routing
│   ├── debris_agent.py         Agent 3 - cleanup route planning
│   └── orchestrator.py         Ties the three together + memory
├── utils/
│   ├── llm_client.py           Shared Groq client
│   ├── gfw_client.py           GFW client + demo generator + boundary line
│   ├── zone_utils.py           Boundary geometry + vessel classification
│   ├── sea_route.py            Offshore waypoints so routes stay at sea
│   ├── triage.py               AI ranking of what to act on first
│   └── fisherman_page.py       Offline geofence file for the boat
├── data/
│   └── sample_debris.json      Sample debris sightings
├── .streamlit/
│   └── config.toml             Streamlit theme (currently defaults)
├── DEFENCE.md                  Answers to the hard questions - read before judging
├── VIDEO_SCRIPT.md             Shot-by-shot demo script
├── CHEATSHEET.md               One-page demo reference
├── UI_PROMPT.md                Brief used for the UI/UX pass
├── test_person_a.py            Foundation layer checks
├── test_person_b.py            Route + debris agent checks
├── requirements.txt
└── .env.example
```

---

## Known limitations

Things we would fix with more time, stated plainly rather than hidden:

- **Weather routing is a marginal gain.** Typically 0-3% depending on the day's
  wind, and exactly 0% where the detour does not pay - the agent then keeps the
  direct route and claims nothing. That is the real figure; we report it rather
  than a flattering one. The wind-to-fuel coefficient (0.01 per km/h) is an
  approximate demo value.
- **The lateral wind search is deliberately narrow (+/-8 km).** A wider search
  finds calmer water but strays from the offshore corridor, and at +/-30 km it
  pushed waypoints inland - the map showed a ship crossing Tamil Nadu. Every
  waypoint on all six port pairs is now verified against real coastal positions
  as being at sea. The cost of the tight search is that wind barely differs
  across 8 km, so savings stay small.
- **Four demo vessels are placed deliberately.** `PINNED_SAMPLE_POSITIONS` in
  `gfw_client.py` puts them at 6, 9, 35 and 55 km from the boundary so a demo
  reliably exercises all four categories instead of depending on luck. The
  classification logic they exercise is not itself rigged, but the demo data is
  arranged — stated here rather than left to be discovered.
- **The Tamil warning is generated, not delivered.** There is no SMS or VHF
  integration. The system identifies which boat needs warning and drafts the
  message; sending it is not built.
- **The fisherman geofence is not packaged as an app.** `utils/fisherman_page.py`
  builds a self-contained HTML file with the boundary and the distance maths
  baked in and no external resources, so the geofence genuinely needs no
  network — its JS was verified to produce the same distances as the Python to
  three decimals. But phone browsers only grant geolocation to a secure origin,
  so opening that file straight off the filesystem does **not** get a GPS fix.
  Shipping it for real means an installable PWA. The logic is finished; the
  packaging is not.
- **Demo scans cost a few AI calls.** Each `medium`/`high` vessel costs one
  call, so a demo scan takes about 5 seconds. Live scans are now *fast* rather
  than slow, but for an unhelpful reason: real vessels are almost always more
  than 200 km from our illustrative boundary, so they classify as `routine_gap`
  and skip the AI entirely. `MAX_RESULTS` in `gfw_client.py` caps a scan at 20
  vessels.
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
- **The illustrative boundary only makes sense in the Gulf of Mannar.** It is a
  single fixed line, so scanning a distant area classifies everything as
  `routine_gap` (see the 200 km guard). A real system would use actual EEZ
  polygons — GFW's event records even carry a `regions` field we do not use yet.
- **Chennai ↔ Kochi clips Pamban.** The Palk Bay → Off Rameswaram leg crosses
  Rameswaram island around 9.3° N. Real vessels use the Pamban channel there, so
  it is not absurd, but zoom in and the line touches land. One extra waypoint
  east of the island would close it.
- **Ports are listed in two places.** `PORT_PRESETS` in `app.py` and
  `PORT_CORRIDOR_INDEX` in `utils/sea_route.py`. Add a port to one and forget the
  other and it silently falls back to a straight line — which is the over-land
  bug all over again. The guard prevents a crash, not a wrong route.
- **A foreign vessel just outside the line reads as routine.** `foreign_intrusion`
  depends on side, so a foreign boat 1.5 km away on *its* side is a `routine_gap`
  while one 90 km inside our side is an intrusion. Correct by the rules, and
  defensible, but a judge may ask.
- **Interception routes are straight lines.** `plan_interception` calls the
  route agent directly rather than going through `utils/sea_route.py`, so a
  long interception can cross land. The legs are usually short and offshore,
  but it is the same limitation the port routing already solves.
- **`utils/zone_utils.py` and `utils/sea_route.py` have no unit tests.** They are
  exercised through `test_person_a.py` and by hand only.

---

## Team

| | Component |
|---|---|
| **Thanush J** | Foundation layer — Groq client, GFW client, Dark-Vessel Agent, `test_person_a.py` |
| **Vishesh Poojary** | Route Optimization Agent, Debris Cleanup Agent, Streamlit dashboard, `test_person_b.py` |
| **Rakshan** | Orchestrator, sample debris data |
