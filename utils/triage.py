"""
triage.py
---------
The one place where the AI makes a DECISION instead of describing one.

Everywhere else in this project the AI writes prose about a conclusion that
threshold rules already reached: the severity bands decide, the category rules
decide, and the model explains. Useful, but it is not reasoning - delete the
model and every decision comes out the same.

This is different. Given every vessel currently flagged, plus how far each one
is from a sensitive boundary, how long it has been silent, and how many times
we have seen it before, the model has to weigh them against each other and say
what the duty officer should do FIRST, and why - a judgement over a whole set,
with competing factors and no threshold that settles it.

The rules deliberately stay in charge of anything an enforcement decision
depends on (severity, category). The model is given the part rules are bad at:
ordering competing priorities and saying so in a sentence a human can argue
with.

    from utils.triage import triage_alerts
    plan = triage_alerts(flagged_vessels)
"""

import json

from utils.llm_client import ask_ai

# If a scan flags more than this, we only ask the model about the most
# concerning ones - both to keep the prompt small and the response fast.
MAX_VESSELS_IN_PROMPT = 8

CONCERN_ORDER = {
    "foreign_intrusion": 3,
    "border_safety_alert": 2,
    "unidentified_near_zone": 1,
    "routine_gap": 0,
}


def _vessel_summary(vessel: dict) -> dict:
    """Reduce a flagged vessel to just the facts the decision turns on."""
    return {
        "id": vessel.get("vessel_name") or vessel["vessel_id"],
        "flag": vessel.get("flag") or "unknown",
        "category": vessel["category"],
        "severity": vessel["severity"],
        "km_from_boundary": vessel["distance_to_border_km"],
        "times_flagged_before": vessel.get("times_flagged", 1),
        "escalated": bool(vessel.get("is_new")) and vessel.get("times_flagged", 1) > 1,
    }


def triage_alerts(flagged_vessels: list[dict]) -> dict:
    """
    Ask the model to prioritise the current alerts and justify the order.

    Input:  the flagged-vessel list from the orchestrator
    Output: {
                "ranking": [str, ...],   # vessel ids, most urgent first
                "reasoning": str,        # why, in a few sentences
                "available": bool,       # False if the model could not be used
            }

    Never raises. If the model is unavailable we fall back to the rule-based
    ordering and say so plainly, so the dashboard can show which one produced
    the list the officer is looking at.
    """
    if not flagged_vessels:
        return {"ranking": [], "reasoning": "Nothing is currently flagged.", "available": True}

    # Rule-based order, used both to choose what to send and as the fallback.
    by_concern = sorted(
        flagged_vessels,
        key=lambda v: (
            -CONCERN_ORDER.get(v["category"], 0),
            v["distance_to_border_km"],
        ),
    )
    shortlist = by_concern[:MAX_VESSELS_IN_PROMPT]
    fallback_ranking = [
        (v.get("vessel_name") or v["vessel_id"]) for v in shortlist
    ]

    facts = [_vessel_summary(v) for v in shortlist]

    prompt = f"""You are the duty officer's assistant at an Indian coast guard
monitoring station. These vessels have all stopped broadcasting their AIS
position. You have one patrol boat available right now.

Here are the facts:
{json.dumps(facts, indent=2)}

Context you must weigh:
- A foreign-flagged vessel inside our waters is an enforcement matter.
- An Indian-flagged vessel near the boundary is a SAFETY matter: that crew may
  be about to cross and be detained. It is not a suspect.
- An unidentified vessel near the boundary is unknown risk.
- A vessel far from the boundary is almost always a broken radio.
- A vessel seen repeatedly, or one that has escalated, matters more than a
  first sighting.

Decide the order to act in, and say why. Reply as JSON only, no markdown:
{{"ranking": ["id", "id", ...], "reasoning": "two or three sentences"}}

Rank every vessel listed. In the reasoning, name the single vessel you would
act on first and say what action you would take."""

    try:
        raw_reply = ask_ai(prompt)

        # Models sometimes wrap JSON in a code fence despite being asked not to.
        cleaned = raw_reply.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)

        ranking = [str(item) for item in parsed.get("ranking", [])]
        reasoning = str(parsed.get("reasoning", "")).strip()

        # If the model gave us nothing usable, treat it as unavailable rather
        # than showing an empty panel.
        if not ranking or not reasoning:
            raise ValueError("model reply missing ranking or reasoning")

        return {"ranking": ranking, "reasoning": reasoning, "available": True}

    except Exception as error:
        print(f"[triage] AI triage unavailable ({error.__class__.__name__}: {error}). "
              f"Falling back to the rule-based order.")
        return {
            "ranking": fallback_ranking,
            "reasoning": (
                "AI triage was unavailable, so this is the rule-based order: "
                "foreign intrusions first, then our own boats near the "
                "boundary, then unidentified vessels, closest to the boundary "
                "first within each group."
            ),
            "available": False,
        }
