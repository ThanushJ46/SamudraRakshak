"""
app.py
------
Samudra Rakshak - Streamlit dashboard for a maritime authority.

NOTE FOR THE DASHBOARD OWNER:
This file was created to hold the "Dark Vessel Monitor" section only.
The Route Optimization and Debris Cleanup sections are marked with TODO
placeholders near the bottom - add yours there, nothing here will clash.

Run it with:
    streamlit run app.py
"""

import folium
import streamlit as st
from streamlit_folium import st_folium

from agents.orchestrator import DEFAULT_AREA, check_dark_vessels

st.set_page_config(page_title="Samudra Rakshak", page_icon="🌊", layout="wide")

st.title("🌊 Samudra Rakshak")
st.caption("Maritime monitoring and deep-sea preservation dashboard")


# ===========================================================================
# DARK VESSEL MONITOR
# ===========================================================================
st.header("🛰️ Dark Vessel Monitor")
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
            f"<span style='background:{colour};color:white;padding:4px 12px;"
            f"border-radius:12px;font-weight:600;font-size:0.9rem'>{label}</span>",
            unsafe_allow_html=True,
        )
        st.caption(explanation)

        new_count = sum(1 for v in flagged_vessels if v.get("is_new"))

        flagged_metric, new_metric = st.columns(2)
        flagged_metric.metric("Vessels flagged", len(flagged_vessels))
        new_metric.metric("New or escalated", new_count)

        if not flagged_vessels:
            st.success("No vessels are currently dark in this area.")

# ---- Map and alert list ------------------------------------------------
if result and result["vessels"]:
    area = st.session_state.get("dark_vessel_area", DEFAULT_AREA)

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

    # One dot per flagged vessel, coloured by how worrying it is.
    for vessel in result["vessels"]:
        is_new = vessel.get("is_new", False)
        new_tag = " - NEW" if is_new else ""

        folium.CircleMarker(
            location=[vessel["lat"], vessel["lon"]],
            radius=10 if is_new else 7,
            color=SEVERITY_COLOURS.get(vessel["severity"], "#6b7280"),
            # New or escalated vessels get a heavier outline so they stand out
            # from the ones we have already shown before.
            weight=4 if is_new else 1,
            fill=True,
            fill_opacity=0.85,
            popup=folium.Popup(
                f"<b>{vessel['vessel_id']}</b>{' <b>(NEW)</b>' if is_new else ''}<br>"
                f"Severity: {vessel['severity'].upper()}<br>"
                f"{vessel['flagged_reason']}",
                max_width=300,
            ),
            tooltip=f"{vessel['vessel_id']} ({vessel['severity']}){new_tag}",
        ).add_to(vessel_map)

    st_folium(vessel_map, height=450, use_container_width=True)

    st.subheader("Alerts")
    st.caption("🔵 **NEW** means newly flagged, or escalated since the last scan.")

    # Show new ones first, then the worst severity first within each group.
    severity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_vessels = sorted(
        result["vessels"],
        key=lambda v: (not v.get("is_new", False), severity_order.get(v["severity"], 3)),
    )

    for vessel in sorted_vessels:
        is_new = vessel.get("is_new", False)
        title = f"{'🔵 NEW - ' if is_new else ''}{vessel['severity'].upper()} - {vessel['vessel_id']}"

        with st.expander(title, expanded=(is_new and vessel["severity"] == "high")):
            st.write(vessel["flagged_reason"])
            st.caption(f"Position: {vessel['lat']:.4f}, {vessel['lon']:.4f}")


# ===========================================================================
# TODO (dashboard owner): Route Optimization section goes here.
#   from agents.orchestrator import get_optimized_route
# ===========================================================================

# ===========================================================================
# TODO (dashboard owner): Debris Cleanup section goes here.
#   from agents.orchestrator import get_cleanup_plan
# ===========================================================================
