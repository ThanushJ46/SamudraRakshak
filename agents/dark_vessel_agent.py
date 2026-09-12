# TEMPORARY STUB - replace with the real version.

from datetime import datetime


def find_dark_vessels(vessel_list: list) -> list:
    flagged_vessels = []
    current_time = datetime.utcnow()

    for vessel in vessel_list:
        last_seen_time = datetime.fromisoformat(vessel["last_position_time"])
        minutes_dark = (current_time - last_seen_time).total_seconds() / 60

        if minutes_dark < 30:
            continue

        if minutes_dark < 90:
            severity = "low"
        elif minutes_dark < 240:
            severity = "medium"
        else:
            severity = "high"

        flagged_vessels.append({
            "vessel_id": vessel["vessel_id"],
            "lat": vessel["lat"],
            "lon": vessel["lon"],
            "flagged_reason": f"No signal for about {int(minutes_dark)} minutes.",
            "severity": severity,
        })

    return flagged_vessels
