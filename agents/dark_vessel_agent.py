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

from utils.llm_client import ask_ai

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
                 "severity": "low" | "medium" | "high"}

            Vessels that are reporting normally are simply left out.
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

        # Step 3: decide how worried to be.
        severity = _decide_severity(minutes_dark)

        # Step 4: ask the AI to explain the flag in one human sentence.
        reason = _write_reason(vessel, minutes_dark, severity)

        # Step 5: build the alert in the exact shape the dashboard expects.
        flagged_vessels.append({
            "vessel_id": vessel["vessel_id"],
            "lat": vessel["lat"],
            "lon": vessel["lon"],
            "flagged_reason": reason,
            "severity": severity,
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
    Ask the AI for a one-sentence, plain-English explanation of the flag.

    If the AI is unavailable (no API key, no internet), we fall back to a
    simple written-out sentence so the dashboard still has something to show.
    """

    hours_dark = minutes_dark / 60

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
