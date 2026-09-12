# Maritime Guardian — Execution Playbook
### Bit N Build '26 — Maritime Logistics & Deep-Sea Preservation

This is your single reference document for the next 24 hours. Everyone on the team should read Section 0 and their own Section 4 task right now, then keep this open as you work.

---

## 0. Do This First (first 15 minutes, all 3 people together)

1. **Get an LLM API key** — fastest option: go to https://aistudio.google.com/apikey, sign in with any Google account, click "Create API key." It's free and instant. (If someone already has an OpenAI or Claude key, that works too — just tell whoever writes `llm_client.py` which one you're using.)
2. **Get a Global Fishing Watch API token** — go to https://globalfishingwatch.org/our-apis/ , register (free, instant, no approval wait — we already checked this). This gives you real ship-tracking data.
3. **Create the GitHub repo** — one person creates it, name it something like `maritime-guardian`, set visibility to **Public** (required by the rules), add the other 2 as collaborators immediately.
4. **Everyone clones the repo locally** and confirms Python 3.10+ is installed (`python3 --version`).

Do not start writing solution code before your hackathon's official 11am start time — steps 1-4 above are just account/access setup, not solution code, so they're safe to do early.

---

## 1. What We're Building (one paragraph)

**Maritime Guardian**: a dashboard for a maritime authority (like the Coast Guard) with 3 AI agents working together. One agent finds the most fuel-efficient route between two points. One agent watches real ship-tracking data and flags boats that suspiciously go dark near a fishing zone. One agent takes a list of ocean debris sightings and plans the smartest route to collect them all. An orchestrator ties the three together, remembers what it already found, and shows everything on one live map.

---

## 2. Architecture (in plain words)

Think of it as 4 simple pieces, each one a separate Python file, so nobody steps on each other's work:

- **`app.py`** — the dashboard. This is the only thing that shows a screen to the user. It's built with Streamlit (a Python tool that turns a plain script into a website with almost no extra code — no HTML/CSS/JavaScript needed).
- **Three agent files** — each one is just a Python function that does ONE job: given some input, produce some output. They don't need to know about each other.
- **`orchestrator.py`** — a small "traffic controller" that calls the right agent, keeps a simple memory (just a Python list or a JSON file — no database needed) of what's already been flagged, and returns everything the dashboard needs to show.
- **`llm_client.py`** — one shared function that all agents use to talk to the LLM (Gemini/OpenAI/Claude), so you only write the "call the AI" logic once.

We are deliberately NOT using a heavy agent framework (like CrewAI or LangGraph). Writing the 3 agents as plain, simple Python functions is faster to build, way easier to fix when something breaks under time pressure, and honestly demonstrates you understand how agents work rather than just importing a library that does it for you.

---

## 3. Repo Structure

Create exactly this folder layout — it keeps everyone's work in separate files so you don't overwrite each other:

```
maritime-guardian/
  app.py                      <- Person C builds this (the dashboard)
  agents/
    route_agent.py            <- Person B builds this
    debris_agent.py           <- Person B builds this
    dark_vessel_agent.py      <- Person A builds this
    orchestrator.py           <- Person C builds this
  utils/
    llm_client.py             <- Person A builds this (build it FIRST, others need it)
    gfw_client.py              <- Person A builds this (talks to Global Fishing Watch API)
  data/
    sample_debris.json         <- Person B creates this (a few made-up debris locations, clearly a demo dataset)
  requirements.txt
  .env.example                 <- shows what API keys are needed, without real keys in it
  .gitignore                   <- must include ".env" so nobody accidentally commits their API key
  README.md
```

---

## 4. Who Builds What

### Person A — Data Layer + Dark-Vessel Agent
This is the foundation everyone else needs, so build it first.

1. Write `utils/llm_client.py`: one function `ask_ai(prompt)` that sends text to your chosen LLM and returns the text answer. Keep it to one function, nothing fancy.
2. Write `utils/gfw_client.py`: a function `get_vessel_positions(area)` that calls the Global Fishing Watch API and returns a simple list of ships with their lat/lon and last-seen time.
3. Write `agents/dark_vessel_agent.py`: a function `find_dark_vessels(vessel_list)` that checks which ships stopped sending updates recently near a fishing zone, and returns a list of flagged ships with a plain-English reason (use `ask_ai` to write the reason in a sentence, e.g. "This vessel stopped broadcasting 40 minutes ago near a restricted zone — possible illegal fishing.").
4. Test it works standalone before handing off — run it from a plain Python script and print the output.

### Person B — Route Optimization Agent + Debris Agent
Can start as soon as Person A's `llm_client.py` exists (or stub it temporarily and swap in the real one later).

1. Write `data/sample_debris.json`: 8-10 made-up debris sightings, each with a lat/lon and a short description. Label it clearly as sample/demo data.
2. Write `agents/route_agent.py`: a function `optimize_route(start, end)` that calculates a simple fuel-efficient path — doesn't need to be state-of-the-art, even a basic "avoid bad weather cells" heuristic using a free weather API is enough. Return distance, estimated fuel, and the path points.
3. Write `agents/debris_agent.py`: a function `plan_cleanup_route(debris_list)` that takes the debris locations and returns the most efficient order to visit them (a simple nearest-neighbor route is completely fine — you don't need a perfect algorithm).
4. Test each function standalone with print statements before handing off.

### Person C — Orchestrator + Dashboard + Demo Prep
Starts by building simple placeholder versions of the other pieces so the dashboard works end-to-end early, then swaps in the real agents as A and B finish them.

1. Write `agents/orchestrator.py`: functions that call each agent, store results in a simple list/dict (this is your "memory" — e.g. don't re-flag a vessel already flagged in the last hour), and return one combined result the dashboard can display.
2. Write `app.py` (Streamlit): a page with a map (use `streamlit-folium`) showing flagged dark vessels, the optimized route line, and debris cleanup points, plus simple buttons/inputs for "check for dark vessels," "optimize this route," "plan debris cleanup."
3. Once the whole thing runs end-to-end, this person also owns: writing the README, recording the demo video, and doing the final GitHub push.

---

## 5. Rough 24-Hour Timeline

- **Hour 0-2**: Repo set up, API keys working, `llm_client.py` and `gfw_client.py` done and tested.
- **Hour 2-6**: All 3 agent functions working standalone (tested with print statements, not yet connected to the dashboard).
- **Hour 6-10**: Orchestrator connects all 3 agents together; basic Streamlit dashboard shows a map.
- **Hour 10-14**: Everything wired together end-to-end — click a button, see real results on the map.
- **Hour 14-18**: Polish — better map styling, clearer flagged-vessel explanations, fix bugs.
- **Hour 18-21**: Full testing — try to break it, fix what breaks.
- **Hour 21-23**: Record the 2-3 min demo video, finish the README.
- **Hour 23-24**: Final commit and push, double-check the repo is Public, buffer time.

---

## 6. Git Workflow (kept simple on purpose)

With 3 people and 24 hours, don't overcomplicate branching:

- Everyone commits directly to `main`, but **always run `git pull` before you start working and before you push**, so you don't overwrite each other.
- Since each person owns different files (see Section 4), conflicts should be rare — if Git ever shows a conflict, just message the other two before resolving it, don't guess.
- Commit **every 3-6 hours** as the rules ask, with a short message saying what you added (e.g. `"add dark vessel detection logic"`), even if it's not fully finished — a partial, honest commit history looks better to judges than 3 giant commits at the end.
- Never commit your `.env` file or real API keys — only `.env.example` with blank placeholders.

---

## 7. Before You Record the Demo — Quick Checklist

- Does the dashboard load without errors from a fresh restart?
- Do all 3 agent buttons actually produce a result (not just a spinner that never finishes)?
- Is the sample/demo data clearly labeled as such anywhere it's used?
- Can you explain, in one sentence each, what makes this "agentic" (the 3 agents + orchestrator + memory) if a judge asks?

---

## 8. Demo Video Structure (2-3 minutes)

1. **0:00-0:20** — One sentence on the real-world problem (illegal fishing, wasted fuel, ocean debris) and who it's for (a maritime authority).
2. **0:20-1:00** — Show the dark-vessel detection: a ship goes dark, your system flags it, explain why in plain words.
3. **1:00-1:40** — Show the route optimization: point A to B, here's the fuel saved.
4. **1:40-2:10** — Show the debris cleanup route being planned.
5. **2:10-2:40** — Zoom out: explain the orchestrator/memory piece — this is the "agentic AI" moment, say it explicitly.
6. **2:40-3:00** — Quick wrap-up: what you'd add with more time.

---

## 9. Final Submission Checklist

- [ ] GitHub repo is set to **Public**
- [ ] Commits made every 3-6 hours throughout (check your own commit history)
- [ ] README explains what the project does and how to run it
- [ ] Demo video is 2-3 minutes, screen recording + voice explanation
- [ ] Demo video uploaded to Google Drive, link set to accessible (not private)
- [ ] Final Google Form submitted with repo link + Drive link before the deadline
