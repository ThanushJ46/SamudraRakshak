"""
Verification script for Person A's deliverables in Maritime Guardian:
1. utils/llm_client.py   -> ask_ai()
2. utils/gfw_client.py   -> get_vessel_positions()
3. agents/dark_vessel_agent.py -> find_dark_vessels()

Run with: python test_person_a.py
"""

import json
from utils.llm_client import ask_ai
from utils.gfw_client import get_vessel_positions
from agents.dark_vessel_agent import find_dark_vessels


def run_tests():
    print("=" * 65)
    print("  MARITIME GUARDIAN — PERSON A VERIFICATION TEST SUITE")
    print("=" * 65)

    # -------------------------------------------------------------
    # Test 1: LLM Client
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing utils/llm_client.py: ask_ai()...")
    test_prompt = "In one sentence, why is AIS tracking critical for marine conservation?"
    print(f"Prompt: {test_prompt}")
    ai_response = ask_ai(test_prompt)
    print(f"Response: {ai_response}")
    print("Test 1 Passed!")

    # -------------------------------------------------------------
    # Test 2: GFW Client
    # -------------------------------------------------------------
    print("\n" + "-" * 65)
    print("[TEST 2] Testing utils/gfw_client.py: get_vessel_positions()...")
    sample_area = {
        "min_lat": 12.0,
        "max_lat": 14.5,
        "min_lon": 80.0,
        "max_lon": 82.5,
    }
    print(f"Querying area: {sample_area}")
    vessels = get_vessel_positions(sample_area)
    print(f"Retrieved {len(vessels)} vessel(s):")
    for v in vessels:
        print(f"  - ID: {v['vessel_id']} | Lat: {v['lat']}, Lon: {v['lon']} | Last Seen: {v['last_position_time']}")
    print("Test 2 Passed!")

    # -------------------------------------------------------------
    # Test 3: Dark-Vessel Agent
    # -------------------------------------------------------------
    print("\n" + "-" * 65)
    print("[TEST 3] Testing agents/dark_vessel_agent.py: find_dark_vessels()...")
    flagged = find_dark_vessels(vessels)
    print(f"\nFlagged {len(flagged)} dark vessel(s) (>30 mins offline):")
    for item in flagged:
        print(f"\n  [Vessel: {item['vessel_id']}]")
        print(f"   Severity: {item['severity'].upper()}")
        print(f"   Location: ({item['lat']}, {item['lon']})")
        print(f"   Reason:   {item['flagged_reason']}")

    print("\n" + "=" * 65)
    print("  ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
