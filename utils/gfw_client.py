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

        vessels.append({
            "vessel_id": str(vessel_id),
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


def generate_sample_vessels(area: dict) -> list[dict]:
    """
    Make 10 believable fake vessels inside the given box.

    This is a PUBLIC function: the orchestrator calls it on purpose when the
    user picks "Demo Sample Data" in the dashboard, and also as its fallback
    when the live GFW call fails.
    """

    now = datetime.now(timezone.utc)
    sample_vessels = []

    for vessel_id, minutes_ago in zip(SAMPLE_VESSEL_IDS, SAMPLE_MINUTES_AGO):
        # Pick a random spot inside the requested box.
        lat = random.uniform(area["min_lat"], area["max_lat"])
        lon = random.uniform(area["min_lon"], area["max_lon"])

        last_seen = now - timedelta(minutes=minutes_ago)

        sample_vessels.append({
            "vessel_id": vessel_id,
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            # Z on the end is the standard way of writing "this is UTC time".
            "last_position_time": last_seen.isoformat().replace("+00:00", "Z"),
        })

    return sample_vessels
