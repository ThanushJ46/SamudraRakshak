# TEMPORARY STUB - replace with the real version.

import math


def _straight_line_distance_km(start: dict, end: dict) -> float:
    lat_diff = end["lat"] - start["lat"]
    lon_diff = end["lon"] - start["lon"]
    return math.sqrt(lat_diff ** 2 + lon_diff ** 2) * 111


def optimize_route(start: dict, end: dict) -> dict:
    distance_km = _straight_line_distance_km(start, end)
    baseline_fuel_liters = distance_km * 3.5
    estimated_fuel_liters = baseline_fuel_liters * 0.9

    return {
        "waypoints": [start, end],
        "distance_km": round(distance_km, 1),
        "baseline_fuel_liters": round(baseline_fuel_liters, 1),
        "estimated_fuel_liters": round(estimated_fuel_liters, 1),
    }
