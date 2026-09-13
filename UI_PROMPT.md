# UI/UX prompt — paste this into your other tool

---

## Context

This is **Samudra Rakshak**, a hackathon project: a maritime monitoring system
for an Indian coast guard authority, plus a separate warning app for fishermen.
Python + Streamlit + Folium. It is finished and working. I need a **UI/UX pass
only**.

There are two Streamlit apps, run separately and on purpose:

```bash
python -m streamlit run app.py --server.port 8501            # coast guard dashboard
python -m streamlit run fisherman_app.py --server.port 8502  # fisherman's app
```

Both must keep working after your changes.

## The goal that overrides everything

**This will be recorded as a 2–3 minute video, watched by judges on laptops and
phones.** So the single most important outcome is: *the important things must
be large and legible at a glance.* Default Streamlit body text is unreadable
when a 1080p screen recording is watched on a phone.

Optimise for "readable in a video", not for information density.

---

## HARD RULES — do not break these

1. **Do not touch any file in `agents/` or `utils/`.** That is the business
   logic and it is verified working. UI changes belong in `app.py`,
   `fisherman_app.py`, and `.streamlit/config.toml` only.
2. **Do not change any data flow in `app.py`.** Do not rename variables that
   come from the backend, do not change what is passed to
   `check_dark_vessels()`, `get_optimized_route()`, `get_cleanup_plan()`, and do
   not alter any `st.session_state` keys. Restyle what is rendered; do not
   change what is computed.
3. **Do not delete or reword any disclaimer.** Specifically these must survive
   verbatim in meaning:
   - "approximate, illustrative maritime boundary … not surveyed or legal
     coordinates"
   - "DEMO ONLY — approximate boundary, not surveyed coordinates. Not for
     navigation."
   - the data-source badge text ("Live Data" / "Demo Data" / "Demo Data (live
     call failed)")
   - the note that offshore waypoints are approximate
   You may restyle them. You may not soften or remove them. They are there for
   honesty reasons and their absence would be a serious problem.
4. **Keep the two apps separate.** `fisherman_app.py` must not import anything
   from `agents/`, and must not import `utils.gfw_client`, `utils.llm_client`,
   `utils.triage`, or `utils.orchestrator`. Do not merge the two apps into one
   with a view toggle — they are separate processes deliberately, so the
   fisherman's app cannot reach the surveillance data or the API token. The
   cross-links (`st.link_button`) between them should stay.
5. **No external CSS/JS/font CDNs anywhere.** Inline CSS only. The project runs
   on flaky conference wifi.
6. **Do not add new Python dependencies.**

---

## Problems to fix

### 1. The theme is not pinned (do this first)

`.streamlit/config.toml` currently contains only a comment and sets no theme,
so the app renders light or dark depending on the machine and browser. That is
unacceptable for a recording.

Pin an explicit dark theme in `.streamlit/config.toml` (`[theme]` with
`base`, `primaryColor`, `backgroundColor`, `secondaryBackgroundColor`,
`textColor`) and make every custom colour in both apps consistent with it.

### 2. White cards on a dark page

In `app.py` the `.stat-card` CSS class is hardcoded `background: #ffffff` with
`color: #0f172a`. On the dark theme these render as glaring white boxes. Rework
the card styling to fit the dark theme — dark surface, subtle border, light
text — while keeping the same information.

### 3. Everything is too small for video

- Metric values ("Vessels Flagged", "Route Distance", "Fuel Saved") should be
  noticeably larger.
- The AI Triage reasoning paragraph and the Tamil/English warning message are
  the two things a judge most needs to read. Give them clear visual prominence:
  larger type, more padding, higher contrast.
- The Tamil text in particular must be comfortably readable — Tamil script
  needs a bit more size and line-height than Latin to stay legible.

### 4. The alert list needs stronger hierarchy

The Dark Vessel Monitor groups alerts into four categories with coloured header
bars. The problem is everything below those headers looks identical, so
"foreign vessel inside our waters" and "routine radio fault" read with equal
weight. Make severity and urgency visible at a glance — the eye should land on
the serious items first. Routine gaps should visibly recede.

### 5. Too much vertical scrolling

The guard dashboard is one long page: Dark Vessel Monitor, Route Optimizer,
Debris Cleanup. In a 3-minute video, scrolling costs time and looks
unrehearsed. Reduce the vertical distance between the key moments — tighten
spacing, reduce redundant captions, consider `st.tabs` for the three sections
**if and only if** that does not change any logic. (If you use tabs, the Dark
Vessel Monitor must be the default tab.)

### 6. The fisherman app should feel like a different product

`fisherman_app.py` currently reuses a similar look to the dashboard. It should
feel unmistakably like a crew-facing mobile tool, not an authority console —
simpler, bigger, fewer words, calmer. The phone mock-up in it is the closing
shot of the video, so it should look genuinely good: realistic device framing,
strong colour states (green / amber / red), large distance number.

### 7. Consistency pass

There are five section headers using a `.sr-section-title` class, plus various
captions and `st.info` / `st.warning` blocks that have accumulated
inconsistently. Unify spacing, heading sizes, caption treatment, and colour
usage across both apps so it reads as one product.

---

## Things to leave alone

- The Folium maps use default OpenStreetMap tiles deliberately. **Do not switch
  to CartoDB or any other tile provider** — they now require an API key and
  silently render "API KEY REQUIRED" watermarks. Marker colours and sizes may be
  restyled.
- The four category names and their meanings.
- The emoji used as category markers (🚩 ⚠️ ❓ ℹ️) — they carry meaning.
- Port names, area presets, slider ranges, thresholds.

---

## How to verify you have not broken anything

After your changes, all of these must still pass:

```bash
python test_person_a.py      # expect RESULT: PASS lines, no FAIL
python test_person_b.py      # expect ALL PERSON B TESTS PASSED (6/6)
```

Then run both apps and confirm by clicking:

1. Dark Vessel Monitor → set **Demo Sample Data** → **Scan for dark vessels**
   → six vessels appear across four category sections, a dashed red boundary
   line on the map, dotted blue interception routes, and an AI Triage panel
   with a ranking and reasoning.
2. Open the **⚠️ Border Safety Alert** entry → a Tamil + English warning
   message and an interception plan are both visible.
3. Route Optimizer → Rameswaram → Kochi → a route that stays **in the sea**
   around the southern tip of India, with baseline/optimised fuel figures.
4. Debris Cleanup → ten numbered stops and a total distance.
5. Fisherman app → drag the slider from 30 to 0 → the phone panel moves green →
   amber → red, and the Tamil text changes with it.
6. Both `st.link_button` cross-links still work.

If any of those stop working, revert rather than patching around it.
