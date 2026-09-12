"""
Verification script for Person B's deliverables in Maritime Guardian:
1. data/sample_debris.json      -> Sample debris sightings dataset
2. agents/route_agent.py        -> optimize_route()
3. agents/debris_agent.py       -> plan_cleanup_route()

Run with: python test_person_b.py
"""

import json
import os
from agents.route_agent import optimize_route
from agents.debris_agent import plan_cleanup_route


def run_tests():
    print("=" * 65)
    print("  MARITIME GUARDIAN -- PERSON B VERIFICATION TEST SUITE")
    print("=" * 65)

    # -------------------------------------------------------------
    # Test 1: Route Optimization Agent (Open-Meteo Integration)
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing agents/route_agent.py: optimize_route()...")
    # Sample coastal journey: Chennai Port to Ennore Port (Coromandel Coast)
    start_point = {"lat": 13.0827, "lon": 80.2707}  # Chennai Port
    end_point = {"lat": 13.2600, "lon": 80.3300}    # Ennore Port / North offshore

    print(f"Start Point: {start_point}")
    print(f"End Point:   {end_point}")

    route_result = optimize_route(start_point, end_point)

    print("\nRoute Optimization Results:")
    print(f"  - Total Distance:        {route_result['distance_km']} km")
    print(f"  - Baseline Fuel:         {route_result['baseline_fuel_liters']} L")
    print(f"  - Estimated Fuel (Opt):  {route_result['estimated_fuel_liters']} L")

    if route_result['baseline_fuel_liters'] > 0:
        fuel_saved = round(route_result['baseline_fuel_liters'] - route_result['estimated_fuel_liters'], 2)
        saved_pct = round((fuel_saved / route_result['baseline_fuel_liters']) * 100, 1)
        print(f"  - Fuel Saved:            {fuel_saved} L ({saved_pct}% reduction)")

    print(f"  - Waypoint Count:        {len(route_result['waypoints'])}")
    for i, wp in enumerate(route_result['waypoints']):
        print(f"      Waypoint {i + 1}: Lat {wp['lat']}, Lon {wp['lon']}")

    # Validation checks
    assert "waypoints" in route_result, "Missing 'waypoints' key"
    assert "distance_km" in route_result, "Missing 'distance_km' key"
    assert "baseline_fuel_liters" in route_result, "Missing 'baseline_fuel_liters' key"
    assert "estimated_fuel_liters" in route_result, "Missing 'estimated_fuel_liters' key"
    assert len(route_result["waypoints"]) >= 2, "Route should have at least start and end waypoints"
    print("[PASS] Test 1 Passed!")

    # -------------------------------------------------------------
    # Test 2: Debris Dataset Loading
    # -------------------------------------------------------------
    print("\n" + "-" * 65)
    print("[TEST 2] Testing data/sample_debris.json loading...")
    data_path = os.path.join(os.path.dirname(__file__), "data", "sample_debris.json")
    with open(data_path, "r", encoding="utf-8") as f:
        debris_data = json.load(f)

    sightings = debris_data.get("debris_sightings", [])
    print(f"Loaded {len(sightings)} debris sightings from {data_path}")
    print(f"Note: {debris_data.get('_note')}")

    assert len(sightings) >= 8, "Expected at least 8 sample debris sightings"
    for item in sightings[:3]:
        print(f"  - [{item['debris_id']}] Lat: {item['lat']}, Lon: {item['lon']} | {item['description']}")
    print("  ... and more.")
    print("[PASS] Test 2 Passed!")

    # -------------------------------------------------------------
    # Test 3: Debris Cleanup Route Planning (Nearest-Neighbor)
    # -------------------------------------------------------------
    print("\n" + "-" * 65)
    print("[TEST 3] Testing agents/debris_agent.py: plan_cleanup_route()...")
    boat_base = {"lat": 13.0800, "lon": 80.3000}
    print(f"Cleanup Boat Base: {boat_base}")

    cleanup_result = plan_cleanup_route(boat_base, sightings)

    print("\nCleanup Route Results:")
    print(f"  - Total Sightings Visited: {len(cleanup_result['visit_order'])}")
    print(f"  - Total Distance:          {cleanup_result['total_distance_km']} km")
    print(f"  - Visit Order:             {' -> '.join(cleanup_result['visit_order'])}")
    print(f"  - Waypoints Generated:     {len(cleanup_result['waypoints'])}")

    # Validation checks
    assert "visit_order" in cleanup_result, "Missing 'visit_order' key"
    assert "waypoints" in cleanup_result, "Missing 'waypoints' key"
    assert "total_distance_km" in cleanup_result, "Missing 'total_distance_km' key"
    assert len(cleanup_result["visit_order"]) == len(sightings), "Not all debris points were scheduled"
    assert len(cleanup_result["waypoints"]) == len(sightings) + 1, "Waypoints should include start + all debris points"
    print("[PASS] Test 3 Passed!")

    print("\n" + "=" * 65)
    print("  ALL PERSON B DELIVERABLES VERIFIED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
