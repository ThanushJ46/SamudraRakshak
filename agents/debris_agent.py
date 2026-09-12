# TEMPORARY STUB - replace with the real version.

def plan_cleanup_route(start: dict, debris_list: list) -> dict:
    visit_order = [d["debris_id"] for d in debris_list]
    waypoints = [start] + [{"lat": d["lat"], "lon": d["lon"]} for d in debris_list]

    total_distance_km = 0.0
    for i in range(len(waypoints) - 1):
        lat_diff = waypoints[i + 1]["lat"] - waypoints[i]["lat"]
        lon_diff = waypoints[i + 1]["lon"] - waypoints[i]["lon"]
        total_distance_km += ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111

    return {
        "visit_order": visit_order,
        "waypoints": waypoints,
        "total_distance_km": round(total_distance_km, 1),
    }
