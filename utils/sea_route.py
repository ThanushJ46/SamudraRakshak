"""
sea_route.py
------------
Keeps ship routes in the water.

The route agent works out a great-circle line between two points and nudges
it sideways to dodge rough weather. What it does NOT know is where the land
is - so asked for Rameswaram to Kochi it draws a straight line across Tamil
Nadu and Kerala, which is obviously not sailable.

This file fixes that WITHOUT changing the route agent. It holds a short chain
of offshore waypoints running around the southern tip of India, and works out
which of them a voyage has to pass through. The caller then asks the route
agent to optimise each leg separately and joins the legs together, so every
segment is short enough to stay at sea and the weather optimisation still
happens leg by leg.

    from utils.sea_route import plan_sea_route
    points = plan_sea_route("Rameswaram", "Kochi", PORT_PRESETS)

---------------------------------------------------------------------------
APPROXIMATE, for demo visualization only - these are eyeballed offshore
points, NOT surveyed shipping lanes, charted channels, or navigational
waypoints. Do not use for navigation.
---------------------------------------------------------------------------
"""

# The corridor, ordered from the west coast, around the southern tip, and up
# the east coast. Every entry is a point in open water.
#
# Index:  0            1              2             3          4          5        6
#       Kochi -> Kanyakumari -> Tuticorin -> Gulf of Mannar -> Rameswaram -> Palk -> Chennai
SEA_CORRIDOR = [
    {"name": "Off Kochi",        "lat": 9.90, "lon": 75.90},
    {"name": "Off Kanyakumari",  "lat": 7.70, "lon": 77.20},
    {"name": "Off Tuticorin",    "lat": 8.45, "lon": 78.45},
    {"name": "Gulf of Mannar",   "lat": 8.75, "lon": 79.00},
    {"name": "Off Rameswaram",   "lat": 9.10, "lon": 79.35},
    {"name": "Palk Bay",         "lat": 10.30, "lon": 79.95},
    {"name": "Off Chennai",      "lat": 13.00, "lon": 80.50},
]

# Where each port joins the corridor. A voyage walks the corridor between the
# two ports' entry points, so it always goes the long way round the coast
# instead of straight over it.
#
# Colombo sits at the Gulf of Mannar entry (index 3) because approaching it
# from anywhere on our coast means coming down through the Gulf of Mannar
# first, on the western side of Sri Lanka.
PORT_CORRIDOR_INDEX = {
    "Kochi": 0,
    "Tuticorin (Thoothukudi)": 2,
    "Colombo": 3,
    "Rameswaram": 4,
    "Mandapam": 4,
    "Chennai": 6,
}


def plan_sea_route(start_port_name: str, end_port_name: str, port_presets: dict) -> list:
    """
    Work out the full list of points a voyage should sail through.

    Inputs:
        start_port_name -> a key of port_presets, e.g. "Rameswaram"
        end_port_name   -> a key of port_presets, e.g. "Kochi"
        port_presets    -> {"Rameswaram": {"lat":..., "lon":...}, ...}

    Output: an ordered list of {"lat", "lon", "name"} dicts, beginning at the
            start port and ending at the destination, with any offshore
            corridor waypoints needed in between.

    The caller is expected to run the route agent on each consecutive PAIR of
    these points and join the results, rather than on the whole voyage at
    once - that is what keeps the path in the water.
    """
    start_port = port_presets[start_port_name]
    end_port = port_presets[end_port_name]

    route_points = [
        {"lat": start_port["lat"], "lon": start_port["lon"], "name": start_port_name}
    ]

    start_index = PORT_CORRIDOR_INDEX.get(start_port_name)
    end_index = PORT_CORRIDOR_INDEX.get(end_port_name)

    # If we don't know where one of the ports joins the corridor, fall back to
    # sailing direct. It may cross land, but it is better than crashing - and
    # every port in PORT_PRESETS is listed above, so this is just a guard.
    if start_index is not None and end_index is not None:
        if start_index <= end_index:
            corridor_slice = SEA_CORRIDOR[start_index:end_index + 1]
        else:
            # Travelling the other way, so walk the corridor backwards.
            corridor_slice = SEA_CORRIDOR[end_index:start_index + 1][::-1]

        for waypoint in corridor_slice:
            route_points.append({
                "lat": waypoint["lat"],
                "lon": waypoint["lon"],
                "name": waypoint["name"],
            })

    route_points.append(
        {"lat": end_port["lat"], "lon": end_port["lon"], "name": end_port_name}
    )

    # Drop any point that repeats the one before it. This happens when a port
    # sits effectively on its own corridor entry (Rameswaram and Mandapam
    # share one), and a zero-length leg would just confuse the fuel maths.
    cleaned_points = [route_points[0]]
    for point in route_points[1:]:
        previous = cleaned_points[-1]
        same_place = (
            abs(point["lat"] - previous["lat"]) < 0.01
            and abs(point["lon"] - previous["lon"]) < 0.01
        )
        if not same_place:
            cleaned_points.append(point)

    return cleaned_points
