# Defending this project

Read this before judging. It is not marketing — it is the answers to the
questions that are actually going to be asked, including the uncomfortable
ones. If you can hold this in your head you can defend the project; if you
cannot, no amount of features will save the viva.

---

## The five questions you will definitely get

### 1. "What does your AI actually decide?"

**Answer:** One thing, deliberately. The rules decide *what* each vessel is —
severity from how long it has been silent, category from flag and distance to
the boundary. Those stay deterministic on purpose, because an enforcement
decision should be auditable and reproducible, not a model's mood.

The AI decides *what to act on first*. `utils/triage.py` hands the model every
flagged vessel — flag, category, severity, distance, how many times we have
seen it before — tells it there is one patrol boat available, and asks for a
ranked order **with reasoning**. That is a judgement across a competing set
with no threshold that settles it, and the reasoning is displayed so the
officer can disagree.

It also writes the bilingual warning (below), which is a genuine language task.

**If pushed — "so it's mostly rules?"** Yes, and that is the design. Say so
without flinching: *"we chose rules for anything an enforcement action depends
on, and the model for the two things rules are bad at — weighing competing
priorities, and writing in Tamil."*

### 2. "Show me the fuel saving being real."

`agents/route_agent.py`. Fuel is charged **per kilometre with a wind penalty**:

```
effective rate = 3.5 L/km x (1 + 0.01 x wind_kmh)
```

So sailing through a 20 km/h wind costs 20% more per km. The agent samples
real Open-Meteo wind at five positions offset up to 30 km either side of the
direct line, at three points along the route, picks the calmest, then **costs
both paths and only takes the detour if it actually comes out cheaper.**

Real numbers from the current code:

| Route | Straight | Path taken | Baseline | Optimised | Saving |
|---|---|---|---|---|---|
| Rameswaram → Chennai | 434.7 km | 450.4 km | 1809.9 L | 1792.7 L | **0.9%** |
| Kochi → Colombo | 517.5 km | 522.8 km | 2190.1 L | 2176.2 L | **0.6%** |
| Rameswaram → Tuticorin | 141.9 km | 141.9 km | 576.1 L | 576.1 L | **0.0%** |

Point at the third row. On that leg the detour did not pay, so the agent kept
the direct route and reported **no saving at all**. That is the honest
behaviour and it is worth more than a big number.

**Be upfront:** the savings are small — under 1%. Say it first, before they
say it: *"weather routing is a marginal gain at this scale, and we report the
marginal number rather than a flattering one."*

**The 0.01 penalty coefficient is an approximate demo figure.** Own that. What
matters is that the saving is *computed from* the path chosen, not asserted.

> An earlier version applied a fixed 5–15% discount to the baseline regardless
> of the route. It reported "saved 9.9%" on a journey that was actually 0.2%
> longer and more expensive. We found it and fixed it. If someone asks whether
> anything like that is still in there, the answer is no, and this is the one
> we caught.

### 3. "Where did that maritime boundary come from?"

**Answer, straight:** we drew it. `ILLUSTRATIVE_BOUNDARY_LINE` in
`utils/gfw_client.py` is two approximate coordinates, not surveyed ones. It is
drawn **dashed** on the map, labelled "approximate", disclaimed in the README,
and the disclaimer is appended **inside the warning message itself** so it
cannot be separated from the number it qualifies.

**What we would do with more time:** Global Fishing Watch returns
`regions.eez`, `regions.eez12Nm` and `regions.mpaNoTake` on every event. We
fetch that response already. Swapping our line for real EEZ membership is the
correct fix and it is written up in the README's Known Limitations.

Do not pretend it is real. A judge who knows the Palk Bay will catch it in
seconds, and being caught is far worse than volunteering it.

### 4. "Run it on live data."

**Say this before they ask.** The public GFW API does not serve live AIS. It
serves **daily-batch fishing events**, hours to days old. Our severity bands
are in minutes, so against real data every vessel is already "hours stale".
And because our demo boundary is in the Gulf of Mannar, real vessels elsewhere
are more than 200 km away and classify as `routine_gap`.

So live mode demonstrates that the **integration** works — real vessels, real
names, real flags — and demo mode demonstrates that the **logic** works. The
dashboard's data-source badge always says which one actually ran, including an
orange state for "you asked for live, it failed, this is demo data".

That badge is the answer to "is this real?" Show it to them.

### 5. "Who receives the Tamil warning?"

**Nobody yet — it renders on the page.** Delivery over SMS or VHF is not
built. Say so plainly and immediately; do not imply it sends.

What it demonstrates: the system knows *which* boat needs warning, and produces
the exact message a station would read out, in the language the crew speaks,
with the caveat attached. Wiring that to an SMS gateway is plumbing, not
insight — and the insight is the part we built.

---

## Code you must be able to walk through

If a judge points at a file, these are the answers.

### `utils/zone_utils.py`

- **`which_side()` — why does a positive cross product mean the Indian side?**
  We take the cross product of the boundary's direction with the vector from
  the boundary's start to the vessel. The *sign* tells you which side. Which
  sign maps to which side depends on the order the boundary's two points are
  written in — ours are written south-to-north, so positive comes out west,
  which is the Indian side. If you reversed the two points in the constant,
  the sign would flip.
- **Why degrees in `which_side` but kilometres in `distance_point_to_line_km`?**
  Because `which_side` only needs the *sign*, and scaling both terms cannot
  flip a sign. Distance needs a real magnitude, so there we convert to flat
  km first (latitude is a constant 110.57 km/degree; longitude shrinks by
  cos(latitude)).
- **Why measure against an infinite line, not the segment?** So a vessel off
  the northern end still reads as "near the line" instead of "far from the
  line's endpoint".
- **Why the 200 km guard (`MAX_RELEVANT_DISTANCE_KM`)?** Because the line is
  infinite, every foreign vessel west of it counted as "on our side". Before
  the guard, scanning the North Sea flagged 17 Belgian and Danish trawlers as
  intrusions from 9,000 km away. Checked first, so a boat on the other side of
  the planet can never be an intrusion.
- **Why classify on `flag` instead of the vessel id?** Live GFW ids are
  meaningless hex (`054b3f2fd-d468-e27f-6ba5-03b9b6fefb11`). An id-prefix rule
  classified every real vessel as unidentified, so the whole layer silently did
  nothing on live data. GFW sends a `flag` and a real `name`; we keep both. The
  id-prefix check remains underneath as a fallback for records with no flag.

### `agents/dark_vessel_agent.py`

- **Why is `routine_gap` capped at `low`?** A boat silent ten hours in open
  water is a broken radio, not an incident. Before the cap it scored `high` and
  buried the alerts that mattered. It also skips the AI call, which is why a
  scan stays fast.
- **Why is severity computed before the category cap?** So the raw severity is
  available, then deliberately overridden — the cap is a visible decision in
  the code, not a hidden branch.

### `utils/gfw_client.py`

- **Why does `get_vessel_positions` raise instead of returning sample data?**
  It used to fall back silently, which meant a failed live call looked
  identical to a successful one. Now it raises and the *orchestrator* decides
  to fall back, so the dashboard can report what actually ran.
- **Why `_keep_latest_per_vessel`?** GFW returns one record per fishing
  *event*, so one boat that fished four times came back four times and was
  drawn on the map four times.
- **Why are four sample vessels pinned (`PINNED_SAMPLE_POSITIONS`)?** So a demo
  reliably exercises all four categories instead of depending on random luck.
  **Volunteer this** — it is visible in the code and looks much worse if a
  judge finds it themselves. The framing: these are *test fixtures for the
  demo*, and the classification logic they exercise is not itself rigged.
- **Why is `MAX_RESULTS` only 20?** Each medium/high vessel costs one AI call.

### `agents/orchestrator.py`

- **Why does `check_dark_vessels` return a dict, not a list?** So it can report
  `data_source` alongside the vessels. Showing sample data as if it were real
  would be the dishonest option.
- **Why does memory never hide a vessel?** It used to return only new or
  escalated vessels, so a second scan with no changes returned an empty list
  and the map went blank. Now every currently-flagged vessel is returned every
  scan and memory only sets `is_new`. The rule: **memory changes how a vessel
  is presented, never whether it appears.**
- **Why track category as well as severity?** A boat drifting from
  `routine_gap` into `border_safety_alert` is the most important transition
  there is, and it can happen while severity stays `low` — the severity-only
  check missed it entirely.

### `utils/sea_route.py`

- **Why does this exist?** The route agent draws great-circle lines and knows
  nothing about land. Asked for Rameswaram → Kochi in one go it drew a straight
  line **across Tamil Nadu and Kerala**. We now plan a path through offshore
  waypoints and call the agent once per short leg, so it stays at sea —
  638 km round the peninsula instead of an impossible 342 km overland. The
  route agent itself is unchanged.
- **Caveat:** the offshore waypoints are eyeballed, not charted. And
  interception routes call the route agent directly rather than going through
  this, so a long interception can still cross land.

---

## Say these before you are asked

Volunteering a weakness costs you a little. Being caught hiding it costs you
the round.

1. "The boundary is approximate — we drew it. Here is the real fix."
2. "The fuel savings are under 1%. That is the honest number."
3. "The public GFW feed is daily-batch, so our minute-level severity bands
   cannot be exercised by live data. The badge tells you which data you are
   seeing."
4. "Four demo vessels are placed deliberately so all four categories appear."
5. "The Tamil warning is generated, not delivered."

---

## The 60-second opening

> A fishing boat goes quiet near the maritime boundary. Most monitoring systems
> either ignore it or treat it as a suspect. But if it is **our** boat, that
> crew is minutes from crossing a line and being detained — and nobody warns
> them.
>
> *[Scan — demo mode, Gulf of Mannar]*
>
> Six vessels have gone dark. The system sorts them: a foreign trawler inside
> our waters, one of **our** boats 6 km from the line, an unidentified vessel,
> and two radio faults it has deliberately deprioritised — including one silent
> for ten hours that we downgraded, because it is 55 km from anywhere
> sensitive.
>
> *[Open the Border Safety Alert]*
>
> For our own boat it has drafted the message a station would actually send —
> Tamil and English. And it has already asked the route agent how to reach it:
> Rameswaram, 71 km, two hours.
>
> *[Point at AI Triage]*
>
> The rules decided what each vessel is. This is the model deciding what to do
> first, with one patrol boat — and showing its reasoning, so the officer can
> disagree.

---

## If the demo breaks

- **Wi-Fi dies:** demo mode needs no GFW; the warning falls back to a fixed
  bilingual message; triage falls back to the rule-based order and *says so*.
  Everything still runs. The fallbacks are a feature — say that out loud.
- **Empty map on a second scan:** `del data\flagged_history.json`.
- **Slow route:** it makes several weather calls. Pre-run it before presenting.
- **Never demo on Live GFW Data** unless you want to talk about batch data —
  everything comes back `routine_gap`.
