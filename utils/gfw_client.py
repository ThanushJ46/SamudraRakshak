"""
Global Fishing Watch (GFW) Client for Maritime Guardian.
Fetches vessel positions within a given bounding box area using the GFW API,
with an automatic realistic fallback generator so teammates are never blocked.
"""

import os
from datetime import datetime, timezone, timedelta
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# =====================================================================
# SAMPLE DATA — replace once real API is confirmed working
# =====================================================================
def get_sample_vessel_positions(area: dict = None) -> list[dict]:
    """
    Generates realistic sample vessel position data.
    Useful for local testing, hackathon demos, or when GFW API credentials are not set.

    Parameters:
        area (dict, optional): Bounding box with keys 'min_lat', 'max_lat', 'min_lon', 'max_lon'.

    Returns:
        list[dict]: List of vessel records with vessel_id, lat, lon, and last_position_time.
    """
    now = datetime.now(timezone.utc)

    # Base coordinates (default to Bay of Bengal / Indian Ocean region if area not provided)
    base_lat = 13.0827
    base_lon = 80.2707

    if area and all(k in area for k in ("min_lat", "max_lat", "min_lon", "max_lon")):
        base_lat = (area["min_lat"] + area["max_lat"]) / 2
        base_lon = (area["min_lon"] + area["max_lon"]) / 2

    return [
        {
            "vessel_id": "VESSEL-IND-101",
            "lat": round(base_lat + 0.05, 4),
            "lon": round(base_lon + 0.12, 4),
            # Transmitted 8 minutes ago (active / normal)
            "last_position_time": (now - timedelta(minutes=8)).isoformat(),
        },
        {
            "vessel_id": "VESSEL-FOR-204",
            "lat": round(base_lat - 0.22, 4),
            "lon": round(base_lon - 0.18, 4),
            # Transmitted 48 minutes ago (dark > 30m, low/medium severity)
            "last_position_time": (now - timedelta(minutes=48)).isoformat(),
        },
        {
            "vessel_id": "VESSEL-UNK-309",
            "lat": round(base_lat + 0.35, 4),
            "lon": round(base_lon - 0.40, 4),
            # Transmitted 110 minutes ago (~1.8 hours, medium severity)
            "last_position_time": (now - timedelta(minutes=110)).isoformat(),
        },
        {
            "vessel_id": "VESSEL-GHOST-404",
            "lat": round(base_lat - 0.50, 4),
            "lon": round(base_lon + 0.65, 4),
            # Transmitted 260 minutes ago (~4.3 hours, high severity)
            "last_position_time": (now - timedelta(minutes=260)).isoformat(),
        },
        {
            "vessel_id": "VESSEL-IND-512",
            "lat": round(base_lat + 0.15, 4),
            "lon": round(base_lon - 0.08, 4),
            # Transmitted 15 minutes ago (active / normal)
            "last_position_time": (now - timedelta(minutes=15)).isoformat(),
        },
    ]


def get_vessel_positions(area: dict) -> list[dict]:
    """
    Fetches vessel positions in a bounding box area from the Global Fishing Watch API.
    If the API token is missing or the request fails, falls back gracefully to sample data.

    Parameters:
        area (dict): A dictionary describing the bounding box, e.g.:
                     {
                         "min_lat": 12.0,
                         "max_lat": 14.5,
                         "min_lon": 79.5,
                         "max_lon": 82.0
                     }

    Returns:
        list[dict]: List of vessel dictionaries, each containing:
                    - vessel_id (str)
                    - lat (float)
                    - lon (float)
                    - last_position_time (str, ISO 8601 UTC timestamp)
    """
    token = os.getenv("GFW_API_TOKEN")

    # If no token is configured, use realistic sample data immediately
    if not token:
        print("[gfw_client] No GFW_API_TOKEN found in .env. Using realistic sample data.")
        return get_sample_vessel_positions(area)

    url = "https://gateway.globalfishingwatch.org/v3/vessels/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Prepare bounding box query parameters
    params = {}
    if area:
        if "query" in area:
            params["query"] = area["query"]
        if all(k in area for k in ("min_lat", "max_lat", "min_lon", "max_lon")):
            params["min-lat"] = area["min_lat"]
            params["max-lat"] = area["max_lat"]
            params["min-lon"] = area["min_lon"]
            params["max-lon"] = area["max_lon"]

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        # If call succeeds and returns entries, parse into standardized list
        if response.status_code == 200:
            data = response.json()
            entries = data.get("entries", [])
            vessels = []
            for item in entries:
                vessel_id = item.get("id") or item.get("shipname") or "UNKNOWN_VESSEL"
                lat = item.get("lastLatitude") or item.get("lat", 0.0)
                lon = item.get("lastLongitude") or item.get("lon", 0.0)
                last_time = item.get("lastPositionTime") or datetime.now(timezone.utc).isoformat()

                vessels.append({
                    "vessel_id": vessel_id,
                    "lat": float(lat),
                    "lon": float(lon),
                    "last_position_time": last_time,
                })

            if vessels:
                return vessels

        # If API returned non-200 or empty results, fallback to sample data
        print(f"[gfw_client] GFW API returned status {response.status_code}. Using sample data.")
        return get_sample_vessel_positions(area)

    except Exception as err:
        print(f"[gfw_client] Error calling GFW API: {err}. Using sample data.")
        return get_sample_vessel_positions(area)
