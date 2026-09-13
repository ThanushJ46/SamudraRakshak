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

st.set_page_config(
    page_title="மீனவர் எச்சரிக்கை · Fisherman Alert",
    page_icon="📱",
    layout="centered",
)

# Custom mobile-focused styling
st.markdown(
    """
    <style>
    /* Clean, focused crew interface */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 820px;
    }
    
    .fisher-header {
        background: linear-gradient(135deg, #064e3b 0%, #0f766e 60%, #0284c7 100%);
        padding: 24px 28px;
        border-radius: 18px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 24px rgba(6, 78, 59, 0.35);
    }
    .fisher-header h1 {
        color: #ffffff;
        margin: 0;
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        line-height: 1.3;
    }
    .fisher-header p {
        color: #ccfbf1;
        margin: 8px 0 0 0;
        font-size: 0.95rem;
        font-weight: 500;
    }

    /* Phone device frame */
    .phone-chassis {
        max-width: 320px;
        margin: 0 auto;
        background: #020617;
        border: 12px solid #1e293b;
        border-radius: 42px;
        overflow: hidden;
        box-shadow: 0 16px 36px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.08);
        position: relative;
    }
    .phone-speaker {
        width: 60px;
        height: 5px;
        background: #334155;
        border-radius: 3px;
        margin: 12px auto 8px auto;
    }
    .phone-notch {
        width: 12px;
        height: 12px;
        background: #0f172a;
        border-radius: 50%;
        display: inline-block;
        margin-left: 8px;
    }
    .phone-screen {
        margin: 0;
        padding: 0;
    }

    /* Action card on control side */
    .control-card {
        background: #131c31;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }
    </style>
    <div class="fisher-header">
        <h1>📱 மீனவர் எல்லை எச்சரிக்கை<br><span style="font-size: 1.25rem; font-weight: 600; opacity: 0.95;">Fisherman Border Safety Alert</span></h1>
        <p>GPS வழிநடத்துதல் &middot; தன்னிச்சையான எச்சரிக்கை &middot; GPS Geofence Only</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Cross-link back to coast guard dashboard
GUARD_APP_URL = "http://localhost:8501"
st.link_button("↩ Back to Coast Guard Dashboard", GUARD_APP_URL)

st.write(
    "The geofence runs on GPS alone — no network and no AIS. That matters "
    "because the boat that most needs warning is the one that has gone dark."
)

# State styles with high-contrast, large text for video recording
FISHERMAN_STATES = {
    "safe": {
        "bg_gradient": "linear-gradient(180deg, #064e3b 0%, #065f46 100%)",
        "border_color": "#10b981",
        "tamil": "பாதுகாப்பாக உள்ளீர்கள்",
        "english": "SAFE ZONE",
        "message": "You are well clear of the boundary. Good fishing.",
        "tamil_sub": "எல்லையிலிருந்து பாதுகாப்பான தொலைவில் உள்ளீர்கள்.",
        "icon": "🟢",
    },
    "caution": {
        "bg_gradient": "linear-gradient(180deg, #78350f 0%, #92400e 100%)",
        "border_color": "#f59e0b",
        "tamil": "எச்சரிக்கை! எல்லை அருகில்",
        "english": "CAUTION — CLOSE",
        "message": "Boundary is close. Stay alert and keep your AIS on.",
        "tamil_sub": "எல்லை அருகில் உள்ளது. கவனமாக படகை திருப்பவும்.",
        "icon": "🟡",
    },
    "danger": {
        "bg_gradient": "linear-gradient(180deg, #7f1d1d 0%, #991b1b 100%)",
        "border_color": "#ef4444",
        "tamil": "உடனடியாக திரும்புங்கள்!",
        "english": "TOO CLOSE — TURN BACK",
        "message": "Turn back towards Indian waters now.",
        "tamil_sub": "எல்லைக்கு மிக அருகில்! உடனே இந்திய எல்லைக்குள் செல்லவும்.",
        "icon": "🔴",
    },
}

controls_column, screen_column = st.columns([1, 1], gap="large")

with controls_column:
    st.markdown("### 🧭 GPS Simulator")
    st.caption(
        "Drag the slider to simulate your boat's distance to the boundary line as read by onboard GPS:"
    )
    simulated_distance_km = st.slider(
        "Distance to boundary (km)",
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

    st.markdown("---")
    st.download_button(
        "⬇️ Download Offline Geofence File",
        data=build_offline_alert_page(),
        file_name="samudra_rakshak_alert.html",
        mime="text/html",
        use_container_width=True,
        type="secondary",
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
        <div class="phone-chassis">
          <div class="phone-speaker"></div>
          <div class="phone-screen">
            <div style="background:{style['bg_gradient']};padding:30px 18px 24px 18px;
                        text-align:center;color:#ffffff;border-bottom:3px solid {style['border_color']};">
              <div style="font-size:1.0rem;margin-bottom:8px;">{style['icon']} GPS LIVE</div>
              <div style="font-size:1.35rem;font-weight:800;line-height:1.45;margin-bottom:6px;
                          letter-spacing:0.01em;">
                {style['tamil']}
              </div>
              <div style="font-size:1.25rem;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;">
                {style['english']}
              </div>
              <div style="font-size:4.0rem;font-weight:900;line-height:1.0;margin:18px 0 4px 0;
                          letter-spacing:-0.03em;text-shadow:0 3px 12px rgba(0,0,0,0.4);">
                {simulated_distance_km:.1f}
              </div>
              <div style="font-size:0.92rem;font-weight:700;color:rgba(255,255,255,0.92);letter-spacing:0.03em;">
                KM TO BOUNDARY · கி.மீ.
              </div>
            </div>
            <div style="background:#0f172a;padding:20px 18px;color:#f1f5f9;font-size:0.95rem;line-height:1.55;">
              <div style="font-weight:700;margin-bottom:6px;color:#f8fafc;font-size:1.05rem;">
                {style['tamil_sub']}
              </div>
              <div style="color:#cbd5e1;font-size:0.9rem;">
                {style['message']}
              </div>
            </div>
            <div style="background:#090d16;padding:12px 18px;color:#94a3b8;font-size:0.75rem;
                        line-height:1.45;border-top:1px solid rgba(255,255,255,0.06);text-align:center;">
              DEMO ONLY — approximate boundary, not surveyed coordinates. Not for navigation.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")
st.info(
    "🔒 **This app is separate from the coast guard dashboard on purpose.** "
    "It carries only the boundary — never vessel positions, patrol locations, "
    "or alerts. A crew should be warned, not watched."
)
