"""
gfw_client.py
-------------
Gets ship positions inside a box on the map, using the
Global Fishing Watch (GFW) public API.

    from utils.gfw_client import get_vessel_positions

    area = {"min_lat": 12.0, "max_lat": 14.5, "min_lon": 79.5, "max_lon": 82.0}
    vessels = get_vessel_positions(area)

This file gives you TWO functions, and the caller picks which one:

  get_vessel_positions(area)   -> the REAL Global Fishing Watch data.
                                  Raises an exception if it cannot deliver.
  generate_sample_vessels(area) -> realistic made-up data for demos.

There is deliberately NO hidden fallback between them. The orchestrator
decides what to do when the live call fails, so the dashboard can always
tell the user which data they are actually looking at.
"""

import math
import os
import random
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import requests

load_dotenv()

# GFW's events endpoint. We ask it for recent fishing activity inside our box,
# and use each activity record as "this vessel was here at this time".
# (GFW does not hand out raw live AIS pings publicly, so activity events are
# the closest public equivalent - and they carry exactly what we need:
# a vessel id, a lat/lon, and a timestamp.)
GFW_EVENTS_URL = "https://gateway.api.globalfishingwatch.org/v3/events"

# ---------------------------------------------------------------------------
# APPROXIMATE, for demo visualization only - not surveyed/legal maritime
# boundary coordinates. Do NOT use this for navigation or for any real
# enforcement decision. It exists so the dashboard has a plausible "sensitive
# line" to measure vessels against during the demo, and runs through the Gulf
# of Mannar area we scan by default.
# ---------------------------------------------------------------------------
ILLUSTRATIVE_BOUNDARY_LINE = [
    {"lat": 9.0, "lon": 79.6},
    {"lat": 10.5, "lon": 80.0},
]


# How far back to look for activity, and how many vessels to ask for.
# MAX_RESULTS is kept deliberately low: every medium/high vessel costs one AI
# call, so a bigger number directly slows the dashboard down in front of an
# audience. 20 is enough to look busy on a map and still respond quickly.
DAYS_OF_HISTORY = 7
MAX_RESULTS = 20


def get_vessel_positions(area: dict) -> list[dict]:
    """
    Return the vessels seen inside a bounding box.

    Input:
        area -> {"min_lat": float, "max_lat": float,
                 "min_lon": float, "max_lon": float}

    Output: a list of dicts, each one shaped exactly like:
        {
            "vessel_id": "abc123",
            "lat": 13.14,
            "lon": 80.31,
            "vessel_name": "NG-21 MARIA-CHRIS",            # or None
            "flag": "IND",                                 # ISO-3, or None
            "last_position_time": "2026-09-12T08:30:00Z"   # ISO datetime string
        }

    Raises an exception if the token is missing, the network call fails, or
    the area comes back empty. It does NOT fall back to sample data - the
    caller decides that, so a failure is never hidden from the user.
    """

    token = os.getenv("GFW_API_TOKEN")

    # No token means we cannot even try. Raise so the caller (the orchestrator)
    # can decide whether to show demo data or an error - that decision is no
    # longer made secretly down here.
    if not token:
        raise ValueError(
            """GFW_API_TOKEN is not set.
Fix: open the .env file in the project root and add the line:
    GFW_API_TOKEN=your_token_here
Get a free token at https://globalfishingwatch.org/our-apis/"""
        )

    # ---- Build the request -----------------------------------------------
    # The API wants a date range and a polygon (our box drawn as 5 corners,
    # ending back where it started).
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=DAYS_OF_HISTORY)

    box_as_polygon = {
        "type": "Polygon",
        "coordinates": [[
            [area["min_lon"], area["min_lat"]],
            [area["max_lon"], area["min_lat"]],
            [area["max_lon"], area["max_lat"]],
            [area["min_lon"], area["max_lat"]],
            [area["min_lon"], area["min_lat"]],
        ]],
    }

    body = {
        "datasets": ["public-global-fishing-events:latest"],
        "startDate": str(start_date),
        "endDate": str(today),
        "geometry": box_as_polygon,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # ---- Make the call ---------------------------------------------------
    response = requests.post(
        GFW_EVENTS_URL,
        headers=headers,
        params={"limit": MAX_RESULTS, "offset": 0},
        json=body,
        timeout=20,
    )
    response.raise_for_status()   # turns a 401/500/etc into an exception

    # ---- Translate their format into OUR format --------------------------
    entries = response.json().get("entries", [])
    vessels = []

    for entry in entries:
        position = entry.get("position") or {}
        vessel_info = entry.get("vessel") or {}

        lat = position.get("lat")
        lon = position.get("lon")
        vessel_id = vessel_info.get("id") or entry.get("id")

        # Skip any record that is missing the bits we need.
        if lat is None or lon is None or not vessel_id:
            continue

        # "end" is when the vessel was last seen doing this activity.
        last_seen = entry.get("end") or entry.get("start")
        if not last_seen:
            continue

        # GFW tells us the vessel's flag state (an ISO-3 country code like
        # "IND" or "DEU") and its real name. We keep BOTH: the flag is what
        # the classifier uses to tell our own boats from foreign ones, and
        # the name is far more use on screen than a hex id.
        flag = (vessel_info.get("flag") or "").strip().upper() or None
        vessel_name = (vessel_info.get("name") or "").strip() or None

        vessels.append({
            "vessel_id": str(vessel_id),
            "vessel_name": vessel_name,
            "flag": flag,
            "lat": float(lat),
            "lon": float(lon),
            "last_position_time": str(last_seen),
        })

    # GFW can report several activity events for the SAME vessel, which
    # would put the same ship on the map several times. Keep only each
    # vessel's most recent sighting.
    vessels = _keep_latest_per_vessel(vessels)

    # An empty box is not useful to the dashboard, so treat it as a failure
    # and let the caller fall back to demo data.
    if not vessels:
        raise ValueError("GFW returned no vessels for this area")

    print(f"[OK] Got {len(vessels)} REAL vessels from Global Fishing Watch.")
    return vessels


def _keep_latest_per_vessel(vessels: list[dict]) -> list[dict]:
    """
    Collapse repeated sightings so each vessel appears exactly once.

    GFW returns one record per fishing activity, so a boat that fished four
    times this week comes back four times. The dashboard only wants to draw
    each boat once, at the last place we saw it.
    """
    latest_by_vessel = {}

    for vessel in vessels:
        vessel_id = vessel["vessel_id"]
        already_kept = latest_by_vessel.get(vessel_id)

        # Keep this record if it is the first we've seen for this vessel,
        # or if its timestamp is newer than the one we already kept.
        if already_kept is None or vessel["last_position_time"] > already_kept["last_position_time"]:
            latest_by_vessel[vessel_id] = vessel

    return list(latest_by_vessel.values())


# Names for the made-up vessels, so the demo map reads like a real coastline
# rather than "VESSEL-1, VESSEL-2".
SAMPLE_VESSEL_IDS = [
    "IND-TN-1042",     # local trawler
    "IND-TN-1197",
    "IND-AP-2310",
    "FOR-LKA-4471",    # foreign-flagged
    "FOR-IDN-5528",
    "UNK-GHOST-6603",  # unidentified
    "IND-TN-1355",
    "FOR-THA-7719",
    "UNK-GHOST-8840",
    "IND-KL-3062",
]

# How many minutes ago each of the vessels above last reported its position.
# 0-30 mins = healthy, the rest are increasingly "dark". We deliberately cover
# every severity band so the dark-vessel agent always has something to find.
SAMPLE_MINUTES_AGO = [4, 12, 21, 47, 68, 105, 168, 295, 640, 26]


# Four of the ten sample vessels are pinned to deliberate positions relative
# to ILLUSTRATIVE_BOUNDARY_LINE, so that a demo scan always produces all four
# classification categories instead of relying on random luck.
#
# Each entry is: vessel_id -> (km from the boundary, which side, how far along)
#
# Only IND-TN-1355 is both Indian-flagged AND silent for long enough to reach
# the agent (168 minutes) - the other IND- boats report every few minutes, so
# they never get flagged. That makes it the only vessel that can produce a
# "border_safety_alert", which is why it is pinned close to the line.
PINNED_SAMPLE_POSITIONS = {
    "IND-TN-1355":    (6.0,  "india_side", 0.50),   # -> border_safety_alert
    "FOR-LKA-4471":   (35.0, "india_side", 0.60),   # -> foreign_intrusion
    "UNK-GHOST-6603": (9.0,  "other_side", 0.40),   # -> unidentified_near_zone
    "UNK-GHOST-8840": (55.0, "other_side", 0.35),   # -> routine_gap
}


def _point_offset_from_boundary(km_from_line: float, side: str, along_fraction: float) -> dict:
    """
    Work out a lat/lon that sits a given distance to one side of the
    illustrative boundary line.

    Inputs:
        km_from_line   -> how far from the line to place the point
        side           -> "india_side" or "other_side"
        along_fraction -> 0.0 is the line's southern end, 1.0 the northern end,
                          0.5 the middle

    Output: {"lat": float, "lon": float}

    This is only used to place demo vessels convincingly. We convert to flat
    kilometres, step sideways from the line, then convert back to degrees.
    """
    line_start = ILLUSTRATIVE_BOUNDARY_LINE[0]
    line_end = ILLUSTRATIVE_BOUNDARY_LINE[1]

    reference_latitude = (line_start["lat"] + line_end["lat"]) / 2
    km_per_degree_longitude = 111.32 * math.cos(math.radians(reference_latitude))
    km_per_degree_latitude = 110.57

    # Both ends of the line, in kilometres.
    start_x = line_start["lon"] * km_per_degree_longitude
    start_y = line_start["lat"] * km_per_degree_latitude
    end_x = line_end["lon"] * km_per_degree_longitude
    end_y = line_end["lat"] * km_per_degree_latitude

    # Walk along the line to our chosen fraction.
    base_x = start_x + along_fraction * (end_x - start_x)
    base_y = start_y + along_fraction * (end_y - start_y)

    # The line's direction, as a unit vector.
    line_dx = end_x - start_x
    line_dy = end_y - start_y
    line_length = math.sqrt(line_dx ** 2 + line_dy ** 2)
    unit_dx = line_dx / line_length
    unit_dy = line_dy / line_length

    # Turning the direction 90 degrees gives (-dy, dx), which for this
    # boundary points west - the Indian side. Flip it for the other side.
    perpendicular_x = -unit_dy
    perpendicular_y = unit_dx
    if side == "other_side":
        perpendicular_x = -perpendicular_x
        perpendicular_y = -perpendicular_y

    offset_x = base_x + perpendicular_x * km_from_line
    offset_y = base_y + perpendicular_y * km_from_line

    # Back into degrees.
    return {
        "lat": round(offset_y / km_per_degree_latitude, 5),
        "lon": round(offset_x / km_per_degree_longitude, 5),
    }


def _boundary_overlaps_area(area: dict) -> bool:
    """
    Is the illustrative boundary line anywhere near the area being scanned?

    If someone scans the North Sea, the Gulf of Mannar boundary is thousands of
    kilometres away, and pinning vessels to it would drop markers outside the
    box they asked for. In that case we just place everything randomly.
    """
    line_lats = [point["lat"] for point in ILLUSTRATIVE_BOUNDARY_LINE]
    line_lons = [point["lon"] for point in ILLUSTRATIVE_BOUNDARY_LINE]

    latitudes_overlap = min(line_lats) <= area["max_lat"] and max(line_lats) >= area["min_lat"]
    longitudes_overlap = min(line_lons) <= area["max_lon"] and max(line_lons) >= area["min_lon"]

    return latitudes_overlap and longitudes_overlap


def _flag_from_sample_id(vessel_id: str):
    """
    Work out a flag state from one of our demo vessel ids.

    Our sample ids encode the flag in their prefix, so we translate them into
    the same ISO-3 country codes the real GFW feed uses. That way demo data
    and live data are classified by exactly the same rule, instead of the
    classifier needing a special case for each.

        "IND-TN-1042"    -> "IND"   (Indian)
        "FOR-LKA-4471"   -> "LKA"   (Sri Lankan)
        "UNK-GHOST-6603" -> None    (no flag = unidentified)
    """
    parts = vessel_id.split("-")

    if parts[0] == "IND":
        return "IND"

    # "FOR-LKA-4471" carries the real country code in the middle.
    if parts[0] == "FOR" and len(parts) > 1:
        return parts[1]

    # Unidentified vessels genuinely have no flag, which is the whole point.
    return None


def generate_sample_vessels(area: dict) -> list[dict]:
    """
    Make 10 believable fake vessels inside the given box.

    This is a PUBLIC function: the orchestrator calls it on purpose when the
    user picks "Demo Sample Data" in the dashboard, and also as its fallback
    when the live GFW call fails.

    Four of the ten are placed at deliberate distances from
    ILLUSTRATIVE_BOUNDARY_LINE (see PINNED_SAMPLE_POSITIONS) so every
    classification category shows up in a demo. The other six are scattered
    randomly. If the boundary is nowhere near the requested area, all ten are
    scattered randomly instead.
    """

    now = datetime.now(timezone.utc)
    sample_vessels = []

    # Only pin vessels to the boundary if the boundary is actually in view.
    use_pinned_positions = _boundary_overlaps_area(area)

    for vessel_id, minutes_ago in zip(SAMPLE_VESSEL_IDS, SAMPLE_MINUTES_AGO):
        pinned = PINNED_SAMPLE_POSITIONS.get(vessel_id)

        if use_pinned_positions and pinned is not None:
            # This vessel has a job to do in the demo - put it exactly where
            # it needs to be relative to the boundary.
            km_from_line, side, along_fraction = pinned
            position = _point_offset_from_boundary(km_from_line, side, along_fraction)
            lat = position["lat"]
            lon = position["lon"]
        else:
            # Pick a random spot inside the requested box.
            lat = round(random.uniform(area["min_lat"], area["max_lat"]), 5)
            lon = round(random.uniform(area["min_lon"], area["max_lon"]), 5)

        last_seen = now - timedelta(minutes=minutes_ago)

        sample_vessels.append({
            "vessel_id": vessel_id,
            # For sample data the id IS the readable name.
            "vessel_name": vessel_id,
            "flag": _flag_from_sample_id(vessel_id),
            "lat": lat,
            "lon": lon,
            # Z on the end is the standard way of writing "this is UTC time".
            "last_position_time": last_seen.isoformat().replace("+00:00", "Z"),
        })

    return sample_vessels
