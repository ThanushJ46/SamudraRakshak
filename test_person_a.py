"""
test_person_a.py
----------------
A quick visual check that Person A's foundation layer works.

Run it from the project root:

    python test_person_a.py

It does NOT need any API keys to pass. Without keys, the live Global Fishing
Watch call fails (which is now correct behaviour - it raises instead of hiding
it), the script falls back to sample vessels, and the AI explanations fall back
to plain templated sentences. Every step says which one happened.
"""

import sys

# Windows terminals default to a legacy codepage that cannot print some of the
# characters the AI likes to use (fancy dashes, narrow spaces). Switch this
# script's output to UTF-8 so printing an alert can never crash the test.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.dark_vessel_agent import find_dark_vessels
from utils.gfw_client import generate_sample_vessels, get_vessel_positions
from utils.llm_client import ask_ai


def print_heading(text: str) -> None:
    """Print a clearly separated section title."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


# A box of ocean off the Tamil Nadu coast, around Chennai.
# Swap these four numbers to look at a different part of the world.
TEST_AREA = {
    "min_lat": 12.0,
    "max_lat": 14.5,
    "min_lon": 79.5,
    "max_lon": 82.0,
}


# ---------------------------------------------------------------------------
# TEST 1: can we talk to the AI?
# ---------------------------------------------------------------------------
print_heading("TEST 1 - utils/llm_client.py -> ask_ai()")

try:
    reply = ask_ai("Say the words 'Samudra Rakshak is online' and nothing else.")
    print("AI replied:", reply)
    print("RESULT: PASS - Groq is working.")
except Exception as error:
    print(f"AI unavailable: {error}")
    print("RESULT: SKIPPED - add GROQ_API_KEY to .env to enable AI explanations.")


# ---------------------------------------------------------------------------
# TEST 2: can we get vessel positions? (both functions)
# ---------------------------------------------------------------------------
print_heading("TEST 2 - utils/gfw_client.py -> both functions")

print(f"Searching this box: {TEST_AREA}")

# --- 2a: the sample generator. Must always work, no keys needed. ---
print("\n2a) generate_sample_vessels() ...")
sample_vessels = generate_sample_vessels(TEST_AREA)
print(f"    got {len(sample_vessels)} sample vessels")
print("    RESULT: PASS" if sample_vessels else "    RESULT: FAIL - empty list")

# --- 2b: the live feed. Allowed to fail, and it now RAISES rather than ---
# --- hiding the failure, so we catch it here on purpose.               ---
print("\n2b) get_vessel_positions() ...")
try:
    vessels = get_vessel_positions(TEST_AREA)
    print(f"    got {len(vessels)} REAL vessels")
    print("    RESULT: PASS - live Global Fishing Watch feed works.")
except Exception as error:
    print(f"    live call failed: {type(error).__name__}: {error}")
    print("    RESULT: SKIPPED - raising here is correct behaviour, not a bug.")
    print("    Using sample vessels for TEST 3 instead.")
    vessels = sample_vessels

print(f"\n{'VESSEL ID':<40} {'LAT':>9} {'LON':>10}   LAST SEEN")
print("-" * 92)
for vessel in vessels:
    print(f"{vessel['vessel_id']:<40} "
          f"{vessel['lat']:>9.4f} "
          f"{vessel['lon']:>10.4f}   "
          f"{vessel['last_position_time']}")


# ---------------------------------------------------------------------------
# TEST 3: can we flag the dark ones?
# ---------------------------------------------------------------------------
print_heading("TEST 3 - agents/dark_vessel_agent.py -> find_dark_vessels()")

print("Checking every vessel above for AIS silence...")
print("(low severity uses a templated sentence - no AI call - to stay fast)\n")

alerts = find_dark_vessels(vessels)

print(f"\nFlagged {len(alerts)} of {len(vessels)} vessels as dark.\n")

for number, alert in enumerate(alerts, start=1):
    print(f"--- ALERT {number} ---")
    print(f"  Vessel ID : {alert['vessel_id']}")
    print(f"  Position  : {alert['lat']:.4f}, {alert['lon']:.4f}")
    print(f"  Severity  : {alert['severity'].upper()}")
    print(f"  Category  : {alert['category']}  "
          f"({alert['distance_to_border_km']} km from boundary)")
    print(f"  Flag      : {alert['flag'] or 'unknown'}")
    print(f"  Reason    : {alert['flagged_reason']}")
    print()

# Check the output shape is exactly what teammates will be importing.
# "category" and "distance_to_border_km" came with the boundary-aware
# classification layer; "vessel_name" and "flag" let the dashboard show a
# readable name instead of a hex id. All four are part of the contract now.
EXPECTED_KEYS = {
    "vessel_id",
    "vessel_name",
    "flag",
    "lat",
    "lon",
    "flagged_reason",
    "severity",
    "category",
    "distance_to_border_km",
}
shape_is_correct = all(set(alert.keys()) == EXPECTED_KEYS for alert in alerts)

if not shape_is_correct and alerts:
    # Say exactly what is off, instead of just "FAIL".
    actual_keys = set(alerts[0].keys())
    print(f"  unexpected extra keys: {sorted(actual_keys - EXPECTED_KEYS)}")
    print(f"  missing keys:          {sorted(EXPECTED_KEYS - actual_keys)}")

print("RESULT: PASS - output shape is correct."
      if shape_is_correct else
      "RESULT: FAIL - output shape does not match the agreed contract.")


# ---------------------------------------------------------------------------
print_heading("SUMMARY FOR TEAMMATES")
print("""
Import these functions like this:

    from utils.llm_client         import ask_ai
    from utils.gfw_client         import get_vessel_positions, generate_sample_vessels
    from agents.dark_vessel_agent import find_dark_vessels

Shapes you can rely on:

  get_vessel_positions(area)    -> REAL data. RAISES if it cannot deliver.
  generate_sample_vessels(area) -> demo data. Never raises.
  Both take:
      {"min_lat": float, "max_lat": float, "min_lon": float, "max_lon": float}
  ...and return a list of:
      {"vessel_id": str, "vessel_name": str|None, "flag": str|None,
       "lat": float, "lon": float, "last_position_time": str}

  find_dark_vessels(vessel_list) takes that same list,
  ...and returns a list of:
      {"vessel_id": str, "vessel_name": str|None, "flag": str|None,
       "lat": float, "lon": float,
       "flagged_reason": str, "severity": "low" | "medium" | "high",
       "category": "foreign_intrusion" | "border_safety_alert"
                 | "unidentified_near_zone" | "routine_gap",
       "distance_to_border_km": float}

  Vessels classified "routine_gap" are capped at "low" severity and never
  cost an AI call, however long they have been silent.

  The orchestrator's check_dark_vessels(area, use_demo_data) wraps all of the
  above and returns:
      {"vessels": [...each with an extra "is_new": bool...],
       "data_source": "live" | "demo" | "demo (live call failed)"}
""")
