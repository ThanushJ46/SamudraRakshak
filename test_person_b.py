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


def test_route_optimization():
    """Test 1: Route Optimization Agent with live Open-Meteo weather data."""
    print("\n[TEST 1] Testing agents/route_agent.py: optimize_route()...")
    # Sample coastal journey: Chennai Port to Ennore Port (Coromandel Coast)
    start_point = {"lat": 13.0827, "lon": 80.2707}  # Chennai Port
    end_point = {"lat": 13.2600, "lon": 80.3300}    # Ennore Port / North offshore

    print(f"  Start Point: {start_point}")
    print(f"  End Point:   {end_point}")

    route_result = optimize_route(start_point, end_point)

    print("\n  Route Optimization Results:")
    print(f"    - Total Distance:        {route_result['distance_km']} km")
    print(f"    - Baseline Fuel:         {route_result['baseline_fuel_liters']} L")
    print(f"    - Estimated Fuel (Opt):  {route_result['estimated_fuel_liters']} L")

    if route_result["baseline_fuel_liters"] > 0:
        fuel_saved = round(
            route_result["baseline_fuel_liters"] - route_result["estimated_fuel_liters"], 2
        )
        saved_pct = round((fuel_saved / route_result["baseline_fuel_liters"]) * 100, 1)
        print(f"    - Fuel Saved:            {fuel_saved} L ({saved_pct}% reduction)")

    print(f"    - Waypoint Count:        {len(route_result['waypoints'])}")
    for i, wp in enumerate(route_result["waypoints"]):
        print(f"        Waypoint {i + 1}: Lat {wp['lat']}, Lon {wp['lon']}")

    # Structural validation
    assert "waypoints" in route_result, "Missing 'waypoints' key"
    assert "distance_km" in route_result, "Missing 'distance_km' key"
    assert "baseline_fuel_liters" in route_result, "Missing 'baseline_fuel_liters' key"
    assert "estimated_fuel_liters" in route_result, "Missing 'estimated_fuel_liters' key"
    assert len(route_result["waypoints"]) >= 2, "Route needs at least start and end waypoints"
    assert route_result["distance_km"] >= 0, "Distance cannot be negative"
    assert route_result["estimated_fuel_liters"] <= route_result["baseline_fuel_liters"], \
        "Optimized fuel should not exceed baseline"

    # Every waypoint must have lat and lon keys
    for wp in route_result["waypoints"]:
        assert "lat" in wp and "lon" in wp, f"Waypoint missing lat/lon: {wp}"

    print("  [PASS] Test 1 Passed!")
    return route_result


def test_route_same_start_end():
    """Test 1b: Edge case -- start and end are the same point."""
    print("\n[TEST 1b] Edge case: start == end (zero-distance route)...")
    same_point = {"lat": 13.0827, "lon": 80.2707}
    result = optimize_route(same_point, same_point)

    assert result["distance_km"] == 0.0, "Zero-distance route should be 0 km"
    assert result["baseline_fuel_liters"] == 0.0, "Zero-distance fuel should be 0"
    assert result["estimated_fuel_liters"] == 0.0, "Zero-distance optimized fuel should be 0"
    assert len(result["waypoints"]) == 2, "Should still have start + end waypoints"
    print("  [PASS] Test 1b Passed!")


def test_debris_data_loading():
    """Test 2: Load and validate sample_debris.json."""
    print("\n" + "-" * 65)
    print("[TEST 2] Testing data/sample_debris.json loading...")
    data_path = os.path.join(os.path.dirname(__file__) or ".", "data", "sample_debris.json")
    with open(data_path, "r", encoding="utf-8") as f:
        debris_data = json.load(f)

    sightings = debris_data.get("debris_sightings", [])
    print(f"  Loaded {len(sightings)} debris sightings")
    print(f"  Note: {debris_data.get('_note')}")

    # Validate count
    assert len(sightings) >= 8, "Expected at least 8 sample debris sightings"

    # Validate every item has the required keys
    required_keys = {"debris_id", "lat", "lon", "description"}
    for item in sightings:
        missing = required_keys - set(item.keys())
        assert not missing, f"Item {item.get('debris_id', '?')} missing keys: {missing}"

    # Validate all debris_ids are unique
    ids = [s["debris_id"] for s in sightings]
    assert len(ids) == len(set(ids)), f"Duplicate debris_id found: {ids}"

    for item in sightings[:3]:
        print(f"    - [{item['debris_id']}] ({item['lat']}, {item['lon']}) | {item['description']}")
    print("    ... and more.")
    print("  [PASS] Test 2 Passed!")
    return sightings


def test_cleanup_route(sightings):
    """Test 3: Debris cleanup route planning with nearest-neighbor."""
    print("\n" + "-" * 65)
    print("[TEST 3] Testing agents/debris_agent.py: plan_cleanup_route()...")
    boat_base = {"lat": 13.0800, "lon": 80.3000}
    print(f"  Cleanup Boat Base: {boat_base}")

    # Pass a copy so the original sightings list stays intact for later checks
    cleanup_result = plan_cleanup_route(boat_base, list(sightings))

    print("\n  Cleanup Route Results:")
    print(f"    - Total Sightings Visited: {len(cleanup_result['visit_order'])}")
    print(f"    - Total Distance:          {cleanup_result['total_distance_km']} km")
    print(f"    - Visit Order:             {' -> '.join(cleanup_result['visit_order'])}")
    print(f"    - Waypoints Generated:     {len(cleanup_result['waypoints'])}")

    # Structural validation
    assert "visit_order" in cleanup_result, "Missing 'visit_order' key"
    assert "waypoints" in cleanup_result, "Missing 'waypoints' key"
    assert "total_distance_km" in cleanup_result, "Missing 'total_distance_km' key"
    assert len(cleanup_result["visit_order"]) == len(sightings), \
        "Not all debris points were scheduled"
    assert len(cleanup_result["waypoints"]) == len(sightings) + 1, \
        "Waypoints should include start + all debris points"
    assert cleanup_result["total_distance_km"] >= 0, "Total distance cannot be negative"

    # Every waypoint must have lat and lon
    for wp in cleanup_result["waypoints"]:
        assert "lat" in wp and "lon" in wp, f"Waypoint missing lat/lon: {wp}"

    # Verify the original sightings list was NOT mutated
    assert len(sightings) >= 8, "Original sightings list was mutated!"

    print("  [PASS] Test 3 Passed!")


def test_cleanup_empty_list():
    """Test 3b: Edge case -- empty debris list."""
    print("\n[TEST 3b] Edge case: empty debris list...")
    boat_base = {"lat": 13.0800, "lon": 80.3000}
    result = plan_cleanup_route(boat_base, [])

    assert result["visit_order"] == [], "Empty input should give empty visit order"
    assert len(result["waypoints"]) == 1, "Empty input should give just the start waypoint"
    assert result["total_distance_km"] == 0.0, "Empty input should have zero distance"
    print("  [PASS] Test 3b Passed!")


def test_cleanup_single_item():
    """Test 3c: Edge case -- single debris item."""
    print("\n[TEST 3c] Edge case: single debris item...")
    boat_base = {"lat": 13.0800, "lon": 80.3000}
    single = [{"debris_id": "test-001", "lat": 13.10, "lon": 80.32, "description": "test item"}]
    result = plan_cleanup_route(boat_base, single)

    assert result["visit_order"] == ["test-001"], "Should visit the one item"
    assert len(result["waypoints"]) == 2, "Start + 1 debris = 2 waypoints"
    assert result["total_distance_km"] > 0, "Distance should be positive"
    print("  [PASS] Test 3c Passed!")


def run_tests():
    print("=" * 65)
    print("  MARITIME GUARDIAN -- PERSON B VERIFICATION TEST SUITE")
    print("=" * 65)

    # Route optimization tests
    test_route_optimization()
    test_route_same_start_end()

    # Debris data tests
    sightings = test_debris_data_loading()

    # Cleanup route tests
    test_cleanup_route(sightings)
    test_cleanup_empty_list()
    test_cleanup_single_item()

    print("\n" + "=" * 65)
    print("  ALL PERSON B TESTS PASSED (6/6)")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
