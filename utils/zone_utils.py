"""
zone_utils.py
-------------
Small geometry helpers for deciding WHERE a vessel is relative to a sensitive
maritime boundary, and what that means.

Why this exists: a vessel that stops broadcasting in the middle of open water
is usually just a flaky radio. The same silence right next to a sensitive
boundary means something quite different. These three functions let the
dark-vessel agent tell those two situations apart instead of treating every
silent boat as equally suspicious.

    from utils.zone_utils import (
        distance_point_to_line_km,
        which_side,
        classify_vessel,
        vessel_origin,
    )
"""

import math

# Roughly how many kilometres one degree of latitude covers. Latitude lines are
# evenly spaced, so this is a constant.
KM_PER_DEGREE_LATITUDE = 110.57

# One degree of LONGITUDE is widest at the equator and shrinks towards the
# poles, so we have to scale it by the cosine of the latitude we are at.
KM_PER_DEGREE_LONGITUDE_AT_EQUATOR = 111.32


def _to_km_xy(point: dict, reference_latitude: float) -> tuple:
    """
    Convert a {"lat", "lon"} point into flat (x, y) kilometres.

    x = kilometres east, y = kilometres north.

    We do this so we can use ordinary flat geometry (which everyone can read)
    instead of spherical trigonometry. Over an area a couple of hundred
    kilometres across, the error is small enough not to matter for a
    "how close is this boat to the line" judgement.
    """
    km_per_degree_longitude = (
        KM_PER_DEGREE_LONGITUDE_AT_EQUATOR * math.cos(math.radians(reference_latitude))
    )

    x_km = point["lon"] * km_per_degree_longitude
    y_km = point["lat"] * KM_PER_DEGREE_LATITUDE
    return (x_km, y_km)


def distance_point_to_line_km(point: dict, line: list) -> float:
    """
    How far a point is from a boundary line, in kilometres.

    Inputs:
        point -> {"lat": float, "lon": float}
        line  -> [{"lat": float, "lon": float}, {"lat": float, "lon": float}]
                 the two ends of the boundary

    Output: the perpendicular distance in km (always positive).

    Note: this measures against the infinite straight line running through
    those two points, not just the segment between them. That is deliberate -
    a vessel sitting off the northern end of the boundary should still be
    reported as "near the line", not as "far from the line's endpoint".
    """
    line_start = line[0]
    line_end = line[1]

    # Use the middle of the boundary as the latitude for our km conversion,
    # so both ends are scaled the same way.
    reference_latitude = (line_start["lat"] + line_end["lat"]) / 2

    point_x, point_y = _to_km_xy(point, reference_latitude)
    start_x, start_y = _to_km_xy(line_start, reference_latitude)
    end_x, end_y = _to_km_xy(line_end, reference_latitude)

    # The direction the boundary runs in.
    line_dx = end_x - start_x
    line_dy = end_y - start_y

    line_length_km = math.sqrt(line_dx ** 2 + line_dy ** 2)

    # Guard against a "line" whose two ends are the same point, which would
    # mean dividing by zero. Fall back to plain point-to-point distance.
    if line_length_km == 0:
        return math.sqrt((point_x - start_x) ** 2 + (point_y - start_y) ** 2)

    # Standard 2D point-to-line distance: the cross product of the line's
    # direction with the start-to-point vector, divided by the line's length.
    cross_product = line_dx * (point_y - start_y) - line_dy * (point_x - start_x)

    return abs(cross_product) / line_length_km


def which_side(point: dict, line: list) -> str:
    """
    Which side of the boundary a point sits on.

    Inputs:
        point -> {"lat": float, "lon": float}
        line  -> the two ends of the boundary

    Output: "india_side" or "other_side".

    How it works: we take the cross product of the boundary's direction with
    the vector from the boundary's start to our point. The SIGN of that number
    tells us which side we are on - positive on one side, negative on the
    other. Which sign means which side depends on the order the boundary's two
    points are written in, so this is calibrated for the boundary defined in
    gfw_client.py, where a positive result is the western (Indian) side.
    """
    line_start = line[0]
    line_end = line[1]

    # Working directly in degrees is fine here, because we only care about the
    # SIGN of the result, not its size. Scaling both terms would not flip it.
    line_dlon = line_end["lon"] - line_start["lon"]
    line_dlat = line_end["lat"] - line_start["lat"]

    point_dlon = point["lon"] - line_start["lon"]
    point_dlat = point["lat"] - line_start["lat"]

    cross_product = (line_dlon * point_dlat) - (line_dlat * point_dlon)

    # Positive means west of the boundary, which for our demo line is the
    # Indian side. Exactly zero (sitting on the line) counts as our side too.
    if cross_product >= 0:
        return "india_side"
    return "other_side"


# How close a vessel has to be to the boundary for us to care, per category.
BORDER_SAFETY_DISTANCE_KM = 10      # our own boats drifting towards the line
UNIDENTIFIED_DISTANCE_KM = 15       # unknown boats get a wider net

# Past this distance the boundary simply is not relevant to the vessel, and no
# category based on it means anything.
#
# This guard matters because the boundary is an INFINITE line (see
# distance_point_to_line_km). Without it, every foreign boat on the western
# side of that line counts as being "on our side" - so scanning the North Sea
# flagged 17 Belgian and Danish trawlers as foreign intrusions from 9,000 km
# away. Anything this far out is a routine gap, whatever its flag.
MAX_RELEVANT_DISTANCE_KM = 200

# The ISO-3 country code that means "one of ours". Global Fishing Watch reports
# flag states in this format ("IND", "LKA", "DEU"), and our sample data is
# generated to match, so one rule covers both.
OUR_FLAG = "IND"


def vessel_origin(vessel: dict) -> str:
    """
    Decide whether a vessel is ours, foreign, or unidentified.

    Output: "ours" | "foreign" | "unknown"

    We prefer the vessel's FLAG, because that is what the real Global Fishing
    Watch feed gives us. Live GFW ids are meaningless hex strings like
    "054b3f2fd-d468-e27f-6ba5-03b9b6fefb11", so a rule based on the id alone
    would classify every real vessel as unknown - which made the whole
    classification layer silently do nothing on live data.

    The id-prefix check is kept underneath as a fallback, so hand-written or
    older sample data with no flag field still works.
    """
    flag = (vessel.get("flag") or "").strip().upper()

    if flag:
        return "ours" if flag == OUR_FLAG else "foreign"

    # No flag on this record - fall back to reading our demo id prefixes.
    vessel_id = vessel.get("vessel_id", "")

    if vessel_id.startswith("IND-"):
        return "ours"
    if vessel_id.startswith("FOR-"):
        return "foreign"

    # Includes "UNK-" and anything we simply do not recognise. Treating an
    # unrecognised vessel as unidentified is the safe way round.
    return "unknown"


def classify_vessel(vessel: dict, distance_km: float, side: str) -> str:
    """
    Decide what kind of situation this dark vessel actually is.

    Inputs:
        vessel      -> a vessel dict; we look at its "flag" (preferred) or
                       its "vessel_id" prefix
        distance_km -> from distance_point_to_line_km()
        side        -> from which_side()

    Output: exactly one of these four strings:

        "foreign_intrusion"      A foreign-flagged boat on our side of the
                                 boundary. Distance does not matter - if it is
                                 on our side at all, that is the story.

        "border_safety_alert"    One of our own boats within 10 km of the
                                 boundary. This is NOT an accusation; it is a
                                 heads-up that a local fisherman may be about
                                 to cross and get into trouble.

        "unidentified_near_zone" An unidentified boat (no flag) within 15 km
                                 of the boundary, either side. We do not know
                                 whose it is, so proximity alone is worth a
                                 look.

        "routine_gap"            Everything else, including anything more
                                 than MAX_RELEVANT_DISTANCE_KM from the
                                 boundary. Almost always just a radio dropout
                                 in open water, not worth waking anybody up
                                 for.
    """
    # Too far away for the boundary to mean anything. Checked FIRST, so a
    # vessel on the other side of the planet can never be an "intrusion".
    if distance_km > MAX_RELEVANT_DISTANCE_KM:
        return "routine_gap"

    origin = vessel_origin(vessel)

    # Foreign boat on our side of the line - the most serious case.
    if origin == "foreign" and side == "india_side":
        return "foreign_intrusion"

    # One of ours, close to the line - warn them, don't accuse them.
    if origin == "ours" and distance_km <= BORDER_SAFETY_DISTANCE_KM:
        return "border_safety_alert"

    # Unknown boat hanging around the boundary, whichever side it is on.
    if origin == "unknown" and distance_km <= UNIDENTIFIED_DISTANCE_KM:
        return "unidentified_near_zone"

    # Nothing special about where this one is.
    return "routine_gap"
