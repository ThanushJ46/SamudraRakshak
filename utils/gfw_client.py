"""
gfw_client.py
-------------
Gets ship positions inside a box on the map, using the
Global Fishing Watch (GFW) public API.

    from utils.gfw_client import get_vessel_positions

    area = {"min_lat": 12.0, "max_lat": 14.5, "min_lon": 79.5, "max_lon": 82.0}
    vessels = get_vessel_positions(area)

If the real API cannot be reached for ANY reason (no token, no internet,
unexpected response), we quietly switch to realistic made-up data instead of
crashing, and print a big warning so you always know which one you got.
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
DAYS_OF_HISTORY = 7
MAX_RESULTS = 50


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

    Never raises - falls back to sample data if anything goes wrong.
    """

    token = os.getenv("GFW_API_TOKEN")

    # No token? Don't even try the network, go straight to samples.
    if not token:
        print("\n[WARNING] GFW_API_TOKEN is not set - using SAMPLE vessel data.")
        print("          Get a free token at https://globalfishingwatch.org/our-apis/")
        print("          then add GFW_API_TOKEN=your_token to your .env file.\n")
        return _generate_sample_vessels(area)

    try:
        # ---- Build the request -------------------------------------------
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

        # ---- Make the call -----------------------------------------------
        response = requests.post(
            GFW_EVENTS_URL,
            headers=headers,
            params={"limit": MAX_RESULTS, "offset": 0},
            json=body,
            timeout=20,
        )
        response.raise_for_status()   # turns a 401/500/etc into an error we catch below

        # ---- Translate their format into OUR format ----------------------
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

        # An empty box is suspicious during a demo, so treat it as a failure
        # and show sample data rather than an empty map.
        if not vessels:
            raise ValueError("GFW returned no vessels for this area")

        print(f"[OK] Got {len(vessels)} REAL vessels from Global Fishing Watch.")
        return vessels

    except Exception as error:
        # Any problem at all (bad token, no internet, odd response shape)
        # lands here. We warn loudly, then carry on with sample data.
        print("\n[WARNING] Could not get real data from Global Fishing Watch.")
        print(f"          Reason: {error}")
        print("          Using SAMPLE vessel data instead.\n")
        return _generate_sample_vessels(area)


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


def _generate_sample_vessels(area: dict) -> list[dict]:
    """
    Make 10 believable fake vessels inside the given box.

    The leading underscore is a Python convention meaning "internal helper -
    other files shouldn't need to call this directly".
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
