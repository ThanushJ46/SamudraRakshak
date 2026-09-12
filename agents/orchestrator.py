import json
import os

from agents.dark_vessel_agent import find_dark_vessels
from agents.route_agent import optimize_route
from agents.debris_agent import plan_cleanup_route
from utils.gfw_client import get_vessel_positions

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


def check_dark_vessels(area: dict = None) -> list:
    if area is None:
        area = DEFAULT_AREA

    vessel_list = get_vessel_positions(area)
    flagged_vessels = find_dark_vessels(vessel_list)

    memory = _load_memory()
    vessels_worth_showing = []

    for vessel in flagged_vessels:
        vessel_id = vessel["vessel_id"]
        new_severity = vessel["severity"]
        previously_seen_severity = memory.get(vessel_id)

        is_brand_new_vessel = previously_seen_severity is None
        severity_got_worse = (
            not is_brand_new_vessel
            and SEVERITY_RANK[new_severity] > SEVERITY_RANK[previously_seen_severity]
        )

        if is_brand_new_vessel or severity_got_worse:
            vessels_worth_showing.append(vessel)

        # keep memory updated either way
        memory[vessel_id] = new_severity

    _save_memory(memory)
    return vessels_worth_showing


def get_optimized_route(start: dict, end: dict) -> dict:
    return optimize_route(start, end)


def get_cleanup_plan(start: dict) -> dict:
    with open(DEBRIS_FILE_PATH, "r") as debris_file:
        debris_data = json.load(debris_file)
    debris_list = debris_data["debris_sightings"]
    return plan_cleanup_route(start, debris_list)
