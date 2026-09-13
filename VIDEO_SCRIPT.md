# 2:55 video script — the persuasive cut

**The constraint:** nobody asks you questions. Every point you want scored has
to land inside three minutes.

**The method:** narration carries the *story*, on-screen captions carry the
*technical facts*. A judge reads a caption while you're saying something else,
so you get roughly double the bandwidth. Every `[CAPTION]` below is text you
burn into the video — do not read them aloud.

**Word budget:** ~450 spoken words. Read at a normal pace. Do not rush; cut
visuals to fit, never speech.

---

## Before you record

```
del data\flagged_history.json
python -m streamlit run app.py --server.port 8501
```

Second terminal:

```
python -m streamlit run fisherman_app.py --server.port 8502
```

- **Demo Sample Data**, **Gulf of Mannar**. Never Live.
- Run the Route Optimizer once so the weather call is warm, then reload.
- Fisherman app in a second window, narrow like a phone.
- Kill stray Streamlit processes first, or you will film the wrong app.

---

## 0:00 – 0:22 · The hook (55 words)

*Screen: dashboard, before scanning.*

> Every year, Indian fishermen are detained for drifting across a maritime
> boundary they cannot see.
>
> Every vessel-monitoring system in the world treats a boat that goes dark as a
> suspect. Ours asks a different question first: **whose boat is it?**
>
> Because if it's ours, that crew doesn't need catching. They need warning.

*Click **Scan for dark vessels**. **CUT the wait.***

`[CAPTION: Global Fishing Watch API · live AIS-gap detection]`

---

## 0:22 – 0:52 · It sorts them (80 words)

*Zoom on the four category headers.*

> Six vessels have gone dark. The system sorts them by flag state and distance
> to the boundary — a foreign trawler inside our waters, one of **our** boats
> six kilometres from the line, an unidentified vessel, and two routine gaps.

*Scroll to Routine Gaps. Zoom the 55 km one.*

> This one has been silent for **ten hours**. We downgraded it — because it is
> fifty-five kilometres from anywhere sensitive. That's a broken radio, not a
> crime. Most systems would have paged an officer.

`[CAPTION: Classification is deterministic — flag state + perpendicular
distance. Auditable, not a model's guess.]`

---

## 0:52 – 1:28 · The part that matters (90 words)

*Open **⚠️ Border Safety Alert**. Zoom the warning box. Hold it.*

> This is our boat. So the system drafts the message a coastal station would
> actually send — in **Tamil and English**, because that's the language the
> crew reads.

*Silence for 3 full seconds on the Tamil. Do not talk over it.*

*Scroll to the Interception plan.*

> And it has already asked the route agent how to reach him: Rameswaram,
> seventy-one kilometres, two hours.
>
> One agent found him. A second planned the response. Nobody clicked anything.

`[CAPTION: Agent chaining — dark-vessel output feeds the route agent
automatically, gated by category]`

---

## 1:28 – 1:52 · The decision (60 words)

*Zoom on **🧠 AI Triage**.*

> The rules decided what each vessel **is**. This is the model deciding what to
> do **first** — one patrol boat, six vessels, competing priorities.
>
> It put the fisherman above the foreign trawler, and said why. That is a
> judgement no threshold makes for you.

`[CAPTION: Groq · openai/gpt-oss-120b · ranked plan + reasoning shown, so the
officer can overrule it]`

---

## 1:52 – 2:18 · The other two agents (65 words)

*Route Optimizer tab, pre-loaded. **CUT any wait.***

> Two more agents. Routing samples live wind either side of the track and takes
> the calmer path **only when it actually burns less fuel** — here, two point
> four percent. When it doesn't pay, it reports zero.

*Debris tab — instant.*

> And cleanup sequences ten debris sightings into a hundred and fifty-eight
> kilometres, priced in fuel.

`[CAPTION: Open-Meteo wind · fuel = distance × rate × wind penalty · sea
corridor keeps the track off land]`

---

## 2:18 – 2:42 · His end of it (60 words)

*Switch to the fisherman window. Drag the slider 14 → 0.*

> And this is the fisherman's side — a **separate app**, on his own phone.
>
> It carries only the boundary. Never vessel positions, never where the patrol
> is. A crew should be warned, not watched.
>
> It runs on GPS alone. No network, no AIS — which matters, because the boat we
> most need to warn is the one that has gone dark.

*Hold the red screen 2 seconds.*

`[CAPTION: Separate process — cannot import the vessel feed or the API token]`

---

## 2:42 – 2:55 · Close (45 words)

> Three agents, plain Python, no framework. Three live APIs. Detection, the
> decision, and the warning — end to end.
>
> The boundary here is approximate, and delivery still needs packaging as an
> installable app. But every number on screen is computed, not claimed.

*Pause.*

> Every other system watches fishermen. **This one warns them.**

---

## The captions, collected

Burn these in. They carry the technical marks you have no time to speak.

1. `Global Fishing Watch API · live AIS-gap detection`
2. `Classification is deterministic — flag state + perpendicular distance.
   Auditable, not a model's guess.`
3. `Agent chaining — dark-vessel output feeds the route agent automatically,
   gated by category`
4. `Groq · openai/gpt-oss-120b · ranked plan + reasoning shown, so the officer
   can overrule it`
5. `Open-Meteo wind · fuel = distance × rate × wind penalty · sea corridor
   keeps the track off land`
6. `Separate process — cannot import the vessel feed or the API token`

Plus one persistent disclaimer, small, bottom-right from 0:22 onward:

> `Boundary approximate — demonstration only. Not surveyed coordinates.`

---

## Why this convinces without a Q&A

Each beat answers a question they would otherwise have asked:

| Unasked question | Where it is answered |
|---|---|
| "Isn't this just another tracking dashboard?" | 0:00 — whose boat is it |
| "Won't it drown officers in false alarms?" | 0:22 — the ten-hour downgrade |
| "Is the AI doing anything real?" | 1:28 — ranking with reasoning |
| "Do the agents actually work together?" | 0:52 — chaining, nobody clicked |
| "Are those fuel numbers made up?" | 1:52 — only when it burns less |
| "Who receives the warning?" | 2:18 — his own app |
| "Are you overclaiming?" | 2:42 — the caveat, volunteered |

That last row matters more than it looks. Volunteering the boundary caveat in a
video where nobody can challenge you reads as confidence. Hiding it and being
noticed reads as the opposite.

---

## What to cut in editing

| Cut | Roughly |
|---|---|
| Scan spinner | 8s |
| Route Optimizer wait | 6–8s |
| Cursor hunting for buttons | 2–4s |

Zoom in on the Tamil message and the triage reasoning — default text is
unreadable when a judge watches on a phone.

## If you only get one clean take

Record **0:00 – 1:28** properly, then jump to **2:18** for the fisherman's
phone and the closing line. Drop route and debris entirely. The detection and
the warning are the idea; the other two agents are supporting cast.
