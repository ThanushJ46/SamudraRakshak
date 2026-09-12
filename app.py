"""
app.py
------
Samudra Rakshak - Streamlit dashboard for a maritime authority.

Three sections, in order:
  1. Dark Vessel Monitor  - silent vessels, classified by where they are
                            relative to an illustrative maritime boundary
  2. Route Optimizer      - fuel-efficient path between two ports
  3. Debris Cleanup       - collection round for a cleanup boat

UI/UX pass: page theme colors live in .streamlit/config.toml. The CSS block
below defines small reusable classes (badge-pill, stat-card, header-banner)
so anyone adding a new section can reuse the same look instead of inventing
new styles - just wrap your HTML in these class names.

Run it with:
    streamlit run app.py
"""

import folium
import streamlit as st
from streamlit_folium import st_folium

from agents.orchestrator import (
    DEFAULT_AREA,
    check_dark_vessels,
    get_cleanup_plan,
    get_optimized_route,
)
from utils.gfw_client import ILLUSTRATIVE_BOUNDARY_LINE
from utils.sea_route import plan_sea_route

st.set_page_config(page_title="Samudra Rakshak", page_icon="🌊", layout="wide")

# ===========================================================================
# SHARED STYLE - reusable classes for this section and any section added
# later (Route Optimizer, Debris Cleanup). Keep using these classes rather
# than inventing new inline styles, so the whole dashboard reads as one
# product instead of three different screens bolted together.
# ===========================================================================
st.markdown(
    """
    <style>
    /* Header banner */
    .sr-header {
        background: linear-gradient(135deg, #0c4a6e 0%, #0369a1 60%, #0891b2 100%);
        padding: 28px 32px;
        border-radius: 14px;
        margin-bottom: 22px;
        box-shadow: 0 4px 14px rgba(3, 105, 161, 0.25);
    }
    .sr-header h1 {
        color: #ffffff;
        margin: 0;
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .sr-header p {
        color: #e0f2fe;
        margin: 6px 0 0 0;
        font-size: 0.95rem;
    }

    /* Section headers - a small colored tab in front of the title */
    .sr-section-title {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 6px 0 4px 0;
    }
    .sr-section-title .bar {
        width: 5px;
        height: 22px;
        border-radius: 3px;
        background: #0891b2;
    }

    /* Badge pill - used for the live/demo data-source indicator and can be
       reused anywhere else a status needs to be shown as a small chip. */
    .badge-pill {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.85rem;
        color: white;
        letter-spacing: 0.01em;
    }

    /* Stat card - a small metric tile, nicer than the bare default metric */
    .stat-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }
    .stat-card .stat-label {
        font-size: 0.78rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-bottom: 4px;
    }
    .stat-card .stat-value {
        font-size: 1.9rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.1;
    }
    .stat-card.accent .stat-value { color: #0891b2; }

    /* Tighter default spacing under Streamlit's own headers */
    div[data-testid="stVerticalBlock"] > div:has(> div.sr-header) { margin-bottom: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sr-header">
        <h1>🌊 Samudra Rakshak</h1>
        <p>Maritime monitoring &amp; deep-sea preservation dashboard — built for Bit N Build '26</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ===========================================================================
# DARK VESSEL MONITOR
# ===========================================================================
st.markdown(
    '<div class="sr-section-title"><div class="bar"></div>'
    '<h2 style="margin:0;font-size:1.35rem;">🛰️ Dark Vessel Monitor</h2></div>',
    unsafe_allow_html=True,
)
st.write(
    "Finds ships that have stopped broadcasting their position - a possible "
    "sign of illegal fishing."
)

# Preset areas to scan. Gulf of Mannar is our home patch; the North Sea is
# included because it reliably has live data, which makes it the safest
# choice when demonstrating the live feed.
AREA_PRESETS = {
    "Gulf of Mannar (default)": DEFAULT_AREA,
    "Chennai coast": {"min_lat": 12.0, "max_lat": 14.5, "min_lon": 79.5, "max_lon": 82.0},
    "North Sea (busy - best for a live demo)": {
        "min_lat": 54.0, "max_lat": 58.0, "min_lon": 2.0, "max_lon": 8.0,
    },
}

# How each severity is drawn on the map.
SEVERITY_COLOURS = {"low": "#3b82f6", "medium": "#f59e0b", "high": "#ef4444"}
SEVERITY_ICONS = {"low": "🔵", "medium": "🟠", "high": "🔴"}

# What badge to show for each data_source the orchestrator can report.
# The key point: this is driven by what ACTUALLY ran, not by what was picked.
DATA_SOURCE_BADGES = {
    "live": ("🟢 Live Data", "#16a34a", "Positions came from the live Global Fishing Watch feed."),
    "demo": ("🟡 Demo Data", "#ca8a04", "Sample data, chosen on purpose. Not real vessels."),
    "demo (live call failed)": (
        "🟠 Demo Data (live call failed)",
        "#ea580c",
        "Live data was requested but the Global Fishing Watch call did not "
        "succeed, so sample data is shown instead.",
    ),
}

controls_column, results_column = st.columns([1, 2])

with controls_column:
    chosen_area_name = st.selectbox("Area to scan", list(AREA_PRESETS.keys()))

    # The toggle the judges can flip.
    data_choice = st.radio(
        "Data source",
        ["Live GFW Data", "Demo Sample Data"],
        horizontal=True,
        help="Live uses the real Global Fishing Watch API. Demo uses built-in "
             "sample vessels with a realistic spread of severities.",
    )

    scan_was_clicked = st.button("Scan for dark vessels", type="primary")

# Run the scan and remember the result, so the map survives Streamlit's
# reruns when the user interacts with it.
if scan_was_clicked:
    with st.spinner("Scanning..."):
        st.session_state["dark_vessel_result"] = check_dark_vessels(
            area=AREA_PRESETS[chosen_area_name],
            use_demo_data=(data_choice == "Demo Sample Data"),
        )
        st.session_state["dark_vessel_area"] = AREA_PRESETS[chosen_area_name]

result = st.session_state.get("dark_vessel_result")

with results_column:
    if result is None:
        st.info("Pick an area and press **Scan for dark vessels** to begin.")
    else:
        flagged_vessels = result["vessels"]
        data_source = result["data_source"]

        # ---- The honesty badge ------------------------------------------
        label, colour, explanation = DATA_SOURCE_BADGES.get(
            data_source, (f"⚪ {data_source}", "#6b7280", "")
        )
        st.markdown(
            f"<span class='badge-pill' style='background:{colour};'>{label}</span>",
            unsafe_allow_html=True,
        )
        st.caption(explanation)

        new_count = sum(1 for v in flagged_vessels if v.get("is_new"))

        flagged_metric, new_metric = st.columns(2)
        with flagged_metric:
            st.markdown(
                f"""<div class="stat-card">
                    <div class="stat-label">Vessels Flagged</div>
                    <div class="stat-value">{len(flagged_vessels)}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with new_metric:
            st.markdown(
                f"""<div class="stat-card accent">
                    <div class="stat-label">New or Escalated</div>
                    <div class="stat-value">{new_count}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        if not flagged_vessels:
            st.success("No vessels are currently dark in this area.")

# ===========================================================================
# HOW EACH CATEGORY IS PRESENTED
#
# The point of this whole block: a foreign boat on our side of the line and
# one of our own fishermen drifting towards it are NOT the same event, and
# must not look the same on screen. Foreign/unidentified get solid threat
# markers; our own boats get a hollow amber ring, which reads as "warn a
# friend" rather than "target".
# ===========================================================================
CATEGORY_ORDER = [
    "foreign_intrusion",
    "border_safety_alert",
    "unidentified_near_zone",
    "routine_gap",
]

CATEGORY_META = {
    "foreign_intrusion": {
        "emoji": "🚩",
        "label": "Foreign Intrusion",
        "colour": "#dc2626",
        "blurb": "Foreign-flagged vessel on our side of the boundary.",
    },
    "border_safety_alert": {
        "emoji": "⚠️",
        "label": "Border Safety Alert (our fishermen)",
        "colour": "#f59e0b",
        "blurb": "One of our own boats close to the line. This is a heads-up "
                 "to warn them, not an accusation.",
    },
    "unidentified_near_zone": {
        "emoji": "❓",
        "label": "Unidentified Near Zone",
        "colour": "#7c3aed",
        "blurb": "Unidentified vessel loitering near the boundary.",
    },
    "routine_gap": {
        "emoji": "ℹ️",
        "label": "Routine Gaps (low priority)",
        "colour": "#94a3b8",
        "blurb": "Silent in open water, far from anything sensitive. Almost "
                 "always just a radio fault.",
    },
}


def vessel_display_name(vessel: dict) -> str:
    """
    What to call this vessel on screen.

    Live GFW ids are unreadable hex, so prefer the real name when the feed
    gave us one and fall back to the id otherwise.
    """
    return vessel.get("vessel_name") or vessel["vessel_id"]


def vessel_flag_label(vessel: dict) -> str:
    """A short "Flag: IND" label, or "Flag: unknown" when the feed had none."""
    flag = vessel.get("flag")
    return f"Flag: {flag}" if flag else "Flag: unknown"


def draw_vessel_marker(vessel: dict, target_map) -> None:
    """
    Put one vessel on the map, styled by its category.

    Foreign and unidentified vessels are drawn as solid, saturated dots -
    they read as threats. Our own fishermen are drawn as a hollow amber ring,
    deliberately softer, so nobody mistakes a safety warning for an accusation.
    Routine gaps are small grey dots that stay out of the way.
    """
    category = vessel.get("category", "routine_gap")
    style = CATEGORY_META.get(category, CATEGORY_META["routine_gap"])
    is_new = vessel.get("is_new", False)

    if category == "border_safety_alert":
        # Hollow ring - a warning for a friend, not a target.
        radius = 12
        fill_opacity = 0.12
        weight = 4
    elif category == "routine_gap":
        # Small and quiet, so it does not compete with the real alerts.
        radius = 4
        fill_opacity = 0.55
        weight = 1
    else:
        # Solid threat marker.
        radius = 10 if is_new else 8
        fill_opacity = 0.9
        weight = 3 if is_new else 1

    distance_km = vessel.get("distance_to_border_km", "?")

    folium.CircleMarker(
        location=[vessel["lat"], vessel["lon"]],
        radius=radius,
        color=style["colour"],
        weight=weight,
        fill=True,
        fill_color=style["colour"],
        fill_opacity=fill_opacity,
        popup=folium.Popup(
            f"<b>{vessel_display_name(vessel)}</b>"
            f"{' <b>(NEW)</b>' if is_new else ''}<br>"
            f"{style['emoji']} {style['label']}<br>"
            f"{vessel_flag_label(vessel)}<br>"
            f"Severity: {vessel['severity'].upper()}<br>"
            f"{distance_km} km from boundary<br>"
            f"{vessel['flagged_reason']}",
            max_width=320,
        ),
        tooltip=f"{style['emoji']} {vessel_display_name(vessel)} ({distance_km} km)",
    ).add_to(target_map)


def draw_boundary_line(target_map) -> None:
    """
    Draw the illustrative boundary as a dashed line.

    Dashed on purpose: a solid line would imply this is a surveyed legal
    border, and it is not. See the comment on ILLUSTRATIVE_BOUNDARY_LINE.
    """
    folium.PolyLine(
        locations=[[p["lat"], p["lon"]] for p in ILLUSTRATIVE_BOUNDARY_LINE],
        color="#be123c",
        weight=3,
        opacity=0.9,
        dash_array="10, 8",
        tooltip="Illustrative maritime boundary (approximate)",
        popup=folium.Popup(
            "<b>Illustrative maritime boundary (approximate)</b><br>"
            "For demo visualisation only. These are NOT surveyed or legal "
            "boundary coordinates.",
            max_width=300,
        ),
    ).add_to(target_map)


# ---- Map and alert list ------------------------------------------------
if result and result["vessels"]:
    area = st.session_state.get("dark_vessel_area", DEFAULT_AREA)

    # NOTE: deliberately using folium's default OpenStreetMap tiles here.
    # "CartoDB positron" looks nicer but now requires Carto's own API key,
    # which we don't have - it silently rendered "API KEY REQUIRED" watermarks
    # instead of a map. OpenStreetMap's default tiles need no key at all.
    vessel_map = folium.Map(
        location=[
            (area["min_lat"] + area["max_lat"]) / 2,
            (area["min_lon"] + area["max_lon"]) / 2,
        ],
        zoom_start=7,
    )

    # Outline the area we searched.
    folium.Rectangle(
        bounds=[[area["min_lat"], area["min_lon"]], [area["max_lat"], area["max_lon"]]],
        color="#64748b",
        weight=1,
        fill=False,
    ).add_to(vessel_map)

    # The sensitive line everything is measured against.
    draw_boundary_line(vessel_map)

    # One marker per flagged vessel, styled by category.
    for vessel in result["vessels"]:
        draw_vessel_marker(vessel, vessel_map)

    st_folium(vessel_map, height=450, use_container_width=True)

    st.caption(
        "The dashed red line is an **approximate, illustrative** maritime "
        "boundary for demo visualisation only - not surveyed or legal "
        "coordinates."
    )

    # ---- Alerts, grouped by category ------------------------------------
    st.subheader("Alerts by category")
    st.caption("🔵 **NEW** means newly flagged, or escalated since the last scan.")

    # Bucket the vessels so each category gets its own clearly separated
    # section. Grouping matters more than sorting here: an officer wants to
    # see "is anything foreign on our side" first, not scroll a flat list.
    vessels_by_category = {name: [] for name in CATEGORY_ORDER}
    for vessel in result["vessels"]:
        category = vessel.get("category", "routine_gap")
        vessels_by_category.setdefault(category, []).append(vessel)

    severity_order = {"high": 0, "medium": 1, "low": 2}

    for category in CATEGORY_ORDER:
        vessels_in_category = vessels_by_category.get(category, [])
        style = CATEGORY_META[category]

        # Coloured header bar so the four groups are impossible to confuse.
        st.markdown(
            f"<div style='background:{style['colour']};color:white;"
            f"padding:8px 14px;border-radius:8px;margin:16px 0 6px 0;"
            f"font-weight:700;font-size:1rem;'>"
            f"{style['emoji']} {style['label']} &nbsp;({len(vessels_in_category)})"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption(style["blurb"])

        if not vessels_in_category:
            st.markdown(
                "<span style='color:#94a3b8;font-size:0.88rem;'>Nothing in "
                "this category.</span>",
                unsafe_allow_html=True,
            )
            continue

        # Worst severity first inside each group.
        for vessel in sorted(
            vessels_in_category,
            key=lambda v: (severity_order.get(v["severity"], 3), not v.get("is_new", False)),
        ):
            is_new = vessel.get("is_new", False)
            distance_km = vessel.get("distance_to_border_km", "?")
            title = (
                f"{style['emoji']} {'🔵 NEW - ' if is_new else ''}"
                f"{vessel['severity'].upper()} - {vessel_display_name(vessel)} "
                f"({distance_km} km from boundary)"
            )

            # Only auto-open the genuinely urgent ones.
            should_expand = (
                category in ("foreign_intrusion", "border_safety_alert")
                and vessel["severity"] in ("medium", "high")
            )

            with st.expander(title, expanded=should_expand):
                st.write(vessel["flagged_reason"])
                st.caption(
                    f"{vessel_flag_label(vessel)} · ID {vessel['vessel_id']} · "
                    f"Position: {vessel['lat']:.4f}, {vessel['lon']:.4f} "
                    f"· {distance_km} km from the illustrative boundary"
                )


# ===========================================================================
# ROUTE OPTIMIZER
# ===========================================================================
st.markdown("---")
st.markdown(
    '<div class="sr-section-title"><div class="bar"></div>'
    '<h2 style="margin:0;font-size:1.35rem;">⛵ Route Optimizer</h2></div>',
    unsafe_allow_html=True,
)
st.write(
    "Works out a fuel-efficient path between two ports, nudging around rough "
    "water using live wind data."
)

# A few ports around the area we operate in, so nobody has to type
# coordinates during a demo.
PORT_PRESETS = {
    "Rameswaram": {"lat": 9.2876, "lon": 79.3129},
    "Mandapam": {"lat": 9.2760, "lon": 79.1250},
    "Tuticorin (Thoothukudi)": {"lat": 8.7642, "lon": 78.1348},
    "Kochi": {"lat": 9.9312, "lon": 76.2673},
    "Chennai": {"lat": 13.0827, "lon": 80.2707},
    "Colombo": {"lat": 6.9271, "lon": 79.8612},
}

route_controls, route_results = st.columns([1, 2])

with route_controls:
    start_port_name = st.selectbox("From", list(PORT_PRESETS.keys()), index=0)
    end_port_name = st.selectbox("To", list(PORT_PRESETS.keys()), index=3)
    route_was_clicked = st.button("Optimize route", type="primary")

if route_was_clicked:
    if start_port_name == end_port_name:
        st.warning("Pick two different ports.")
    else:
        with st.spinner("Checking wind along the route..."):
            # The route agent draws great-circle lines and knows nothing about
            # land, so asking it for Rameswaram -> Kochi in one go would sail
            # straight across Tamil Nadu. Instead we break the voyage into
            # short offshore legs and optimise each one, then join them up.
            sea_points = plan_sea_route(start_port_name, end_port_name, PORT_PRESETS)

            stitched_waypoints = []
            total_distance_km = 0.0
            total_baseline_fuel = 0.0
            total_estimated_fuel = 0.0

            for leg_start, leg_end in zip(sea_points, sea_points[1:]):
                leg = get_optimized_route(
                    {"lat": leg_start["lat"], "lon": leg_start["lon"]},
                    {"lat": leg_end["lat"], "lon": leg_end["lon"]},
                )

                total_distance_km += leg["distance_km"]
                total_baseline_fuel += leg["baseline_fuel_liters"]
                total_estimated_fuel += leg["estimated_fuel_liters"]

                # Skip the first waypoint of every leg after the first, since
                # it is the same point the previous leg ended on.
                leg_waypoints = leg["waypoints"] if not stitched_waypoints else leg["waypoints"][1:]
                stitched_waypoints.extend(leg_waypoints)

            st.session_state["route_result"] = {
                "waypoints": stitched_waypoints,
                "distance_km": round(total_distance_km, 2),
                "baseline_fuel_liters": round(total_baseline_fuel, 2),
                "estimated_fuel_liters": round(total_estimated_fuel, 2),
            }
            st.session_state["route_labels"] = (start_port_name, end_port_name)
            # Keep the corridor names so we can show the path taken.
            st.session_state["route_via"] = [
                point["name"] for point in sea_points[1:-1]
            ]

route_result = st.session_state.get("route_result")

with route_results:
    if route_result is None:
        st.info("Pick two ports and press **Optimize route**.")
    else:
        baseline_fuel = route_result["baseline_fuel_liters"]
        optimized_fuel = route_result["estimated_fuel_liters"]

        # Guard against dividing by zero if the two ports were the same point.
        if baseline_fuel > 0:
            saved_percent = (baseline_fuel - optimized_fuel) / baseline_fuel * 100
        else:
            saved_percent = 0.0

        from_label, to_label = st.session_state.get("route_labels", ("Start", "End"))
        st.markdown(f"**{from_label} → {to_label}**")

        via_names = st.session_state.get("route_via", [])
        if via_names:
            st.caption("Routed offshore via " + " → ".join(via_names))

        # The plain-text summary asked for, kept as one readable line.
        st.markdown(
            f"Baseline: **{baseline_fuel}L**, Optimized: "
            f"**{optimized_fuel}L**, saved **{saved_percent:.1f}%**"
        )

        distance_card, saving_card = st.columns(2)
        with distance_card:
            st.markdown(
                f"""<div class="stat-card">
                    <div class="stat-label">Route Distance</div>
                    <div class="stat-value">{route_result['distance_km']} km</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with saving_card:
            st.markdown(
                f"""<div class="stat-card accent">
                    <div class="stat-label">Fuel Saved</div>
                    <div class="stat-value">{baseline_fuel - optimized_fuel:.1f} L</div>
                </div>""",
                unsafe_allow_html=True,
            )

if route_result:
    waypoints = route_result["waypoints"]

    # Centre the map on the middle of the route.
    route_lats = [w["lat"] for w in waypoints]
    route_lons = [w["lon"] for w in waypoints]

    route_map = folium.Map(
        location=[sum(route_lats) / len(route_lats), sum(route_lons) / len(route_lons)],
        zoom_start=7,
    )

    # The optimized path.
    folium.PolyLine(
        locations=[[w["lat"], w["lon"]] for w in waypoints],
        color="#0891b2",
        weight=4,
        opacity=0.95,
        tooltip="Optimized route",
    ).add_to(route_map)

    # Start and end pins.
    folium.Marker(
        location=[waypoints[0]["lat"], waypoints[0]["lon"]],
        tooltip="Start",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(route_map)
    folium.Marker(
        location=[waypoints[-1]["lat"], waypoints[-1]["lon"]],
        tooltip="Destination",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(route_map)

    # The detour waypoints in between.
    for waypoint in waypoints[1:-1]:
        folium.CircleMarker(
            location=[waypoint["lat"], waypoint["lon"]],
            radius=5,
            color="#0891b2",
            fill=True,
            fill_opacity=0.9,
            tooltip="Waypoint",
        ).add_to(route_map)

    st_folium(route_map, height=420, use_container_width=True)
    st.caption(
        "The voyage is split into short offshore legs so it stays at sea "
        "instead of cutting across land. 'Baseline' is that same sea route "
        "without weather detours. Offshore waypoints are approximate and for "
        "demo visualisation only - not charted shipping lanes. Fuel figures "
        "use an approximate demo consumption rate."
    )


# ===========================================================================
# DEBRIS CLEANUP
# ===========================================================================
st.markdown("---")
st.markdown(
    '<div class="sr-section-title"><div class="bar"></div>'
    '<h2 style="margin:0;font-size:1.35rem;">🗑️ Debris Cleanup Planner</h2></div>',
    unsafe_allow_html=True,
)
st.write(
    "Plans the shortest collection round for a cleanup boat, visiting every "
    "reported debris sighting."
)

# The cleanup boat always sets out from the same harbour, so there is nothing
# for the user to fill in - one button is the whole interface.
CLEANUP_START = {"lat": 9.2876, "lon": 79.3129}   # Rameswaram harbour

cleanup_controls, cleanup_results = st.columns([1, 2])

with cleanup_controls:
    st.caption(
        f"Departing Rameswaram harbour "
        f"({CLEANUP_START['lat']:.4f}, {CLEANUP_START['lon']:.4f})"
    )
    cleanup_was_clicked = st.button("Plan cleanup route", type="primary")

if cleanup_was_clicked:
    with st.spinner("Planning collection order..."):
        st.session_state["cleanup_result"] = get_cleanup_plan(CLEANUP_START)

cleanup_result = st.session_state.get("cleanup_result")

with cleanup_results:
    if cleanup_result is None:
        st.info("Press **Plan cleanup route** to build a collection round.")
    else:
        visit_order = cleanup_result["visit_order"]

        stops_card, distance_card = st.columns(2)
        with stops_card:
            st.markdown(
                f"""<div class="stat-card">
                    <div class="stat-label">Debris Stops</div>
                    <div class="stat-value">{len(visit_order)}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with distance_card:
            st.markdown(
                f"""<div class="stat-card accent">
                    <div class="stat-label">Total Distance</div>
                    <div class="stat-value">{cleanup_result['total_distance_km']} km</div>
                </div>""",
                unsafe_allow_html=True,
            )

        if visit_order:
            st.markdown("**Collection order**")
            st.markdown("Harbour → " + " → ".join(visit_order))
        else:
            st.success("No debris sightings to collect.")

if cleanup_result and cleanup_result["visit_order"]:
    cleanup_waypoints = cleanup_result["waypoints"]

    cleanup_lats = [w["lat"] for w in cleanup_waypoints]
    cleanup_lons = [w["lon"] for w in cleanup_waypoints]

    cleanup_map = folium.Map(
        location=[sum(cleanup_lats) / len(cleanup_lats),
                  sum(cleanup_lons) / len(cleanup_lons)],
        zoom_start=9,
    )

    # The round trip, in the order the boat will sail it.
    folium.PolyLine(
        locations=[[w["lat"], w["lon"]] for w in cleanup_waypoints],
        color="#059669",
        weight=4,
        opacity=0.9,
        tooltip="Cleanup route",
    ).add_to(cleanup_map)

    # The harbour it leaves from.
    folium.Marker(
        location=[cleanup_waypoints[0]["lat"], cleanup_waypoints[0]["lon"]],
        tooltip="Rameswaram harbour (start)",
        icon=folium.Icon(color="blue", icon="home"),
    ).add_to(cleanup_map)

    # Numbered stops. waypoints[0] is the harbour, so waypoints[1:] lines up
    # one-for-one with visit_order.
    for stop_number, (debris_id, waypoint) in enumerate(
        zip(cleanup_result["visit_order"], cleanup_waypoints[1:]), start=1
    ):
        folium.Marker(
            location=[waypoint["lat"], waypoint["lon"]],
            tooltip=f"Stop {stop_number}: {debris_id}",
            popup=folium.Popup(
                f"<b>Stop {stop_number}</b><br>{debris_id}", max_width=200
            ),
            icon=folium.DivIcon(
                html=(
                    f"<div style='background:#059669;color:white;width:24px;"
                    f"height:24px;border-radius:50%;text-align:center;"
                    f"line-height:24px;font-weight:700;font-size:12px;"
                    f"border:2px solid white;'>{stop_number}</div>"
                ),
                icon_size=(24, 24),
                icon_anchor=(12, 12),
            ),
        ).add_to(cleanup_map)

    st_folium(cleanup_map, height=420, use_container_width=True)
    st.caption(
        "Numbers show the order the boat collects each sighting, planned with "
        "a nearest-neighbour route."
    )
