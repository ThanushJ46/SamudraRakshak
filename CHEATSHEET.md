# Demo cheat sheet — one page

Hold this. Everything else is in `DEFENCE.md`.

---

## Setup, before you present

```
del data\flagged_history.json
python -m streamlit run app.py
```

Set **Gulf of Mannar** + **Demo Sample Data**. Run the Route Optimizer once
(Rameswaram → Kochi) so it's warm. Then reload and leave it on the Dark Vessel
Monitor.

**Never demo on Live GFW Data.**

---

## Opening — say this first

> A fishing boat goes quiet near the maritime boundary. Most systems either
> ignore it or treat it as a suspect. But if it's **our** boat, that crew is
> minutes from crossing a line and being detained — and nobody warns them.

Then press **Scan for dark vessels**.

---

## Click order

1. **Scan** → 6 vessels, four categories
2. Point at **ℹ️ Routine Gaps** → *"this one's been silent ten hours, 55 km from
   anywhere sensitive. We downgraded it. That's a broken radio, not a crime."*
3. Open **⚠️ Border Safety Alert** → the Tamil message + the interception plan
4. Point at **🧠 AI Triage** → *"rules decided what each vessel is. This is the
   model deciding what to do first with one patrol boat — and showing its
   reasoning so the officer can disagree."*
5. **Route Optimizer** → Rameswaram → Kochi, round Kanyakumari
6. **Debris Cleanup** → one button, 10 stops, 554.8 L
7. **Switch to the fisherman window** → drag 14 km to 0, green → amber → red

---

## The five hard answers

**"What does your AI actually decide?"**
> Rules decide severity and category — auditable, reproducible, because an
> enforcement action depends on them. The model decides what to act on first
> across the whole set, and writes the Tamil warning. Two things rules are bad
> at.

**"Is that a real maritime boundary?"**
> No. We drew it. It's dashed on the map, labelled approximate, and the
> disclaimer is inside the warning message itself. The real fix is GFW's EEZ
> data, which we already receive — it's in the README as the next step.

**"Show me the fuel saving being real."**
> Fuel is charged per km with a wind penalty, we sample real wind 30 km either
> side, cost both paths, and only detour if it's actually cheaper. It's under
> 1% — and on Rameswaram → Tuticorin it's 0%, where we keep the direct route
> and claim nothing.

**"Run it on live data."**
> Public GFW is daily-batch, not live AIS, so minute-level severity can't be
> exercised on it. Live proves the integration — real vessels, names, flags.
> Demo proves the logic. The badge always says which one actually ran.

**"Why is the fisherman's app separate?"**
> Because he must never see the surveillance picture — which boats are
> flagged, where the patrol is, when it's coming. That app imports only the
> geometry module; it cannot reach the vessel feed or the API token at all.

**"Who receives the Tamil warning?"**
> Nobody yet — it's drafted, not delivered. Delivery is a phone app with an
> offline chart and an on-device geofence, because GPS works when AIS doesn't,
> and the boat we most need to warn is the one that's gone dark. Over NavIC
> satellite messaging, which India already uses for fishermen advisories.

---

## Volunteer these before you're asked

- The boundary is approximate — we drew it
- Savings are under 1%, that's the honest number
- Four demo vessels are placed deliberately so all four categories appear
- The warning is generated, not delivered

---

## If it breaks

- **Wi-Fi dies** → demo mode needs no internet; warning and triage both fall
  back and *say so*. Say out loud: "the fallbacks are deliberate."
- **Empty map on 2nd scan** → `del data\flagged_history.json`
- **Anything else** → talk about the architecture; you know it now.

---

## One line to close on

> Every other system watches fishermen. This one warns them.
