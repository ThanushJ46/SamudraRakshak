"""
dark_vessel_agent.py
--------------------
Agent 1 of 3: finds ships that have "gone dark".

A ship going dark means it stopped broadcasting its position. Sometimes that
is a broken radio - but near a protected fishing zone it can also mean someone
switched it off on purpose to fish illegally. Our job is to flag it so a human
can take a look.

    from agents.dark_vessel_agent import find_dark_vessels
    alerts = find_dark_vessels(vessels)
"""

import os
import sys
from datetime import datetime, timezone

# Let this file find the "utils" folder even if it is run directly
# (python agents/dark_vessel_agent.py) rather than imported from the root.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.gfw_client import ILLUSTRATIVE_BOUNDARY_LINE
from utils.llm_client import ask_ai
from utils.zone_utils import classify_vessel, distance_point_to_line_km, which_side

# A vessel is only interesting once it has been silent this long.
DARK_THRESHOLD_MINUTES = 30

# Where "low" turns into "medium", and "medium" turns into "high".
MEDIUM_THRESHOLD_MINUTES = 90        # 1.5 hours
HIGH_THRESHOLD_MINUTES = 240         # 4 hours


def find_dark_vessels(vessel_list: list[dict]) -> list[dict]:
    """
    Look through a list of vessels and return only the suspicious ones.

    Input:  vessel_list -> exactly what utils.gfw_client.get_vessel_positions()
            returns, i.e. a list of:
                {"vessel_id": str, "lat": float, "lon": float,
                 "last_position_time": "2026-09-12T08:30:00Z"}

    Output: a list of dicts, each one shaped exactly like:
                {"vessel_id": str,
                 "lat": float,
                 "lon": float,
                 "flagged_reason": str,          # one plain-English sentence
                 "severity": "low" | "medium" | "high",
                 "category": str,                # see utils.zone_utils
                 "distance_to_border_km": float, # to the illustrative boundary
                 "vessel_name": str | None,      # readable name if we have one
                 "flag": str | None,             # ISO-3 flag state, e.g. "IND"
                 "warning_message": str | None}  # Tamil + English warning,
                                                 # only for border_safety_alert

            Vessels that are reporting normally are simply left out.

            Vessels categorised as "routine_gap" are capped at "low" severity
            no matter how long they have been silent, and never cost an AI
            call. A boat silent for ten hours in open water is a radio fault,
            not an incident - treating it as "high" was drowning the real
            alerts in noise.
    """

    flagged_vessels = []
    now = datetime.now(timezone.utc)

    for vessel in vessel_list:
        # Step 1: work out how long this vessel has been silent.
        last_seen = _parse_time(vessel.get("last_position_time"))

        # If the timestamp was unreadable we can't judge it, so skip it.
        if last_seen is None:
            continue

        minutes_dark = (now - last_seen).total_seconds() / 60

        # Step 2: still reporting recently enough? Not our problem.
        if minutes_dark <= DARK_THRESHOLD_MINUTES:
            continue

        # Step 3: work out WHERE this vessel is relative to the sensitive
        # boundary, and what kind of situation that makes it.
        distance_km = distance_point_to_line_km(vessel, ILLUSTRATIVE_BOUNDARY_LINE)
        side = which_side(vessel, ILLUSTRATIVE_BOUNDARY_LINE)
        category = classify_vessel(vessel, distance_km, side)

        # Step 4: decide how worried to be.
        severity = _decide_severity(minutes_dark)

        # Step 5: a "routine_gap" is a boat that went quiet in open water,
        # far from anything sensitive. However long it has been silent, that
        # is a radio fault and not an incident - so we cap it at "low", give
        # it a plainly different sentence, and skip the AI call entirely.
        # Without this cap, a ten-hour dropout in the middle of nowhere
        # showed up as "high" and buried the alerts that actually matter.
        if category == "routine_gap":
            severity = "low"
            reason = (
                f"Silent for {int(minutes_dark)} minutes, {distance_km:.1f}km "
                f"from the nearest sensitive zone - likely a routine gap, not "
                f"flagged as suspicious."
            )
        else:
            reason = _write_reason(vessel, minutes_dark, severity)

        # Step 6: if this is one of OUR boats near the line, write the message
        # we would actually radio or text to them. Only for this category -
        # there is no point drafting a friendly warning for a foreign
        # trawler or for a radio fault in open water.
        if category == "border_safety_alert":
            warning_message = _write_fisherman_warning(vessel, minutes_dark, distance_km)
        else:
            warning_message = None

        # Step 7: build the alert in the exact shape the dashboard expects.
        flagged_vessels.append({
            "vessel_id": vessel["vessel_id"],
            # Live GFW ids are unreadable hex, so pass the real name and flag
            # through for the dashboard to show instead. Both can be None.
            "vessel_name": vessel.get("vessel_name"),
            "flag": vessel.get("flag"),
            "lat": vessel["lat"],
            "lon": vessel["lon"],
            "flagged_reason": reason,
            "severity": severity,
            "category": category,
            "distance_to_border_km": round(distance_km, 1),
            # Only set for "border_safety_alert"; None otherwise.
            "warning_message": warning_message,
        })

    return flagged_vessels


def _decide_severity(minutes_dark: float) -> str:
    """
    Turn 'minutes of silence' into one of our three severity labels.

        30 - 90 minutes   -> "low"
        90 min - 4 hours  -> "medium"
        4+ hours          -> "high"
    """
    if minutes_dark >= HIGH_THRESHOLD_MINUTES:
        return "high"
    if minutes_dark >= MEDIUM_THRESHOLD_MINUTES:
        return "medium"
    return "low"


def _parse_time(time_string) -> datetime | None:
    """
    Turn an ISO datetime string like "2026-09-12T08:30:00Z" into a real
    datetime object that we can do maths with.

    Returns None if the string is missing or in a format we don't recognise,
    so one bad record can never crash the whole agent.
    """
    if not time_string:
        return None

    # Some feeds hand us a real datetime object instead of a string.
    if isinstance(time_string, datetime):
        if time_string.tzinfo is None:
            return time_string.replace(tzinfo=timezone.utc)
        return time_string.astimezone(timezone.utc)

    try:
        # Python doesn't always understand the "Z" ending, so swap it for the
        # spelled-out version of the same thing (+00:00 means UTC).
        cleaned = str(time_string).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(cleaned)

        # If the timestamp didn't say which timezone it was in, assume UTC -
        # that's what ship-tracking feeds use.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed
    except ValueError:
        return None


def _write_reason(vessel: dict, minutes_dark: float, severity: str) -> str:
    """
    Write the one-sentence explanation shown next to the alert.

    "low" severity vessels get a simple templated sentence with NO AI call.
    Every AI call costs about two seconds, and a busy area can flag twenty
    vessels at once - so we spend those seconds only on the medium and high
    alerts, which are the ones anybody actually reads.

    If the AI is unavailable (no API key, no internet), we fall back to the
    same kind of plain sentence so the dashboard always has something to show.
    """

    hours_dark = minutes_dark / 60

    # Low severity: no AI, just state the facts. This is what keeps a 20-vessel
    # scan fast.
    if severity == "low":
        return (
            f"Silent for {int(minutes_dark)} minutes at "
            f"{vessel['lat']:.2f}, {vessel['lon']:.2f} - a short AIS gap."
        )

    prompt = (
        "You are a maritime monitoring assistant for a coast guard dashboard.\n"
        f"Vessel {vessel['vessel_id']} stopped broadcasting its AIS position "
        f"{int(minutes_dark)} minutes ago ({hours_dark:.1f} hours) at "
        f"latitude {vessel['lat']}, longitude {vessel['lon']}. "
        f"The alert severity is '{severity}'.\n"
        "Write ONE short sentence (maximum 25 words) explaining to an officer "
        "why this vessel has been flagged - for example possible unauthorised "
        "fishing, transshipment, or a vessel in distress. Plain English, no "
        "jargon, no bullet points, no preamble."
    )

    try:
        return ask_ai(prompt)
    except Exception as error:
        print(f"[WARNING] AI explanation unavailable ({error.__class__.__name__}), "
              f"using a basic sentence instead.")
        return (
            f"Vessel {vessel['vessel_id']} has not reported its position for "
            f"{int(minutes_dark)} minutes ({hours_dark:.1f} hours), which is "
            f"a {severity}-severity sign it may have gone dark deliberately."
        )


def _write_fisherman_warning(vessel: dict, minutes_dark: float, distance_km: float) -> str:
    """
    Draft the message we would send to one of OUR OWN fishing boats that has
    gone quiet near the maritime boundary.

    This is the one place the AI does something only an AI can do: write the
    same short warning in Tamil and in English, in the right tone. It is a
    heads-up to a fisherman who may be about to cross a line and be detained -
    not an accusation, and not an enforcement notice.

    Falls back to a fixed bilingual message if the AI is unavailable, so an
    officer always has something to send.
    """
    boat_label = vessel.get("vessel_name") or vessel["vessel_id"]

    prompt = f"""You are drafting a short safety warning for a small Indian fishing
boat that is close to a maritime boundary and has stopped broadcasting its
AIS position.

Boat: {boat_label}.
Distance from the boundary: {distance_km:.1f} km.
Silent for {int(minutes_dark)} minutes.

Write a warning of at most 25 words, telling them how far they are from the
boundary, to turn back towards Indian waters, and to switch their AIS
transponder back on.

Give it TWICE: first in Tamil, then in English, each on its own line,
prefixed exactly 'TA:' and 'EN:'. Be calm and helpful - this is a warning to
protect them, not an accusation. No preamble."""

    try:
        return ask_ai(prompt)
    except Exception as error:
        print(f"[WARNING] Could not draft fisherman warning ({error.__class__.__name__}), "
              f"using a fixed bilingual message.")
        return (
            f"""TA: எச்சரிக்கை: நீங்கள் கடல் எல்லையிலிருந்து {distance_km:.1f} கி.மீ. தொலைவில் உள்ளீர்கள். இந்திய கடல் பகுதிக்குத் திரும்பி, AIS கருவியை உடனே இயக்கவும்.
EN: Warning: you are {distance_km:.1f} km from the maritime boundary. Turn back towards Indian waters and switch your AIS transponder on immediately."""
        )
