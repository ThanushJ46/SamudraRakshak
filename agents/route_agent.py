"""
Route Optimization Agent for Maritime Guardian.

Given a start and end location, this agent:
1. Samples real wind speeds from Open-Meteo at several positions offset
   sideways from the direct line, at three points along the route.
2. Picks the calmest option at each point.
3. Costs BOTH paths with a fuel model where wind raises consumption per km,
   and takes the detour only if it genuinely comes out cheaper.

The reported saving is always derived from the path actually chosen. If the
calmer route is not cheaper, the agent returns the direct route and reports
no saving at all.
"""

import math
import requests

# Constant demo fuel consumption rate for an offshore patrol/cargo vessel.
# Note: This is an approximate demo figure (liters of marine diesel per km),
# chosen for clarity and predictable demonstration in hackathon evaluations.
# NOT scientifically precise -- a real vessel might range from 1 to 10+ L/km
# depending on size, speed, cargo, and sea state.
FUEL_RATE_LITERS_PER_KM = 3.5

# How much wind raises fuel burn PER KILOMETRE.
# effective rate = FUEL_RATE_LITERS_PER_KM x (1 + WIND_FUEL_PENALTY_PER_KMH x wind)
# At 20 km/h of wind that is +20% fuel per km.
#
# This is an approximate demo coefficient, NOT a measured vessel curve. What
# matters is that the saving we report is COMPUTED from it and from the path we
# actually chose - an earlier version applied a fixed 5-15% discount to the
# baseline regardless of the route, which reported a saving on journeys that
# were actually longer and more expensive.
WIND_FUEL_PENALTY_PER_KMH = 0.01

# How far sideways we are willing to look for calmer water, in km.
# A 2 km nudge is pointless - the wind there is identical. 0.0 must stay in the
# list: it is the direct route, and our baseline.
LATERAL_OFFSETS_KM = [-30.0, -15.0, 0.0, 15.0, 30.0]


def haversine_distance(coord1: dict, coord2: dict) -> float:
    """
    Calculates great-circle distance between two (lat, lon) coordinates in kilometers.
    Uses the standard Haversine formula on Earth's mean radius (6371 km).
    """
    lat1, lon1 = coord1["lat"], coord1["lon"]
    lat2, lon2 = coord2["lat"], coord2["lon"]

    # Convert degrees to radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return 6371.0 * c


def _safe_float(value, default=0.0):
    """Safely convert a value to float, returning default if conversion fails."""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def _fetch_wind_speeds(sample_points):
    """
    Query the free Open-Meteo API for current wind speeds at the given points.
    Returns a list of wind speed floats (km/h), or an empty list on failure.
    """
    wind_speeds = []

    try:
        lat_list = ",".join(str(p["lat"]) for p in sample_points)
        lon_list = ",".join(str(p["lon"]) for p in sample_points)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat_list,
            "longitude": lon_list,
            "current": "wind_speed_10m",
        }

        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            print(
                f"[RouteAgent Warning] Open-Meteo API returned status "
                f"{response.status_code}. Using straight-line path."
            )
            return []

        data = response.json()

        # If multiple coordinates were queried, API returns a list of result objects
        if isinstance(data, list):
            for item in data:
                speed = item.get("current", {}).get("wind_speed_10m")
                wind_speeds.append(_safe_float(speed))
        elif isinstance(data, dict):
            speed = data.get("current", {}).get("wind_speed_10m")
            wind_speeds.append(_safe_float(speed))

    except Exception as error:
        print(
            f"[RouteAgent Warning] Could not reach Open-Meteo API ({error}). "
            f"Using straight-line path fallback."
        )
        return []

    return wind_speeds


def _fuel_for_leg(distance_km: float, wind_speed_kmh: float) -> float:
    """
    Fuel for one leg, in litres, accounting for how rough the water is.

    Sailing into wind and chop costs more fuel PER KILOMETRE, which is the
    whole reason a weather detour can pay for itself: a slightly longer route
    through calm water can burn less than a short route through a gale.

    effective rate = base rate x (1 + penalty x wind speed)

    WIND_FUEL_PENALTY_PER_KMH is an approximate demo coefficient, not a
    measured vessel curve - but the SAVING IS COMPUTED FROM IT rather than
    asserted, so the number on screen is always consistent with the path we
    actually chose.
    """
    effective_rate = FUEL_RATE_LITERS_PER_KM * (
        1.0 + WIND_FUEL_PENALTY_PER_KMH * max(wind_speed_kmh, 0.0)
    )
    return distance_km * effective_rate


def _fuel_for_path(points: list, winds: list) -> float:
    """
    Total fuel along a path.

    points -> [start, mid1, mid2, mid3, end]
    winds  -> wind speed at each of the three middle points

    Each leg is charged at the wind of the sampled point it runs toward, with
    the final leg reusing the last sample. Rough, but applied identically to
    both the baseline and the optimized path, so the comparison is fair.
    """
    total_fuel = 0.0

    for index in range(len(points) - 1):
        leg_distance = haversine_distance(points[index], points[index + 1])
        # Use the wind at the sample point this leg heads towards.
        wind_index = min(index, len(winds) - 1) if winds else 0
        wind_here = winds[wind_index] if winds else 0.0
        total_fuel += _fuel_for_leg(leg_distance, wind_here)

    return total_fuel


def _path_distance_km(points: list) -> float:
    """Total distance along an ordered list of points."""
    return sum(
        haversine_distance(points[i], points[i + 1]) for i in range(len(points) - 1)
    )


def optimize_route(start: dict, end: dict) -> dict:
    """
    Optimizes a maritime route between start and end coordinates.

    Args:
        start: {"lat": float, "lon": float}
        end:   {"lat": float, "lon": float}

    Returns:
        dict: {
            "waypoints": [{"lat": float, "lon": float}, ...],
            "distance_km": float,
            "baseline_fuel_liters": float,
            "estimated_fuel_liters": float
        }

    HOW THE SAVING IS EARNED
    ------------------------
    At three points along the route we sample the wind at several positions
    offset sideways from the direct line, then pick the calmest option at each
    point. Fuel is charged per kilometre with a penalty for wind, so a longer
    but calmer path can genuinely cost less.

    If the calmer path does NOT come out cheaper, we return the straight line
    with estimated_fuel equal to baseline_fuel and claim no saving at all.
    The reported figure is always computed from the path we actually chose -
    never a fixed percentage applied to the baseline.
    """
    straight_line_km = haversine_distance(start, end)

    start_wp = {"lat": round(start["lat"], 4), "lon": round(start["lon"], 4)}
    end_wp = {"lat": round(end["lat"], 4), "lon": round(end["lon"], 4)}

    # Edge case: start and end are the same (or extremely close).
    if straight_line_km < 0.01:
        return {
            "waypoints": [start_wp, end_wp],
            "distance_km": 0.0,
            "baseline_fuel_liters": 0.0,
            "estimated_fuel_liters": 0.0,
        }

    # ---- 1. The direct points we would pass through ---------------------
    fractions = [0.25, 0.50, 0.75]
    direct_points = []
    for fraction in fractions:
        direct_points.append({
            "lat": round(start["lat"] + fraction * (end["lat"] - start["lat"]), 4),
            "lon": round(start["lon"] + fraction * (end["lon"] - start["lon"]), 4),
        })

    # ---- 2. Candidate positions offset sideways from each -------------
    # A 2 km nudge is pointless: the wind there is the same. We look far
    # enough out for conditions to actually differ.
    delta_lat = end["lat"] - start["lat"]
    delta_lon = end["lon"] - start["lon"]
    length = math.sqrt(delta_lat ** 2 + delta_lon ** 2)

    # Unit vector perpendicular to the direction of travel, in degrees.
    perpendicular_lat = -delta_lon / length
    perpendicular_lon = delta_lat / length

    # Roughly 1 degree ~ 111 km, so convert our km offsets into degrees.
    candidates_per_point = []
    for point in direct_points:
        candidates = []
        for offset_km in LATERAL_OFFSETS_KM:
            offset_degrees = offset_km / 111.0
            candidates.append({
                "lat": round(point["lat"] + perpendicular_lat * offset_degrees, 4),
                "lon": round(point["lon"] + perpendicular_lon * offset_degrees, 4),
            })
        candidates_per_point.append(candidates)

    # ---- 3. One weather call for every candidate ------------------------
    flat_candidates = [c for candidates in candidates_per_point for c in candidates]
    all_winds = _fetch_wind_speeds(flat_candidates)

    straight_path = [start_wp] + direct_points + [end_wp]

    # No weather data: we cannot justify any detour, so claim no saving.
    if len(all_winds) != len(flat_candidates):
        if not all_winds:
            print("[RouteAgent] No wind data - reporting the straight route with no saving.")
        else:
            print("[RouteAgent] Incomplete wind data - reporting the straight route with no saving.")
        straight_fuel = round(straight_line_km * FUEL_RATE_LITERS_PER_KM, 2)
        return {
            "waypoints": [start_wp, end_wp],
            "distance_km": round(straight_line_km, 2),
            "baseline_fuel_liters": straight_fuel,
            "estimated_fuel_liters": straight_fuel,
        }

    # ---- 4. Pick the calmest candidate at each point --------------------
    number_of_offsets = len(LATERAL_OFFSETS_KM)
    zero_offset_index = LATERAL_OFFSETS_KM.index(0.0)

    chosen_points = []
    chosen_winds = []
    direct_winds = []

    for point_index, candidates in enumerate(candidates_per_point):
        winds_here = all_winds[
            point_index * number_of_offsets : (point_index + 1) * number_of_offsets
        ]

        direct_winds.append(winds_here[zero_offset_index])

        calmest_index = min(range(len(winds_here)), key=lambda i: winds_here[i])
        chosen_points.append(candidates[calmest_index])
        chosen_winds.append(winds_here[calmest_index])

    detour_path = [start_wp] + chosen_points + [end_wp]

    # ---- 5. Cost both paths honestly ------------------------------------
    baseline_fuel = _fuel_for_path(straight_path, direct_winds)
    detour_fuel = _fuel_for_path(detour_path, chosen_winds)

    # ---- 6. Only detour if it actually pays ----------------------------
    if detour_fuel < baseline_fuel:
        return {
            "waypoints": detour_path,
            "distance_km": round(_path_distance_km(detour_path), 2),
            "baseline_fuel_liters": round(baseline_fuel, 2),
            "estimated_fuel_liters": round(detour_fuel, 2),
        }

    # The calm-water detour was not worth the extra distance. Say so, and
    # report no saving rather than inventing one.
    print("[RouteAgent] Detour would not save fuel - keeping the direct route.")
    return {
        "waypoints": straight_path,
        "distance_km": round(_path_distance_km(straight_path), 2),
        "baseline_fuel_liters": round(baseline_fuel, 2),
        "estimated_fuel_liters": round(baseline_fuel, 2),
    }
