"""
Dark-Vessel Agent for Maritime Guardian.
Identifies vessels that have stopped transmitting AIS tracking signals (gone "dark"),
evaluates risk severity, and generates an AI explanation for each flagged vessel.
"""

from datetime import datetime, timezone
import sys
import os

# Allow imports from project root whether run directly or imported as a module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.llm_client import ask_ai


def _parse_timestamp(timestamp_val) -> datetime:
    """
    Helper function to parse a timestamp into an aware UTC datetime.
    Supports datetime objects and ISO formatted strings.
    """
    if isinstance(timestamp_val, datetime):
        if timestamp_val.tzinfo is None:
            return timestamp_val.replace(tzinfo=timezone.utc)
        return timestamp_val.astimezone(timezone.utc)

    if isinstance(timestamp_val, str):
        clean_str = timestamp_val.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

    # Fallback to current UTC time if parsing fails
    return datetime.now(timezone.utc)


def _determine_severity(minutes_offline: float) -> str:
    """
    Determines severity level based on how long the vessel has been dark:
    - 30 to 60 minutes: 'low'
    - 60 to 180 minutes (1 to 3 hours): 'medium'
    - More than 180 minutes (> 3 hours): 'high'
    """
    if minutes_offline > 180:
        return "high"
    elif minutes_offline > 60:
        return "medium"
    return "low"


def find_dark_vessels(vessel_list: list[dict]) -> list[dict]:
    """
    Scans a list of vessels and flags those whose last position broadcast
    is more than ~30 minutes old.

    Parameters:
        vessel_list (list[dict]): A list of vessel records, each containing:
                                  - vessel_id (str)
                                  - lat (float)
                                  - lon (float)
                                  - last_position_time (str or datetime)

    Returns:
        list[dict]: A list of flagged dark vessels with:
                    - vessel_id (str)
                    - lat (float)
                    - lon (float)
                    - flagged_reason (str): AI-generated explanation
                    - severity (str): 'low', 'medium', or 'high'
    """
    now = datetime.now(timezone.utc)
    flagged_vessels = []

    for vessel in vessel_list:
        vessel_id = vessel.get("vessel_id", "UNKNOWN")
        lat = vessel.get("lat", 0.0)
        lon = vessel.get("lon", 0.0)
        raw_time = vessel.get("last_position_time")

        if not raw_time:
            continue

        last_time = _parse_timestamp(raw_time)
        time_diff = now - last_time
        minutes_offline = time_diff.total_seconds() / 60.0

        # Flag vessel if it has not broadcasted position for more than 30 minutes
        if minutes_offline > 30:
            severity = _determine_severity(minutes_offline)

            # Build a clear prompt for the Gemini LLM
            prompt = (
                f"You are an expert maritime intelligence officer for the Coast Guard. "
                f"Vessel '{vessel_id}' at coordinates ({lat}, {lon}) ceased transmitting AIS data "
                f"{int(minutes_offline)} minutes ago (severity level: {severity}). "
                f"In exactly one concise sentence, provide the operational reason why this vessel "
                f"is flagged as suspicious (e.g., potential unauthorized fishing, transshipment, or distress)."
            )

            # Ask AI for an explanation
            flagged_reason = ask_ai(prompt)

            flagged_vessels.append({
                "vessel_id": vessel_id,
                "lat": lat,
                "lon": lon,
                "flagged_reason": flagged_reason,
                "severity": severity,
            })

    return flagged_vessels
