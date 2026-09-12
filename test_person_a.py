"""
test_person_a.py
----------------
A quick visual check that Person A's three functions work.

Run it from the project root:

    python test_person_a.py

It does NOT need any API keys to pass - without keys it falls back to sample
vessels and basic (non-AI) explanations, and says so clearly.
"""

import sys

# Ensure Windows terminal outputs Unicode cleanly without charmap encoding errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agents.dark_vessel_agent import find_dark_vessels
from utils.gfw_client import get_vessel_positions
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
# TEST 2: can we get vessel positions?
# ---------------------------------------------------------------------------
print_heading("TEST 2 - utils/gfw_client.py -> get_vessel_positions()")

print(f"Searching this box: {TEST_AREA}")
vessels = get_vessel_positions(TEST_AREA)

print(f"Got {len(vessels)} vessels back.\n")
print(f"{'VESSEL ID':<20} {'LAT':>10} {'LON':>12}   LAST SEEN")
print("-" * 70)
for vessel in vessels:
    print(f"{vessel['vessel_id']:<20} "
          f"{vessel['lat']:>10.4f} "
          f"{vessel['lon']:>12.4f}   "
          f"{vessel['last_position_time']}")

print("\nRESULT: PASS" if vessels else "\nRESULT: FAIL - empty list")


# ---------------------------------------------------------------------------
# TEST 3: can we flag the dark ones?
# ---------------------------------------------------------------------------
print_heading("TEST 3 - agents/dark_vessel_agent.py -> find_dark_vessels()")

print("Checking every vessel above for AIS silence...\n")
alerts = find_dark_vessels(vessels)

print(f"\nFlagged {len(alerts)} of {len(vessels)} vessels as dark.\n")

for number, alert in enumerate(alerts, start=1):
    print(f"--- ALERT {number} ---")
    print(f"  Vessel ID : {alert['vessel_id']}")
    print(f"  Position  : {alert['lat']:.4f}, {alert['lon']:.4f}")
    print(f"  Severity  : {alert['severity'].upper()}")
    print(f"  Reason    : {alert['flagged_reason']}")
    print()

# Check the output shape is exactly what teammates will be importing.
EXPECTED_KEYS = {"vessel_id", "lat", "lon", "flagged_reason", "severity"}
shape_is_correct = all(set(alert.keys()) == EXPECTED_KEYS for alert in alerts)

print("RESULT: PASS - output shape is correct."
      if shape_is_correct else
      "RESULT: FAIL - output shape does not match the agreed contract.")


# ---------------------------------------------------------------------------
print_heading("SUMMARY FOR TEAMMATES")
print("""
Import these three functions like this:

    from utils.llm_client         import ask_ai
    from utils.gfw_client         import get_vessel_positions
    from agents.dark_vessel_agent import find_dark_vessels

Shapes you can rely on:

  get_vessel_positions(area) takes:
      {"min_lat": float, "max_lat": float, "min_lon": float, "max_lon": float}
  ...and returns a list of:
      {"vessel_id": str, "lat": float, "lon": float, "last_position_time": str}

  find_dark_vessels(vessel_list) takes that same list,
  ...and returns a list of:
      {"vessel_id": str, "lat": float, "lon": float,
       "flagged_reason": str, "severity": "low" | "medium" | "high"}
""")
