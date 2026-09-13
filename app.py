"""
app.py
------
Samudra Rakshak - Streamlit dashboard for a maritime authority.

Three sections, organized into tabs:
  1. Dark Vessel Monitor  - silent vessels, classified by where they are
                            relative to an illustrative maritime boundary
  2. Route Optimizer      - fuel-efficient path between two ports
  3. Debris Cleanup       - collection round for a cleanup boat

UI/UX pass:
  - Pinned dark maritime theme (.streamlit/config.toml)
  - High-contrast, enlarged typography optimized for video recordings on laptops and phones
  - Cohesive dark stat cards and visual hierarchy
  - Tabbed layout to eliminate vertical scrolling

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
from agents.route_agent import FUEL_RATE_LITERS_PER_KM

st.set_page_config(
    page_title="Samudra Rakshak — Maritime Authority",
    page_icon="🌊",
    layout="wide",
)

# ===========================================================================
# SHARED STYLES - Designed for high legibility in screen recordings
# ===========================================================================
st.markdown(
    """
    <style>
    /* Top Header Banner */
    .sr-header {
        background: linear-gradient(135deg, #032b43 0%, #0369a1 60%, #0891b2 100%);
        padding: 24px 30px;
        border-radius: 16px;
        margin-bottom: 16px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 8px 24px rgba(3, 105, 161, 0.3);
    }
    .sr-header h1 {
        color: #ffffff;
        margin: 0;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.02em;
    }
    .sr-header p {
        color: #e0f2fe;
        margin: 6px 0 0 0;
        font-size: 1.05rem;
        font-weight: 500;
    }

    /* Section Header Bars */
    .sr-section-title {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 10px 0 6px 0;
    }
    .sr-section-title .bar {
        width: 6px;
        height: 26px;
        border-radius: 3px;
        background: #0ea5e9;
    }
    .sr-section-title h2 {
        margin: 0;
        font-size: 1.55rem;
        font-weight: 700;
        color: #f8fafc;
    }

    /* Badge Pill */
    .badge-pill {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.92rem;
        color: white;
        letter-spacing: 0.02em;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
    }

    /* Dark Mode Stat Card - Huge numbers for video clarity */
    .stat-card {
        background: #131c31;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        margin-bottom: 8px;
    }
    .stat-card .stat-label {
        font-size: 0.88rem;
        color: #94a3b8;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .stat-card .stat-value {
        font-size: 2.7rem;
        font-weight: 900;
        color: #f8fafc;
        line-height: 1.05;
        letter-spacing: -0.02em;
    }
    .stat-card.accent .stat-value {
        color: #38bdf8;
    }

    /* AI Triage Card */
    .triage-card {
        background: #0f172a;
        border-left: 5px solid #0ea5e9;
        border-radius: 12px;
        padding: 18px 22px;
        margin: 14px 0;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .triage-reasoning {
        font-size: 1.15rem;
        line-height: 1.6;
        color: #e2e8f0;
        font-weight: 500;
        margin-top: 10px;
    }

    /* Warning Message Box - Tamil & English radio dispatch */
    .warning-box {
        background: #1e1b18;
        border: 2px solid #f59e0b;
        border-radius: 12px;
        padding: 18px 20px;
        margin: 12px 0;
        box-shadow: 0 4px 14px rgba(245, 158, 11, 0.15);
    }
    .warning-box .tamil-text {
        font-size: 1.25rem;
        line-height: 1.65;
        color: #fef08a;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .warning-box .english-text {
        font-size: 1.05rem;
        line-height: 1.5;
        color: #f8fafc;
        font-weight: 600;
    }

    /* Streamlit Tab Styling Enhancement */
    button[data-baseweb="tab"] {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.markdown(
        """
        <div class="sr-header">
            <h1>🌊 Samudra Rakshak</h1>
            <p>Maritime Surveillance & Deep-Sea Protection Authority — Command Dashboard</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with header_col2:
    FISHERMAN_APP_URL = "http://localhost:8502"
    st.write("")
    st.link_button(
        "📱 Open Fisherman's App",
        FISHERMAN_APP_URL,
        use_container_width=True,
        help="Opens the separate crew-facing alert app on port 8502 in a new tab.",
    )

# Tabbed Navigation to eliminate vertical scrolling during video demos
tab_dark, tab_route, tab_debris = st.tabs([
    "🛰️ Dark Vessel Monitor",
    "⛵ Route Optimizer",
    "🗑️ Debris Cleanup",
])


# ===========================================================================
# TAB 1: DARK VESSEL MONITOR
# ===========================================================================
with tab_dark:
    st.markdown(
        '<div class="sr-section-title"><div class="bar"></div>'
        '<h2>🛰️ Dark Vessel Monitor</h2></div>',
        unsafe_allow_html=True,
    )
    st.write(
        "Identifies vessels that have stopped broadcasting AIS position — "
        "a key indicator of illegal fishing or maritime boundary drift."
    )

    AREA_PRESETS = {
        "Gulf of Mannar (default)": DEFAULT_AREA,
        "Chennai coast": {"min_lat": 12.0, "max_lat": 14.5, "min_lon": 79.5, "max_lon": 82.0},
        "North Sea (busy - best for a live demo)": {
            "min_lat": 54.0, "max_lat": 58.0, "min_lon": 2.0, "max_lon": 8.0,
        },
    }

    SEVERITY_COLOURS = {"low": "#3b82f6", "medium": "#f59e0b", "high": "#ef4444"}
    SEVERITY_ICONS = {"low": "🔵", "medium": "🟠", "high": "🔴"}

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

    controls_column, results_column = st.columns([1, 2], gap="medium")

    with controls_column:
        chosen_area_name = st.selectbox("Area to scan", list(AREA_PRESETS.keys()), key="dark_area_select")

        data_choice = st.radio(
            "Data source",
            ["Live GFW Data", "Demo Sample Data"],
            horizontal=True,
            help="Live uses the real Global Fishing Watch API. Demo uses built-in "
                 "sample vessels with a realistic spread of severities.",
            key="dark_data_source_radio",
        )

        scan_was_clicked = st.button("Scan for dark vessels", type="primary", use_container_width=True)

    if scan_was_clicked:
        with st.spinner("Scanning maritime area for dark vessels..."):
            st.session_state["dark_vessel_result"] = check_dark_vessels(
                area=AREA_PRESETS[chosen_area_name],
                use_demo_data=(data_choice == "Demo Sample Data"),
            )
            st.session_state["dark_vessel_area"] = AREA_PRESETS[chosen_area_name]

    result = st.session_state.get("dark_vessel_result")

    with results_column:
        if result is None:
            st.info("Select an area and press **Scan for dark vessels** to initiate monitoring.")
        else:
            flagged_vessels = result["vessels"]
            data_source = result["data_source"]

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

    # AI Triage: Action priority
    if result and result.get("triage") and result["vessels"]:
        triage = result["triage"]

        st.markdown(
            '<div class="sr-section-title"><div class="bar"></div>'
            '<h3 style="margin:0;font-size:1.25rem;color:#f8fafc;">🧠 AI Triage &mdash; Priority Action Plan</h3>'
            '</div>',
            unsafe_allow_html=True,
        )

        ranking_html = ""
        if triage.get("ranking"):
            ranking_items = []
            for idx, name in enumerate(triage["ranking"], start=1):
                if idx == 1:
                    ranking_items.append(f"<span style='color:#38bdf8;font-weight:800;'>{idx}. {name} (Top Priority)</span>")
                else:
                    ranking_items.append(f"<span>{idx}. {name}</span>")
            ranking_html = " &nbsp;➔&nbsp; ".join(ranking_items)

        # Flatten any newlines: embedded line breaks would break the HTML
        # block and show raw markup on screen.
        reasoning_text = " ".join(str(triage.get("reasoning", "")).split())

        st.markdown(
            f"""
            <div class="triage-card">
                <div style="font-size:1.05rem;font-weight:700;color:#38bdf8;margin-bottom:8px;">
                    Patrol Boat Dispatch Order: &nbsp; {ranking_html}
                </div>
                <div class="triage-reasoning">
                    {reasoning_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not triage.get("available"):
            st.warning(
                "AI triage unavailable — showing the rule-based order instead. "
                "The dashboard says which one you are looking at rather than "
                "passing one off as the other."
            )

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
            "colour": "#64748b",
            "blurb": "Silent in open water, far from anything sensitive. Almost "
                     "always just a radio fault.",
        },
    }

    def vessel_display_name(vessel: dict) -> str:
        return vessel.get("vessel_name") or vessel["vessel_id"]

    def vessel_flag_label(vessel: dict) -> str:
        flag = vessel.get("flag")
        return f"Flag: {flag}" if flag else "Flag: unknown"

    def draw_vessel_marker(vessel: dict, target_map) -> None:
        category = vessel.get("category", "routine_gap")
        style = CATEGORY_META.get(category, CATEGORY_META["routine_gap"])
        is_new = vessel.get("is_new", False)

        if category == "border_safety_alert":
            radius = 13
            fill_opacity = 0.15
            weight = 4
        elif category == "routine_gap":
            radius = 5
            fill_opacity = 0.5
            weight = 1
        else:
            radius = 11 if is_new else 9
            fill_opacity = 0.92
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
            tooltip=f"{style['emoji']} {vessel_display_name(vessel)} · "
                    f"{vessel.get('flag') or 'no flag'} · {distance_km} km",
        ).add_to(target_map)

        # The flag state, printed ON the map next to the dot.
        #
        # Without this the map only shows WHERE a vessel is, so a red marker
        # sitting in Indian waters reads as "an Indian boat marked as a
        # threat". It is the opposite: it is red BECAUSE it is foreign and it
        # is in our waters. Nobody hovers a tooltip during a three-minute
        # video, so the flag has to be visible without interaction.
        flag_code = vessel.get("flag") or "?"

        if category == "routine_gap":
            # Routine gaps stay quiet - no label, so they do not compete.
            return

        folium.Marker(
            location=[vessel["lat"], vessel["lon"]],
            icon=folium.DivIcon(
                html=(
                    f"<div style='transform:translate(14px,-9px);"
                    f"background:{style['colour']};color:#ffffff;"
                    f"padding:1px 6px;border-radius:5px;"
                    f"font-size:11px;font-weight:800;letter-spacing:0.04em;"
                    f"white-space:nowrap;border:1px solid rgba(255,255,255,0.35);"
                    f"box-shadow:0 1px 4px rgba(0,0,0,0.5);'>{flag_code}</div>"
                ),
                icon_size=(0, 0),
                icon_anchor=(0, 0),
            ),
        ).add_to(target_map)

    def draw_boundary_line(target_map) -> None:
        folium.PolyLine(
            locations=[[p["lat"], p["lon"]] for p in ILLUSTRATIVE_BOUNDARY_LINE],
            color="#ef4444",
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

    # Map & Alert listing
    if result and result["vessels"]:
        area = st.session_state.get("dark_vessel_area", DEFAULT_AREA)

        vessel_map = folium.Map(
            location=[
                (area["min_lat"] + area["max_lat"]) / 2,
                (area["min_lon"] + area["max_lon"]) / 2,
            ],
            zoom_start=7,
        )

        folium.Rectangle(
            bounds=[[area["min_lat"], area["min_lon"]], [area["max_lat"], area["max_lon"]]],
            color="#64748b",
            weight=1,
            fill=False,
        ).add_to(vessel_map)

        draw_boundary_line(vessel_map)

        for vessel in result["vessels"]:
            draw_vessel_marker(vessel, vessel_map)

        interceptions_drawn = 0
        for vessel in result["vessels"]:
            interception = vessel.get("interception")
            if not interception:
                continue

            interceptions_drawn += 1
            route_points = [[w["lat"], w["lon"]] for w in interception["waypoints"]]

            folium.PolyLine(
                locations=route_points,
                color="#0ea5e9",
                weight=3,
                opacity=0.9,
                dash_array="5, 6",
                tooltip=(
                    f"Intercept {vessel_display_name(vessel)} from "
                    f"{interception['base_name']} - {interception['distance_km']} km, "
                    f"{interception['eta_hours']} h"
                ),
            ).add_to(vessel_map)

            folium.Marker(
                location=route_points[0],
                tooltip=f"{interception['base_name']} patrol base",
                icon=folium.Icon(color="blue", icon="flag"),
            ).add_to(vessel_map)

        st_folium(vessel_map, height=460, use_container_width=True)

        if interceptions_drawn:
            st.caption(
                f"Dotted blue lines are **interception routes** - the "
                f"{interceptions_drawn} highest-priority vessels were handed "
                f"automatically to the Route Agent, which planned the fastest "
                f"approach from the nearest patrol base."
            )

        st.caption(
            "🚩 red = foreign flag inside our waters · ⚠️ amber ring = one "
            "of ours near the line · ❓ purple = no flag. The label beside "
            "each marker is the vessel's flag state. "
            "The dashed red line is an **approximate, illustrative** maritime "
            "boundary for demo visualisation only - not surveyed or legal "
            "coordinates."
        )

        st.markdown("### Alerts by Category")
        st.caption("🔵 **NEW** means newly flagged, or escalated since the last scan.")

        vessels_by_category = {name: [] for name in CATEGORY_ORDER}
        for vessel in result["vessels"]:
            category = vessel.get("category", "routine_gap")
            vessels_by_category.setdefault(category, []).append(vessel)

        severity_order = {"high": 0, "medium": 1, "low": 2}

        for category in CATEGORY_ORDER:
            vessels_in_category = vessels_by_category.get(category, [])
            style = CATEGORY_META[category]
            is_routine = (category == "routine_gap")

            header_bg = "#1e293b" if is_routine else style["colour"]
            header_text_color = "#94a3b8" if is_routine else "#ffffff"

            st.markdown(
                f"<div style='background:{header_bg};color:{header_text_color};"
                f"padding:10px 16px;border-radius:10px;margin:18px 0 8px 0;"
                f"font-weight:800;font-size:1.1rem;display:flex;justify-content:space-between;align-items:center;'>"
                f"<span>{style['emoji']} {style['label']}</span>"
                f"<span style='background:rgba(255,255,255,0.15);padding:2px 10px;border-radius:999px;font-size:0.9rem;'>"
                f"{len(vessels_in_category)} "
                f"{'vessel' if len(vessels_in_category) == 1 else 'vessels'}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.caption(style["blurb"])

            if not vessels_in_category:
                st.markdown(
                    "<span style='color:#64748b;font-size:0.9rem;font-style:italic;'>No vessels flagged in this category.</span>",
                    unsafe_allow_html=True,
                )
                continue

            for vessel in sorted(
                vessels_in_category,
                key=lambda v: (severity_order.get(v["severity"], 3), not v.get("is_new", False)),
            ):
                is_new = vessel.get("is_new", False)
                distance_km = vessel.get("distance_to_border_km", "?")
                title = (
                    f"{style['emoji']} {'🔵 NEW — ' if is_new else ''}"
                    f"[{vessel['severity'].upper()}] {vessel_display_name(vessel)} "
                    f"({distance_km} km from boundary)"
                )

                should_expand = (
                    category in ("foreign_intrusion", "border_safety_alert")
                    and vessel["severity"] in ("medium", "high")
                )

                with st.expander(title, expanded=should_expand):
                    st.markdown(f"**Analysis:** {vessel['flagged_reason']}")

                    if vessel.get("warning_message"):
                        st.markdown("**📻 Broadcast Dispatch Warning (Tamil & English)**")
                        # High-prominence bilingual warning box
                        # The agent returns the message as separate lines:
                        #   TA: <tamil>
                        #   EN: <english>
                        #   [DEMO ONLY - ...]
                        # Split on those prefixes, not on a separator string.
                        warning_msg = vessel["warning_message"]
                        tamil_part = ""
                        english_part = ""
                        disclaimer_part = ""

                        for line in warning_msg.splitlines():
                            stripped = line.strip()
                            if not stripped:
                                continue
                            if stripped.startswith("TA:"):
                                tamil_part = stripped[3:].strip()
                            elif stripped.startswith("EN:"):
                                english_part = stripped[3:].strip()
                            elif "DEMO ONLY" in stripped:
                                disclaimer_part = stripped
                            elif tamil_part and not english_part:
                                tamil_part += " " + stripped
                            elif english_part:
                                english_part += " " + stripped

                        # If the model ignored the format, show the raw text
                        # rather than silently dropping the warning.
                        if not tamil_part and not english_part:
                            english_part = warning_msg

                        tamil_html = (
                            f'<div class="tamil-text">📡 {tamil_part}</div>'
                            if tamil_part else ""
                        )
                        english_html = (
                            f'<div class="english-text">📢 {english_part}</div>'
                            if english_part else ""
                        )
                        # The DEMO ONLY caveat must stay with the message.
                        disclaimer_html = (
                            f'<div style="margin-top:10px;font-size:0.72rem;'
                            f'opacity:0.75;line-height:1.4;">{disclaimer_part}</div>'
                            if disclaimer_part else ""
                        )

                        st.markdown(
                            f'<div class="warning-box">{tamil_html}'
                            f'{english_html}{disclaimer_html}</div>',
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            "Drafted in Tamil and English so it can be read out "
                            "over radio or sent as an SMS."
                        )

                    interception = vessel.get("interception")
                    if interception:
                        st.markdown("**🚤 Interception Plan**")
                        st.markdown(
                            f"Nearest patrol base **{interception['base_name']}** · "
                            f"**{interception['distance_km']} km** · "
                            f"ETA **{interception['eta_hours']} h** · "
                            f"**{interception['fuel_liters']} L** fuel"
                        )
                        st.caption(
                            "Planned automatically by the Route Agent from this "
                            "vessel's position - shown dotted on the map above."
                        )

                    times_flagged = vessel.get("times_flagged", 1)
                    previous_category = vessel.get("previous_category")

                    if times_flagged > 1:
                        history_note = f"Flagged on {times_flagged} scans"
                        if previous_category and previous_category != vessel["category"]:
                            was = CATEGORY_META.get(previous_category, {}).get(
                                "label", previous_category
                            )
                            history_note += f" · escalated from *{was}*"
                        st.caption(history_note)

                    st.caption(
                        f"{vessel_flag_label(vessel)} · ID {vessel['vessel_id']} · "
                        f"Position: {vessel['lat']:.4f}, {vessel['lon']:.4f} "
                        f"· {distance_km} km from the illustrative boundary"
                    )


# ===========================================================================
# TAB 2: ROUTE OPTIMIZER
# ===========================================================================
with tab_route:
    st.markdown(
        '<div class="sr-section-title"><div class="bar"></div>'
        '<h2>⛵ Fuel-Efficient Sea Route Optimizer</h2></div>',
        unsafe_allow_html=True,
    )
    st.write(
        "Works out a fuel-efficient path between two ports, nudging around rough "
        "water using live wind data."
    )

    PORT_PRESETS = {
        "Rameswaram": {"lat": 9.2876, "lon": 79.3129},
        "Mandapam": {"lat": 9.2760, "lon": 79.1250},
        "Tuticorin (Thoothukudi)": {"lat": 8.7642, "lon": 78.1348},
        "Kochi": {"lat": 9.9312, "lon": 76.2673},
        "Chennai": {"lat": 13.0827, "lon": 80.2707},
        "Colombo": {"lat": 6.9271, "lon": 79.8612},
    }

    route_controls, route_results = st.columns([1, 2], gap="medium")

    with route_controls:
        start_port_name = st.selectbox("From", list(PORT_PRESETS.keys()), index=0, key="route_start_select")
        end_port_name = st.selectbox("To", list(PORT_PRESETS.keys()), index=3, key="route_end_select")
        route_was_clicked = st.button("Optimize route", type="primary", use_container_width=True)

    if route_was_clicked:
        if start_port_name == end_port_name:
            st.warning("Pick two different ports.")
        else:
            with st.spinner("Analyzing wind, wave conditions and coastal corridors..."):
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

                    leg_waypoints = leg["waypoints"] if not stitched_waypoints else leg["waypoints"][1:]
                    stitched_waypoints.extend(leg_waypoints)

                st.session_state["route_result"] = {
                    "waypoints": stitched_waypoints,
                    "distance_km": round(total_distance_km, 2),
                    "baseline_fuel_liters": round(total_baseline_fuel, 2),
                    "estimated_fuel_liters": round(total_estimated_fuel, 2),
                }
                st.session_state["route_labels"] = (start_port_name, end_port_name)
                st.session_state["route_via"] = [
                    point["name"] for point in sea_points[1:-1]
                ]

    route_result = st.session_state.get("route_result")

    with route_results:
        if route_result is None:
            st.info("Select start and destination ports and press **Optimize route**.")
        else:
            baseline_fuel = route_result["baseline_fuel_liters"]
            optimized_fuel = route_result["estimated_fuel_liters"]

            if baseline_fuel > 0:
                saved_percent = (baseline_fuel - optimized_fuel) / baseline_fuel * 100
            else:
                saved_percent = 0.0

            from_label, to_label = st.session_state.get("route_labels", ("Start", "End"))
            st.markdown(f"### 📍 **{from_label} ➔ {to_label}**")

            via_names = st.session_state.get("route_via", [])
            if via_names:
                st.caption("Routed offshore via " + " → ".join(via_names))

            st.markdown(
                f"Baseline: **{baseline_fuel}L**, Optimized: "
                f"**{optimized_fuel}L**, saved **{saved_percent:.1f}%**"
            )

            distance_card, saving_card = st.columns(2)
            with distance_card:
                st.markdown(
                    f"""<div class="stat-card">
                        <div class="stat-label">Route Distance</div>
                        <div class="stat-value">{route_result['distance_km']} <span style="font-size:1.5rem;font-weight:600;color:#94a3b8;">km</span></div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with saving_card:
                saved_fuel = max(0.0, baseline_fuel - optimized_fuel)
                st.markdown(
                    f"""<div class="stat-card accent">
                        <div class="stat-label">Fuel Saved</div>
                        <div class="stat-value">{saved_fuel:.1f} <span style="font-size:1.5rem;font-weight:600;color:#38bdf8;">L</span></div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    if route_result:
        waypoints = route_result["waypoints"]

        route_lats = [w["lat"] for w in waypoints]
        route_lons = [w["lon"] for w in waypoints]

        route_map = folium.Map(
            location=[sum(route_lats) / len(route_lats), sum(route_lons) / len(route_lons)],
            zoom_start=7,
        )

        folium.PolyLine(
            locations=[[w["lat"], w["lon"]] for w in waypoints],
            color="#0ea5e9",
            weight=4,
            opacity=0.95,
            tooltip="Optimized route",
        ).add_to(route_map)

        folium.Marker(
            location=[waypoints[0]["lat"], waypoints[0]["lon"]],
            tooltip=f"Departure: {from_label}",
            icon=folium.Icon(color="green", icon="play"),
        ).add_to(route_map)

        folium.Marker(
            location=[waypoints[-1]["lat"], waypoints[-1]["lon"]],
            tooltip=f"Arrival: {to_label}",
            icon=folium.Icon(color="red", icon="stop"),
        ).add_to(route_map)

        for waypoint in waypoints[1:-1]:
            folium.CircleMarker(
                location=[waypoint["lat"], waypoint["lon"]],
                radius=5,
                color="#0ea5e9",
                fill=True,
                fill_opacity=0.9,
                tooltip="Offshore Waypoint",
            ).add_to(route_map)

        st_folium(route_map, height=440, use_container_width=True)
        st.caption(
            "The voyage is split into short offshore legs so it stays at sea "
            "instead of cutting across land. 'Baseline' is that same sea route "
            "without weather detours. Offshore waypoints are approximate and for "
            "demo visualisation only - not charted shipping lanes. Fuel figures "
            "use an approximate demo consumption rate."
        )


# ===========================================================================
# TAB 3: DEBRIS CLEANUP PLANNER
# ===========================================================================
with tab_debris:
    st.markdown(
        '<div class="sr-section-title"><div class="bar"></div>'
        '<h2>🗑️ Marine Debris Cleanup Planner</h2></div>',
        unsafe_allow_html=True,
    )
    st.write(
        "Sequences every reported debris sighting into an efficient pickup "
        "order, using a nearest-neighbour route."
    )

    CLEANUP_START = {"lat": 9.2876, "lon": 79.3129}   # Rameswaram harbour

    cleanup_controls, cleanup_results = st.columns([1, 2], gap="medium")

    with cleanup_controls:
        st.caption(
            f"Departing Rameswaram harbour "
            f"({CLEANUP_START['lat']:.4f}, {CLEANUP_START['lon']:.4f})"
        )
        cleanup_was_clicked = st.button("Plan cleanup route", type="primary", use_container_width=True)

    if cleanup_was_clicked:
        with st.spinner("Sequencing pickups by nearest-neighbour..."):
            st.session_state["cleanup_result"] = get_cleanup_plan(CLEANUP_START)

    cleanup_result = st.session_state.get("cleanup_result")

    with cleanup_results:
        if cleanup_result is None:
            st.info("Press **Plan cleanup route** to compute an efficient debris collection route.")
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
                        <div class="stat-label">Collection Distance</div>
                        <div class="stat-value">{cleanup_result['total_distance_km']} <span style="font-size:1.5rem;font-weight:600;color:#38bdf8;">km</span></div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            # What the round actually costs to sail, using the route agent's own
            # fuel rate - so the cleanup is priced on the same basis as a route
            # rather than with a second invented number.
            cleanup_fuel_liters = round(
                cleanup_result["total_distance_km"] * FUEL_RATE_LITERS_PER_KM, 1
            )
            st.markdown(
                f"Estimated fuel for the collection run: **{cleanup_fuel_liters} L** "
                f"({FUEL_RATE_LITERS_PER_KM} L/km)"
            )
            st.caption(
                "Harbour to the final sighting. The return leg is not included - "
                "the planner sequences the pickups, it does not plan the trip home."
            )

            if visit_order:
                st.markdown("### 🧭 Collection Sequence")
                st.markdown("**Harbour** ➔ " + " ➔ ".join([f"**{v}**" for v in visit_order]))
            else:
                st.success("No debris sightings to collect.")

    if cleanup_result and cleanup_result.get("visit_order"):
        cleanup_waypoints = cleanup_result["waypoints"]

        cleanup_lats = [w["lat"] for w in cleanup_waypoints]
        cleanup_lons = [w["lon"] for w in cleanup_waypoints]

        cleanup_map = folium.Map(
            location=[sum(cleanup_lats) / len(cleanup_lats),
                      sum(cleanup_lons) / len(cleanup_lons)],
            zoom_start=9,
        )

        folium.PolyLine(
            locations=[[w["lat"], w["lon"]] for w in cleanup_waypoints],
            color="#10b981",
            weight=4,
            opacity=0.9,
            tooltip="Cleanup route",
        ).add_to(cleanup_map)

        folium.Marker(
            location=[cleanup_waypoints[0]["lat"], cleanup_waypoints[0]["lon"]],
            tooltip="Rameswaram harbour (start)",
            icon=folium.Icon(color="blue", icon="home"),
        ).add_to(cleanup_map)

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
                        f"<div style='background:#10b981;color:white;width:26px;"
                        f"height:26px;border-radius:50%;text-align:center;"
                        f"line-height:24px;font-weight:800;font-size:13px;"
                        f"border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);'>{stop_number}</div>"
                    ),
                    icon_size=(26, 26),
                    icon_anchor=(13, 13),
                ),
            ).add_to(cleanup_map)

        st_folium(cleanup_map, height=440, use_container_width=True)
        st.caption(
            "Numbers show the order the boat collects each sighting, planned with "
            "a nearest-neighbour route."
        )

# ===========================================================================
# Footer Disclaimer & Isolation Note
# ===========================================================================
st.markdown("---")
st.caption(
    "🔒 The fisherman's alert is a **separate app** on his own device — it "
    "carries only the boundary, never the surveillance picture. This opens it "
    "in a new tab; it is a different application, not a tab of this one."
)
