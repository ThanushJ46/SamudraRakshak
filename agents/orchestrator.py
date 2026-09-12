import json
import os

from agents.dark_vessel_agent import find_dark_vessels
from agents.route_agent import optimize_route
from agents.debris_agent import plan_cleanup_route
from utils.gfw_client import get_vessel_positions, generate_sample_vessels

MEMORY_FILE_PATH = "data/flagged_history.json"
DEBRIS_FILE_PATH = "data/sample_debris.json"

DEFAULT_AREA = {
    "min_lat": 9.0,
    "max_lat": 10.5,
    "min_lon": 79.0,
    "max_lon": 80.5,
}

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


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
                # every currently-flagged vessel, every scan, plus one
                # extra field on each:
                #   "is_new": True if this vessel is newly flagged or its
                #             severity just got worse, else False
                ...
            ],
            "data_source": "live" | "demo" | "demo (live call failed)"
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
        previously_seen_severity = memory.get(vessel_id)

        is_brand_new_vessel = previously_seen_severity is None
        severity_got_worse = (
            not is_brand_new_vessel
            and SEVERITY_RANK[new_severity] > SEVERITY_RANK.get(previously_seen_severity, 0)
        )

        # Copy the vessel and add the extra flag, so we never mutate what the
        # agent handed us.
        vessel_with_flag = dict(vessel)
        vessel_with_flag["is_new"] = is_brand_new_vessel or severity_got_worse
        all_flagged_vessels.append(vessel_with_flag)

        # Remember this severity for next time.
        memory[vessel_id] = new_severity

    _save_memory(memory)

    return {
        "vessels": all_flagged_vessels,
        "data_source": data_source,
    }


def get_optimized_route(start: dict, end: dict) -> dict:
    return optimize_route(start, end)


def get_cleanup_plan(start: dict) -> dict:
    with open(DEBRIS_FILE_PATH, "r") as debris_file:
        debris_data = json.load(debris_file)
    debris_list = debris_data["debris_sightings"]
    return plan_cleanup_route(start, debris_list)