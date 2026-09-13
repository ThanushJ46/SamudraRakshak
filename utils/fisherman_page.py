"""
fisherman_page.py
-----------------
Builds the file the FISHERMAN takes to sea.

Why a file and not a web page: out on the water there is no network. But GPS
only RECEIVES - it needs no signal at all - so a phone still knows exactly
where it is. This builds a single self-contained HTML file with the boundary
baked into it and NO external resources: no map tiles, no CDN, no fonts, no
API calls. The geofence itself therefore needs no network at all.

ONE HONEST LIMITATION: phone browsers only grant geolocation to pages from a
secure origin (https or localhost), so opening this file straight off the
filesystem will NOT get a GPS fix - Chrome refuses with "only secure origins
are allowed". Shipping this for real means packaging it as an installable PWA,
which is cached and served from a secure origin and does work offline. What is
finished here is the logic and the boundary maths; the packaging is not.

That matters because of the awkward truth in this whole project: the boat we
most want to warn is the one that has gone dark, and a dark boat is the one
the shore station can least reach. A warning that lives on the boat does not
depend on the boat broadcasting anything.

    from utils.fisherman_page import build_offline_alert_page
    html = build_offline_alert_page()

APPROXIMATE BOUNDARY - demonstration only. Not for navigation.
"""

import json

# Deliberately from zone_utils, NOT gfw_client: the fisherman's app must
# not import the surveillance client or anything that reads the API token.
from utils.zone_utils import ILLUSTRATIVE_BOUNDARY_LINE

# How close is too close, in km. These match the shore-side thresholds in
# utils/zone_utils.py so the fisherman and the coast guard are working to the
# same numbers.
CAUTION_DISTANCE_KM = 10.0
DANGER_DISTANCE_KM = 5.0


def build_offline_alert_page() -> str:
    """
    Return a complete, standalone HTML page as a string.

    No network is used after the file is saved. The page reads GPS through the
    browser's geolocation API, works out the perpendicular distance to the
    boundary with the same maths the server uses, and shows one of three
    states.
    """
    boundary_json = json.dumps(ILLUSTRATIVE_BOUNDARY_LINE)

    return """<!DOCTYPE html>
<html lang="ta">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Samudra Rakshak - எல்லை எச்சரிக்கை</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 18px;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: #0b1220; color: #e2e8f0;
    min-height: 100vh;
  }
  h1 { font-size: 1.05rem; margin: 0 0 4px 0; font-weight: 700; }
  .sub { font-size: 0.78rem; color: #94a3b8; margin-bottom: 18px; }
  #state {
    border-radius: 16px; padding: 26px 20px; text-align: center;
    transition: background 0.3s;
  }
  #label { font-size: 1.6rem; font-weight: 800; line-height: 1.15; }
  #tamil { font-size: 1.15rem; font-weight: 700; margin-bottom: 8px; }
  #dist {
    font-size: 3.1rem; font-weight: 800; margin: 14px 0 2px 0;
    letter-spacing: -0.02em;
  }
  #distlabel { font-size: 0.8rem; opacity: 0.85; }
  .safe   { background: #14532d; }
  .caution{ background: #854d0e; }
  .danger { background: #7f1d1d; }
  .unknown{ background: #1e293b; }
  #msg {
    margin-top: 16px; padding: 14px; border-radius: 12px;
    background: #111c2e; border: 1px solid #1e2d47;
    font-size: 0.92rem; line-height: 1.5;
  }
  #pos { margin-top: 14px; font-size: 0.74rem; color: #64748b; }
  .note {
    margin-top: 18px; padding: 11px; border-radius: 10px;
    background: #1c1917; border: 1px solid #44403c;
    font-size: 0.72rem; color: #a8a29e; line-height: 1.45;
  }
  button {
    width: 100%; margin-top: 14px; padding: 13px;
    border: 0; border-radius: 12px; background: #0891b2; color: white;
    font-size: 0.95rem; font-weight: 700;
  }
</style>
</head>
<body>

<h1>🌊 Samudra Rakshak</h1>
<div class="sub">எல்லை எச்சரிக்கை · Boundary alert · GPS only, no network</div>

<div id="state" class="unknown">
  <div id="tamil">GPS தேடுகிறது…</div>
  <div id="label">Searching for GPS</div>
  <div id="dist">--</div>
  <div id="distlabel">km from boundary · எல்லையிலிருந்து கி.மீ.</div>
</div>

<div id="msg">Allow location access to begin. இருப்பிடத்தை அனுமதிக்கவும்.</div>
<div id="pos"></div>

<button onclick="startWatching()">Start / மீண்டும் தொடங்கு</button>

<div class="note">
  <b>DEMO ONLY.</b> The boundary in this file is approximate and is not
  surveyed or legal maritime boundary data. Do not use for navigation.
  இது ஒரு மாதிரி செயலி மட்டுமே; வழிசெலுத்தலுக்குப் பயன்படுத்த வேண்டாம்.
  <br><br>
  If GPS is refused, this file was opened straight from disk - phone browsers
  only give location to an installed app or a secure origin. The distance
  maths here needs no network; the packaging does.
</div>

<script>
// The boundary, baked in when this file was generated. No network needed.
var BOUNDARY = __BOUNDARY__;
var CAUTION_KM = __CAUTION__;
var DANGER_KM = __DANGER__;

var KM_PER_DEG_LAT = 110.57;

// Same maths as utils/zone_utils.py: flatten to kilometres, then take the
// perpendicular distance from the point to the line through the two ends.
function distanceToBoundaryKm(lat, lon) {
  var a = BOUNDARY[0], b = BOUNDARY[1];
  var refLat = (a.lat + b.lat) / 2;
  var kmPerDegLon = 111.32 * Math.cos(refLat * Math.PI / 180);

  var px = lon * kmPerDegLon,       py = lat * KM_PER_DEG_LAT;
  var ax = a.lon * kmPerDegLon,     ay = a.lat * KM_PER_DEG_LAT;
  var bx = b.lon * kmPerDegLon,     by = b.lat * KM_PER_DEG_LAT;

  var dx = bx - ax, dy = by - ay;
  var len = Math.sqrt(dx * dx + dy * dy);
  if (len === 0) { return Math.sqrt((px-ax)*(px-ax) + (py-ay)*(py-ay)); }

  var cross = dx * (py - ay) - dy * (px - ax);
  return Math.abs(cross) / len;
}

// Positive cross product means west of the line, which is our side.
function onOurSide(lat, lon) {
  var a = BOUNDARY[0], b = BOUNDARY[1];
  var cross = (b.lon - a.lon) * (lat - a.lat) - (b.lat - a.lat) * (lon - a.lon);
  return cross >= 0;
}

function render(lat, lon) {
  var km = distanceToBoundaryKm(lat, lon);
  var ours = onOurSide(lat, lon);

  var state = document.getElementById('state');
  var tamil = document.getElementById('tamil');
  var label = document.getElementById('label');
  var msg   = document.getElementById('msg');

  document.getElementById('dist').textContent = km.toFixed(1);
  document.getElementById('pos').textContent =
    'Position ' + lat.toFixed(4) + ', ' + lon.toFixed(4) +
    (ours ? ' · Indian side' : ' · across the boundary');

  if (!ours) {
    state.className = 'danger';
    tamil.textContent = 'நீங்கள் எல்லையைக் கடந்துவிட்டீர்கள்!';
    label.textContent = 'YOU HAVE CROSSED';
    msg.innerHTML = '<b>உடனே திரும்பவும்.</b> வடக்கு நோக்கி இந்திய ' +
      'கடல் பகுதிக்குத் திரும்பவும்.<br><br><b>Turn back immediately.</b> ' +
      'Head north into Indian waters.';
  } else if (km < DANGER_KM) {
    state.className = 'danger';
    tamil.textContent = 'எல்லைக்கு மிக அருகில்!';
    label.textContent = 'TOO CLOSE - TURN BACK';
    msg.innerHTML = 'நீங்கள் எல்லையிலிருந்து ' + km.toFixed(1) +
      ' கி.மீ. தொலைவில் மட்டுமே உள்ளீர்கள். திரும்பவும்.<br><br>' +
      'You are only ' + km.toFixed(1) + ' km from the boundary. Turn back.';
  } else if (km < CAUTION_KM) {
    state.className = 'caution';
    tamil.textContent = 'எச்சரிக்கை';
    label.textContent = 'CAUTION';
    msg.innerHTML = 'எல்லை ' + km.toFixed(1) + ' கி.மீ. தொலைவில் உள்ளது. ' +
      'கவனமாக இருங்கள்.<br><br>Boundary is ' + km.toFixed(1) +
      ' km away. Stay alert and keep your AIS on.';
  } else {
    state.className = 'safe';
    tamil.textContent = 'பாதுகாப்பாக உள்ளீர்கள்';
    label.textContent = 'SAFE';
    msg.innerHTML = 'எல்லையிலிருந்து ' + km.toFixed(1) +
      ' கி.மீ. தொலைவில் உள்ளீர்கள்.<br><br>You are ' + km.toFixed(1) +
      ' km from the boundary. Good fishing.';
  }
}

function startWatching() {
  if (!navigator.geolocation) {
    document.getElementById('msg').textContent =
      'This device cannot provide GPS.';
    return;
  }
  navigator.geolocation.watchPosition(
    function (p) { render(p.coords.latitude, p.coords.longitude); },
    function (e) {
      document.getElementById('msg').textContent =
        'Could not read GPS (' + e.message + '). Tap Start to retry.';
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 }
  );
}

startWatching();
</script>
</body>
</html>
""".replace("__BOUNDARY__", boundary_json) \
   .replace("__CAUTION__", str(CAUTION_DISTANCE_KM)) \
   .replace("__DANGER__", str(DANGER_DISTANCE_KM))
