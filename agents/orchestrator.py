import json
import os

from agents.dark_vessel_agent import find_dark_vessels
from agents.route_agent import optimize_route
from agents.debris_agent import plan_cleanup_route
from utils.gfw_client import get_vessel_positions, generate_sample_vessels
from utils.triage import triage_alerts

MEMORY_FILE_PATH = "data/flagged_history.json"
DEBRIS_FILE_PATH = "data/sample_debris.json"

DEFAULT_AREA = {
    "min_lat": 9.0,
    "max_lat": 10.5,
    "min_lon": 79.0,
    "max_lon": 80.5,
}

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}

# ---------------------------------------------------------------------------
# INTERCEPTION - this is where the three agents stop being three separate
# tools and start working together.
#
# When the dark-vessel agent flags something worth responding to, we hand that
# vessel's position straight to the ROUTE agent and ask it for the fastest way
# there from the nearest patrol base. The officer gets an action ("Mandapam,
# 34 km, 1.0 hours, 118 L"), not just a red dot on a map.
# ---------------------------------------------------------------------------

# Coast guard / marine police bases we can dispatch from.
# APPROXIMATE positions, for demo purposes only.
PATROL_BASES = {
    "Mandapam": {"lat": 9.2760, "lon": 79.1250},
    "Rameswaram": {"lat": 9.2876, "lon": 79.3129},
    "Tuticorin": {"lat": 8.7642, "lon": 78.1348},
}

# Cruising speed of a patrol vessel, km/h. An approximate demo figure - real
# interceptor craft vary widely - used only to turn distance into an ETA.
PATROL_SPEED_KMH = 35.0

# Which categories are worth sending a boat for. A routine_gap is a radio
# fault in open water; dispatching anyone would be a waste.
CATEGORIES_NEEDING_RESPONSE = (
    "foreign_intrusion",
    "border_safety_alert",
    "unidentified_near_zone",
)

# Each interception costs one route-agent call, which costs one weather API
# call. Cap it so a busy scan cannot stall the dashboard.
MAX_INTERCEPTIONS_PER_SCAN = 3


def _nearest_patrol_base(vessel: dict) -> tuple:
    """
    Find the patrol base closest to a vessel.

    Returns (base_name, base_coordinates). Uses the route agent's own
    haversine helper so distances are measured the same way everywhere.
    """
    from agents.route_agent import haversine_distance

    closest_name = None
    closest_base = None
    shortest_distance = float("inf")

    for base_name, base_coordinates in PATROL_BASES.items():
        distance = haversine_distance(base_coordinates, vessel)
        if distance < shortest_distance:
            shortest_distance = distance
            closest_name = base_name
            closest_base = base_coordinates

    return (closest_name, closest_base)


def plan_interception(vessel: dict) -> dict:
    """
    Work out how to reach a flagged vessel.

    Input:  a flagged vessel dict (needs "lat" and "lon")
    Output: {
                "base_name": str,
                "distance_km": float,
                "fuel_liters": float,
                "eta_hours": float,
                "waypoints": [{"lat", "lon"}, ...],
            }
            or None if the route could not be planned.

    This is the dark-vessel agent's output becoming the route agent's input -
    one agent's finding driving another agent's work, decided by the category
    rather than by a human clicking a second button.
    """
    try:
        base_name, base_coordinates = _nearest_patrol_base(vessel)

        route = optimize_route(
            base_coordinates,
            {"lat": vessel["lat"], "lon": vessel["lon"]},
        )

        distance_km = route["distance_km"]

        return {
            "base_name": base_name,
            "distance_km": distance_km,
            "fuel_liters": route["estimated_fuel_liters"],
            "eta_hours": round(distance_km / PATROL_SPEED_KMH, 1),
            "waypoints": route["waypoints"],
        }
    except Exception as error:
        # An interception is a bonus, never a reason for the scan to fail.
        print(f"[orchestrator] Could not plan interception: {error}")
        return None


# How much each category worries us, so we can tell an escalation from a
# sideways move. Used for both "is_new" and interception priority.
CATEGORY_CONCERN = {
    "routine_gap": 0,
    "unidentified_near_zone": 1,
    "border_safety_alert": 2,
    "foreign_intrusion": 3,
}


def _remembered_entry(memory: dict, vessel_id: str):
    """
    Read one vessel out of the memory file, in a shape we can rely on.

    Older versions stored just a severity string per vessel. This upgrades
    those entries on the fly rather than throwing the history away, so an
    existing data/flagged_history.json keeps working.
    """
    entry = memory.get(vessel_id)

    if entry is None:
        return None

    # Old format: the value was the severity string itself.
    if isinstance(entry, str):
        return {"severity": entry, "category": "routine_gap", "times_flagged": 1}

    return {
        "severity": entry.get("severity", "low"),
        "category": entry.get("category", "routine_gap"),
        "times_flagged": entry.get("times_flagged", 1),
    }


def _load_memory():
    if not os.path.exists(MEMORY_FILE_PATH):
        return {}
    with open(MEMORY_FILE_PATH, "r") as memory_file:
        try:
            return json.load(memory_file)
        except json.JSONDecodeError:
            return {}


def _save_memory(memory_dict):
    os.makedirs(os.path.dirname(MEMORY_FILE_PATH), exist_ok=True)
    with open(MEMORY_FILE_PATH, "w") as memory_file:
        json.dump(memory_dict, memory_file, indent=2)


def check_dark_vessels(area: dict = None, use_demo_data: bool = False) -> dict:
    """
    Find every currently dark vessel, and say where the data came from.

    Inputs:
        area          -> bounding box dict, or None for DEFAULT_AREA
        use_demo_data -> True to deliberately use sample data instead of the
                         live Global Fishing Watch feed

    Returns:
        {
            "vessels": [
                # every currently-flagged vessel, every scan, plus these
                # extra fields on each:
                #   "is_new":            newly flagged, or severity/category
                #                        got worse since the last scan
                #   "times_flagged":     how many scans have flagged it
                #   "previous_category": what it was last scan, or None
                #   "interception":      route from the nearest patrol base,
                #                        or None if no response is needed
                ...
            ],
            "data_source": "live" | "demo" | "demo (live call failed)",
            "triage": {"ranking": [...], "reasoning": str, "available": bool}
        }

    The "data_source" value reports what ACTUALLY ran, not what was asked for.
    If the caller wanted live data and the call failed, we still return demo
    data so the dashboard keeps working - but we say so plainly.
    """
    if area is None:
        area = DEFAULT_AREA

    if use_demo_data:
        # The user explicitly asked for demo data.
        vessel_list = generate_sample_vessels(area)
        data_source = "demo"
    else:
        # Try the real feed. get_vessel_positions raises rather than hiding a
        # failure, so we are the ones who decide to fall back - and we record
        # that we did.
        try:
            vessel_list = get_vessel_positions(area)
            data_source = "live"
        except Exception as error:
            print(f"[orchestrator] Live GFW call failed ({error}). Falling back to demo data.")
            vessel_list = generate_sample_vessels(area)
            data_source = "demo (live call failed)"

    flagged_vessels = find_dark_vessels(vessel_list)

    # Memory changes how a vessel is PRESENTED, never whether it appears.
    # Every vessel that is currently flagged goes into the list every single
    # scan - otherwise a second scan with no changes would blank the map and
    # look broken. We only use memory to mark which ones are newly interesting.
    memory = _load_memory()
    all_flagged_vessels = []

    for vessel in flagged_vessels:
        vessel_id = vessel["vessel_id"]
        new_severity = vessel["severity"]
        new_category = vessel["category"]

        remembered = _remembered_entry(memory, vessel_id)

        is_brand_new_vessel = remembered is None

        if is_brand_new_vessel:
            severity_got_worse = False
            category_got_worse = False
            times_flagged = 1
        else:
            severity_got_worse = (
                SEVERITY_RANK.get(new_severity, 0)
                > SEVERITY_RANK.get(remembered["severity"], 0)
            )
            # A vessel moving OUT of "routine_gap" into a category we would
            # act on is the single most important change to catch - and it can
            # happen while severity stays "low", which the old severity-only
            # check missed completely.
            category_got_worse = (
                CATEGORY_CONCERN.get(new_category, 0)
                > CATEGORY_CONCERN.get(remembered["category"], 0)
            )
            times_flagged = remembered["times_flagged"] + 1

        # Copy the vessel and add the extra fields, so we never mutate what
        # the agent handed us.
        vessel_with_flag = dict(vessel)
        vessel_with_flag["is_new"] = (
            is_brand_new_vessel or severity_got_worse or category_got_worse
        )
        vessel_with_flag["times_flagged"] = times_flagged
        vessel_with_flag["previous_category"] = (
            None if is_brand_new_vessel else remembered["category"]
        )
        vessel_with_flag["interception"] = None
        all_flagged_vessels.append(vessel_with_flag)

        # Remember what we saw, for next time.
        memory[vessel_id] = {
            "severity": new_severity,
            "category": new_category,
            "times_flagged": times_flagged,
        }

    _save_memory(memory)

    # ---- Hand the worst findings to the ROUTE agent ---------------------
    # This is the multi-step bit: the dark-vessel agent's output becomes the
    # route agent's input, automatically, chosen by category and severity.
    vessels_needing_response = [
        vessel for vessel in all_flagged_vessels
        if vessel["category"] in CATEGORIES_NEEDING_RESPONSE
    ]
    vessels_needing_response.sort(
        key=lambda v: (
            -CATEGORY_CONCERN.get(v["category"], 0),
            -SEVERITY_RANK.get(v["severity"], 0),
        )
    )

    for vessel in vessels_needing_response[:MAX_INTERCEPTIONS_PER_SCAN]:
        vessel["interception"] = plan_interception(vessel)

    # ---- Ask the model to decide what to act on first -------------------
    # Everything above this line was decided by rules. This is the one step
    # where the AI weighs the whole set against itself and produces a
    # judgement - which the officer can disagree with, because the reasoning
    # is shown alongside it.
    triage = triage_alerts(all_flagged_vessels)

    return {
        "vessels": all_flagged_vessels,
        "data_source": data_source,
        "triage": triage,
    }


def get_optimized_route(start: dict, end: dict) -> dict:
    return optimize_route(start, end)


def get_cleanup_plan(start: dict) -> dict:
    with open(DEBRIS_FILE_PATH, "r") as debris_file:
        debris_data = json.load(debris_file)
    debris_list = debris_data["debris_sightings"]
    return plan_cleanup_route(start, debris_list)