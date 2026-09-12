"""
Debris Cleanup Agent for Maritime Guardian.

Given the cleanup boat's starting coordinate and a list of ocean debris sightings,
this agent plans an efficient collection route using the Nearest-Neighbor algorithm.
"""

import math


def haversine_distance(coord1: dict, coord2: dict) -> float:
    """
    Calculates great-circle distance between two (lat, lon) coordinates in kilometers.
    Uses the standard Haversine formula on Earth's mean radius (6371 km).
    """
    lat1, lon1 = coord1["lat"], coord1["lon"]
    lat2, lon2 = coord2["lat"], coord2["lon"]

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return 6371.0 * c


def plan_cleanup_route(start: dict, debris_list: list[dict]) -> dict:
    """
    Plans a debris cleanup route visiting all debris locations in optimal order
    using a greedy nearest-neighbor approach.

    Args:
        start:       {"lat": float, "lon": float} (vessel starting position)
        debris_list: List of dicts, each shaped:
                     {"debris_id": str, "lat": float, "lon": float, "description": str}

    Returns:
        dict: {
            "visit_order": [debris_id, ...],
            "waypoints": [{"lat": float, "lon": float}, ...],
            "total_distance_km": float
        }
    """
    # If the debris list is empty, return an empty plan
    if not debris_list:
        return {
            "visit_order": [],
            "waypoints": [{"lat": round(start["lat"], 4), "lon": round(start["lon"], 4)}],
            "total_distance_km": 0.0,
        }

    # Track unvisited sightings (make a shallow copy of the input list)
    unvisited = list(debris_list)

    current_pos = {"lat": start["lat"], "lon": start["lon"]}
    visit_order = []
    waypoints = [{"lat": round(start["lat"], 4), "lon": round(start["lon"], 4)}]
    total_distance = 0.0

    # Nearest-neighbor search loop
    while unvisited:
        nearest_index = None
        min_distance = float("inf")

        # Find the unvisited debris closest to current position
        for i, item in enumerate(unvisited):
            target_coord = {"lat": item["lat"], "lon": item["lon"]}
            dist = haversine_distance(current_pos, target_coord)
            if dist < min_distance:
                min_distance = dist
                nearest_index = i

        # Move to the chosen nearest debris
        chosen_debris = unvisited.pop(nearest_index)
        visit_order.append(chosen_debris["debris_id"])
        waypoints.append({
            "lat": round(chosen_debris["lat"], 4),
            "lon": round(chosen_debris["lon"], 4),
        })
        total_distance += min_distance

        # Update current position to this debris point
        current_pos = {"lat": chosen_debris["lat"], "lon": chosen_debris["lon"]}

    return {
        "visit_order": visit_order,
        "waypoints": waypoints,
        "total_distance_km": round(total_distance, 2),
    }
