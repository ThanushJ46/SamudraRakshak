"""
fisherman_app.py
----------------
The FISHERMAN's app. Deliberately a separate application from app.py.

This is not a styling choice. A fishing crew must never see the coast guard's
surveillance picture - which vessels are flagged, where the patrol boats are,
or when one is on its way. An app that showed them would be a tool for
evading enforcement rather than a tool for keeping fishermen safe.

So this app shares NO state with the authority's dashboard. It knows exactly
two things: where the boundary is, and how close is too close. It never
imports the orchestrator, the agents, or the vessel feed.

Run it on its own port, alongside the guard dashboard:

    python -m streamlit run fisherman_app.py --server.port 8502

APPROXIMATE BOUNDARY - demonstration only. Not for navigation.
"""

import streamlit as st

from utils.fisherman_page import (
    CAUTION_DISTANCE_KM,
    DANGER_DISTANCE_KM,
    build_offline_alert_page,
)

st.set_page_config(page_title="Samudra Rakshak - Fisherman", page_icon="📱")

st.markdown(
    """
    <style>
    .fisher-header {
        background: linear-gradient(135deg, #0f766e 0%, #0891b2 100%);
        padding: 20px 24px; border-radius: 14px; margin-bottom: 18px;
    }
    .fisher-header h1 { color: #fff; margin: 0; font-size: 1.45rem; font-weight: 700; }
    .fisher-header p { color: #ccfbf1; margin: 5px 0 0 0; font-size: 0.88rem; }
    </style>
    <div class="fisher-header">
        <h1>📱 மீனவர் எச்சரிக்கை · Fisherman Alert</h1>
        <p>எல்லை நெருங்கும் போது எச்சரிக்கை &middot; Boundary warning, GPS only</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "🔒 **This app is separate from the coast guard dashboard on purpose.** "
    "It carries only the boundary — never vessel positions, patrol locations, "
    "or alerts. A crew should be warned, not watched."
)

# A link back, purely so a demo can move between the two without hunting for
# windows. It is a plain URL - this app still shares no state, and no code,
# with the dashboard.
GUARD_APP_URL = "http://localhost:8501"
st.link_button("↩ Back to the coast guard dashboard", GUARD_APP_URL)

st.write(
    "The geofence runs on GPS alone — no network and no AIS. That matters "
    "because the boat that most needs warning is the one that has gone dark."
)

# How each state is drawn. Thresholds come from utils/fisherman_page.py, the
# same ones baked into the downloadable file, so the two cannot drift apart.
FISHERMAN_STATES = {
    "safe": {
        "background": "#14532d",
        "tamil": "பாதுகாப்பாக உள்ளீர்கள்",
        "english": "SAFE",
        "message": "You are well clear of the boundary. Good fishing.",
    },
    "caution": {
        "background": "#854d0e",
        "tamil": "எச்சரிக்கை",
        "english": "CAUTION",
        "message": "Boundary is close. Stay alert and keep your AIS on.",
    },
    "danger": {
        "background": "#7f1d1d",
        "tamil": "எல்லைக்கு மிக அருகில்!",
        "english": "TOO CLOSE - TURN BACK",
        "message": "Turn back towards Indian waters now.",
    },
}

controls_column, screen_column = st.columns([1, 1])

with controls_column:
    st.caption(
        "Drag to simulate the boat approaching the boundary, as it would be "
        "read from GPS on board."
    )
    simulated_distance_km = st.slider(
        "Distance from boundary (km)",
        min_value=0.0,
        max_value=30.0,
        value=14.0,
        step=0.5,
    )

    if simulated_distance_km < DANGER_DISTANCE_KM:
        alert_state = "danger"
    elif simulated_distance_km < CAUTION_DISTANCE_KM:
        alert_state = "caution"
    else:
        alert_state = "safe"

    st.download_button(
        "⬇️ Download the geofence file",
        data=build_offline_alert_page(),
        file_name="samudra_rakshak_alert.html",
        mime="text/html",
        help="One self-contained HTML file with the boundary baked in. No map "
             "tiles, no CDN, no API calls - the geofence needs no network.",
    )
    st.caption(
        "The boundary and the distance maths are baked in, so **no network is "
        "needed to work out how close the boat is** — GPS only receives. "
        "Shipping this for real means packaging it as an installable app "
        "(a PWA): phone browsers only hand GPS to pages from a secure origin, "
        "so opening this file straight off the filesystem will not get a fix. "
        "The logic is what is finished here; the packaging is not."
    )

with screen_column:
    style = FISHERMAN_STATES[alert_state]

    st.markdown(
        f"""
        <div style="max-width:300px;margin:0 auto;border:10px solid #1e293b;
                    border-radius:30px;overflow:hidden;
                    box-shadow:0 6px 20px rgba(0,0,0,0.35);">
          <div style="background:{style['background']};padding:26px 18px;
                      text-align:center;color:#ffffff;">
            <div style="font-size:1.1rem;font-weight:700;margin-bottom:6px;">
              {style['tamil']}
            </div>
            <div style="font-size:1.4rem;font-weight:800;line-height:1.15;">
              {style['english']}
            </div>
            <div style="font-size:2.9rem;font-weight:800;margin:12px 0 0 0;">
              {simulated_distance_km:.1f}
            </div>
            <div style="font-size:0.72rem;opacity:0.85;">
              km from boundary · எல்லையிலிருந்து கி.மீ.
            </div>
          </div>
          <div style="background:#111c2e;padding:14px;color:#cbd5e1;
                      font-size:0.82rem;line-height:1.45;">
            {style['message']}
          </div>
          <div style="background:#1c1917;padding:9px 14px;color:#a8a29e;
                      font-size:0.62rem;line-height:1.4;">
            DEMO ONLY — approximate boundary, not surveyed coordinates.
            Not for navigation.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
