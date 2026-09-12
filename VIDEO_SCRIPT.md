# 2:45 video script

Target 2:55, hard ceiling 3:00. Narration is written to be read aloud at a
normal pace — do not rush it, cut the visuals to fit instead.

**The editorial decision: half the video is the fishermen story.** Route and
debris get ten seconds each. Do not try to show three agents properly in three
minutes — you will show none of them properly.

---

## Before you record

```
del data\flagged_history.json
python -m streamlit run app.py
```

- **Demo Sample Data** + **Gulf of Mannar**. Never Live.
- Run the Route Optimizer once (Rameswaram → Kochi) so the weather call is
  warm, then reload the page.
- Browser at **100% zoom**, full screen, bookmarks bar hidden.
- Close Streamlit's **Deploy** button popup if it appears.
- Record at 1080p. Zoom in during editing on the Tamil message and the triage
  text — default size is unreadable on a phone.

**Record in one take, then cut the waiting.** Every spinner gets removed.

---

## 0:00 – 0:25 · The hook

*Screen: the dashboard, before scanning.*

> A fishing boat goes quiet near the maritime boundary between India and Sri
> Lanka.
>
> Every monitoring system treats that the same way — a suspect. But if it's an
> Indian boat, that crew is minutes from crossing a line they can't see, and
> being detained for weeks.
>
> Nobody warns them. That's what we built.

*Click **Scan for dark vessels**. **CUT the 8-second wait.***

---

## 0:25 – 0:55 · It sorts them

*Screen: results. Zoom on the four category headers.*

> Six vessels have gone dark. Samudra Rakshak doesn't treat them alike — it
> asks where each one is, and whose it is.
>
> A foreign trawler inside our waters. One of **our** boats, six kilometres
> from the line. An unidentified vessel. And two routine gaps.

*Scroll to Routine Gaps, zoom on the 55 km one.*

> This one has been silent for ten hours — and we **downgraded** it, because
> it's fifty-five kilometres from anywhere sensitive. That's a broken radio,
> not a crime. Cutting false alarms is the point.

---

## 0:55 – 1:35 · The part that matters

*Open **⚠️ Border Safety Alert**. Zoom on the Tamil message. Hold it.*

> This is our boat. Six kilometres from the boundary, silent for three hours.
>
> So the system drafts the message a coastal station would actually send —
> in **Tamil and English**, because that's the language the crew reads.

*Let the Tamil sit on screen for a full 3 seconds. Do not talk over it.*

*Scroll slightly to the Interception plan.*

> And it has already asked the route agent how to reach him: Rameswaram,
> seventy-one kilometres, two hours.
>
> One agent found him. Another planned the response. The warning is already
> written.

---

## 1:35 – 1:55 · The AI decides

*Zoom on **🧠 AI Triage**.*

> Rules decide what each vessel **is** — that stays deterministic, because an
> enforcement action depends on it.
>
> This is the model deciding what to do **first**, with one patrol boat
> available — and showing its reasoning, so the officer can disagree with it.

---

## 1:55 – 2:20 · The other two agents, fast

*Route Optimizer, already loaded. **CUT any wait.***

> Two more agents. Routing keeps ships at sea instead of cutting across land,
> and picks the calmer water using live wind data.

*Debris Cleanup — click, it's instant.*

> And cleanup plans the shortest collection round for ten debris sightings —
> a hundred and fifty-eight kilometres, priced in fuel.

---

## 2:20 – 2:40 · The fisherman's phone

*Scroll to **📱 Fisherman Alert**. Drag the slider from 14 km down to 0.*

> And this is his end of it. The same boundary, on his own phone — green,
> amber, red as he closes on the line.
>
> It runs on GPS alone. No network, no AIS. Which matters, because the boat we
> most need to warn is the one that's gone dark.

*Let the red screen hold for 2 seconds. That is the closing image.*

---

## 2:40 – 2:55 · Close

*Screen: back to the Border Safety Alert, or the full map.*

> Three agents, plain Python, no framework — detection, the decision, and the
> warning, end to end.
>
> The boundary here is approximate, and the alert still needs packaging as an
> installable app. But the logic is done.

*Pause.*

> Every other system watches fishermen. This one warns them.

---

## On-screen text to burn in

One caption, bottom of frame, around 2:20 — not spoken beyond the line above:

> Boundary shown is approximate, for demonstration only. Not surveyed
> coordinates.

That one line covers you, and the README carries the detail if anyone opens
the repo.

---

## What to cut in editing

| Cut | Roughly |
|---|---|
| Scan spinner | 8s |
| Route Optimizer wait | 6–8s |
| Any mouse hunting for a button | 2–4s |

The Fisherman Alert slider is instant — no cut needed. Drag it smoothly from
14 down to 0 in one motion so the colour change reads on camera.

Practise the clicks so the cursor moves straight to things. Nothing reads as
unprepared faster than a cursor wandering the screen.

---

## If you only have time for one take

Record **0:00 – 1:35** properly — the hook, the sorting, and the Tamil
warning — then jump straight to **2:20**, the fisherman's phone, and the
closing line. Drop route and debris entirely if you have to. The detection and
the warning are the idea; the other two agents are supporting cast.
