#!/usr/bin/env -S uv run
# -*- mode: python; -*-
# vim: set ft=python:
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "flask",
# ]
# ///
"""
Web interface for antenna comparison experiments - with proper proxy prefix support.

Run with: uv run antenna_web.py
Access at: http://localhost:5000 or behind proxy at https://www.shoeph.one/hf/
"""

from flask import Flask, Blueprint, render_template, request, jsonify, redirect, url_for, send_file
from datetime import datetime, timezone
from werkzeug.middleware.proxy_fix import ProxyFix
from pathlib import Path
import json
import os

import antenna

# Determine if running behind proxy at /hf/
# URL_PREFIX is used on the blueprint so Flask generates correct URLs
# Proxy must preserve the path (ProxyPass /hf http://127.0.0.1:5000/hf)
URL_PREFIX = os.getenv('URL_PREFIX', '')

app = Flask(__name__)

# Support running behind reverse proxy
if URL_PREFIX:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Create blueprint with URL prefix for correct URL generation
bp = Blueprint('main', __name__, url_prefix=URL_PREFIX)

# Default test plan based on rybtest.md
DEFAULT_PLAN = {
    "bands": ["20m", "15m", "10m"],
    "duration_minutes": 5,
    "pattern": "alternate",  # A@20, B@20, A@15, B@15, ...
}


# ============================================================
# HTML Routes
# ============================================================

@bp.route("/")
def index():
    """Dashboard / home page."""
    status = antenna.get_session_status()
    antennas = antenna.get_antennas()
    solar = antenna.fetch_solar_data()
    comparisons = antenna.list_comparisons()[:5]  # Recent 5
    return render_template("dashboard.html",
                           status=status,
                           antennas=antennas,
                           solar=solar,
                           comparisons=comparisons)


@bp.route("/antennas")
def antennas_page():
    """Antenna management page."""
    antennas = antenna.get_antennas()
    return render_template("antennas.html", antennas=antennas)


@bp.route("/experiment")
def experiment_page():
    """Experiment execution page."""
    status = antenna.get_session_status()
    antennas = antenna.get_antennas()
    solar = antenna.fetch_solar_data()
    return render_template("experiment.html",
                           status=status,
                           antennas=antennas,
                           solar=solar,
                           default_plan=DEFAULT_PLAN)


@bp.route("/analysis/<comparison_id>")
def analysis_page(comparison_id):
    """View analysis results."""
    comparison = antenna.get_comparison(comparison_id)
    if not comparison:
        return "Comparison not found", 404
    return render_template("analysis.html", comparison=comparison)


@bp.route("/comparisons")
def comparisons_page():
    """List all comparisons."""
    comparisons = antenna.list_comparisons()
    return render_template("comparisons.html", comparisons=comparisons)


@bp.route("/wspr")
def wspr_page():
    """WSPR beacon monitoring dashboard."""
    return render_template("wspr.html")


@bp.route("/wspr/compare")
def wspr_compare_page():
    """WSPR antenna comparison dashboard."""
    return render_template("wspr_compare.html")


# ============================================================
# API Routes
# ============================================================

@bp.route("/api/status")
def api_status():
    """Get current session status."""
    return jsonify(antenna.get_session_status())


@bp.route("/api/antennas", methods=["GET"])
def api_antennas_list():
    """List all antennas."""
    return jsonify(antenna.get_antennas())


@bp.route("/api/antennas", methods=["POST"])
def api_antennas_create():
    """Create a new antenna."""
    data = request.json
    label = data.get("label", "").strip()
    description = data.get("description", "").strip()

    if not label or not description:
        return jsonify({"error": "Label and description required"}), 400

    antennas = antenna.load_json(antenna.ANTENNAS_FILE)
    is_update = label in antennas
    antennas[label] = {
        "description": description,
        "created": antennas.get(label, {}).get("created", datetime.now(timezone.utc).isoformat()),
        "updated": datetime.now(timezone.utc).isoformat(),
    }
    antenna.save_json(antenna.ANTENNAS_FILE, antennas)

    return jsonify({
        "success": True,
        "action": "updated" if is_update else "created",
        "label": label,
    })


@bp.route("/api/antennas/<label>", methods=["DELETE"])
def api_antennas_delete(label):
    """Delete an antenna."""
    antennas = antenna.load_json(antenna.ANTENNAS_FILE)
    if label not in antennas:
        return jsonify({"error": "Antenna not found"}), 404

    del antennas[label]
    antenna.save_json(antenna.ANTENNAS_FILE, antennas)
    return jsonify({"success": True, "deleted": label})


@bp.route("/api/start", methods=["POST"])
def api_start():
    """Start a new session."""
    status = antenna.get_session_status()
    if status["active"]:
        return jsonify({"error": "Session already active"}), 400

    solar = antenna.fetch_solar_data()
    solar_summary = None
    if solar:
        solar_summary = {
            "sfi": solar.get("solarflux", "?"),
            "k": solar.get("kindex", "?"),
            "a": solar.get("aindex", "?"),
            "geomagfield": solar.get("geomagfield", "?"),
        }

    log = antenna.load_json(antenna.ANTENNA_LOG_FILE)
    if not isinstance(log, list):
        log = []

    entry = {
        "event": "start",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if solar_summary:
        entry["solar"] = solar_summary

    log.append(entry)
    antenna.save_json(antenna.ANTENNA_LOG_FILE, log)

    return jsonify({"success": True, "entry": entry})


@bp.route("/api/stop", methods=["POST"])
def api_stop():
    """Stop the current session."""
    status = antenna.get_session_status()
    if not status["active"]:
        return jsonify({"error": "No active session"}), 400

    log = antenna.load_json(antenna.ANTENNA_LOG_FILE)
    entry = {
        "event": "stop",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(entry)
    antenna.save_json(antenna.ANTENNA_LOG_FILE, log)

    return jsonify({"success": True, "entry": entry})


@bp.route("/api/pause", methods=["POST"])
def api_pause():
    """Pause the current session."""
    status = antenna.get_session_status()
    if not status["active"]:
        return jsonify({"error": "No active session"}), 400
    if status["paused"]:
        return jsonify({"error": "Already paused"}), 400

    log = antenna.load_json(antenna.ANTENNA_LOG_FILE)
    entry = {
        "event": "pause",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(entry)
    antenna.save_json(antenna.ANTENNA_LOG_FILE, log)

    return jsonify({"success": True, "entry": entry})


@bp.route("/api/resume", methods=["POST"])
def api_resume():
    """Resume a paused session."""
    status = antenna.get_session_status()
    if not status["active"]:
        return jsonify({"error": "No active session"}), 400
    if not status["paused"]:
        return jsonify({"error": "Session not paused"}), 400

    log = antenna.load_json(antenna.ANTENNA_LOG_FILE)
    entry = {
        "event": "resume",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(entry)
    antenna.save_json(antenna.ANTENNA_LOG_FILE, log)

    return jsonify({"success": True, "entry": entry})


@bp.route("/api/use", methods=["POST"])
def api_use():
    """Switch to an antenna (optionally with band)."""
    status = antenna.get_session_status()
    if not status["active"]:
        return jsonify({"error": "No active session"}), 400

    data = request.json
    label = data.get("antenna")
    band = data.get("band")

    antennas = antenna.get_antennas()
    if label not in antennas:
        return jsonify({"error": f"Unknown antenna: {label}"}), 400

    band_switched = False
    if band:
        band_switched = antenna.switch_band(band)

    log = antenna.load_json(antenna.ANTENNA_LOG_FILE)
    entry = {
        "event": "use",
        "antenna": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": antennas[label]["description"],
    }
    if band:
        entry["band"] = band

    log.append(entry)
    antenna.save_json(antenna.ANTENNA_LOG_FILE, log)

    return jsonify({
        "success": True,
        "entry": entry,
        "band_switched": band_switched,
        "paused": status["paused"],
    })


@bp.route("/api/preview")
def api_preview():
    """Get live preview of data collected so far."""
    grid = request.args.get("grid", "CM98kq")
    return jsonify(antenna.get_live_preview(grid))


@bp.route("/api/solar")
def api_solar():
    """Get current solar conditions."""
    solar = antenna.fetch_solar_data()
    if not solar:
        return jsonify({"error": "Could not fetch solar data"}), 503
    return jsonify(solar)


@bp.route("/api/comparisons")
def api_comparisons():
    """List all comparisons."""
    return jsonify(antenna.list_comparisons())


@bp.route("/api/comparisons/<comparison_id>")
def api_comparison(comparison_id):
    """Get details of a comparison."""
    comp = antenna.get_comparison(comparison_id)
    if not comp:
        return jsonify({"error": "Not found"}), 404
    return jsonify(comp)


@bp.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Run analysis on current session."""
    data = request.json or {}
    grid = data.get("grid", "CM98kq")

    try:
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        antenna.cmd_analyze(grid)

        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        comparisons = antenna.list_comparisons()
        latest = comparisons[0] if comparisons else None

        return jsonify({
            "success": True,
            "output": output,
            "comparison_id": latest["id"] if latest else None,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/wsjtx/switch", methods=["POST"])
def api_wsjtx_switch():
    """Switch WSJT-X band configuration."""
    data = request.json
    band = data.get("band")
    if not band:
        return jsonify({"error": "Band required"}), 400

    success = antenna.switch_band(band)
    return jsonify({"success": success, "band": band})


@bp.route("/api/clear", methods=["POST"])
def api_clear():
    """Clear the session log."""
    antenna.save_json(antenna.ANTENNA_LOG_FILE, [])
    return jsonify({"success": True})


@bp.route("/api/wspr/spots")
def api_wspr_spots():
    """Get recent WSPR spots from PSKReporter."""
    spots_file = Path("/var/www/local/wspr-data/spots.json")

    # Check local dev fallback
    if not spots_file.exists():
        spots_file = Path.home() / "wspr-data" / "spots.json"

    if spots_file.exists():
        return send_file(spots_file, mimetype='application/json')

    return jsonify({
        "callsign": "AK6MJ",
        "tx_grid": None,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "spots": []
    })


@bp.route("/api/wspr/beacon")
def api_wspr_beacon():
    """Get current WSPR beacon status (band, frequency, etc)."""
    status_file = Path("/var/www/local/wspr-data/beacon_status.json")

    # Check local dev fallback
    if not status_file.exists():
        status_file = Path.home() / "work/ak6mj-hf-propagation/local/wspr-data/beacon_status.json"

    if status_file.exists():
        try:
            data = json.loads(status_file.read_text())
            # Check if status is stale (more than 30 min old)
            last_updated = datetime.fromisoformat(data.get("last_updated", "").replace("Z", "+00:00"))
            age_minutes = (datetime.now(timezone.utc) - last_updated).total_seconds() / 60
            data["stale"] = age_minutes > 30
            data["age_minutes"] = round(age_minutes, 1)
            return jsonify(data)
        except (json.JSONDecodeError, ValueError) as e:
            return jsonify({
                "status": "error",
                "error": f"Failed to parse beacon status: {e}"
            })

    return jsonify({
        "status": "unknown",
        "band": None,
        "error": "Beacon status file not found"
    })


@bp.route("/api/wspr/compare")
def api_wspr_compare():
    """Get WSPR antenna comparison data from wspr.live."""
    import urllib.request
    from collections import defaultdict

    # Antenna switch time: Jan 25 4pm PST = Jan 26 00:00 UTC
    SWITCH_TIME = datetime(2026, 1, 26, 0, 0, 0, tzinfo=timezone.utc)

    # Query wspr.live for historical data
    url = "http://db1.wspr.live/?query=SELECT%20time,%20band,%20snr,%20distance,%20rx_sign,%20azimuth%20FROM%20wspr.rx%20WHERE%20tx_sign%20%3D%20%27AK6MJ%27%20AND%20time%20%3E%3D%20%272026-01-12%27%20ORDER%20BY%20time%20FORMAT%20JSON"

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch from wspr.live: {e}"}), 500

    spots = data.get("data", [])

    # Split by antenna
    ant_80ef1 = []
    ant_ryb = []
    for s in spots:
        ts = datetime.strptime(s["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        s["_hour"] = ts.hour
        if ts < SWITCH_TIME:
            ant_80ef1.append(s)
        else:
            ant_ryb.append(s)

    # Time-match: only compare same hours
    ryb_hours = set(s["_hour"] for s in ant_ryb) if ant_ryb else set()
    ant_80ef1_matched = [s for s in ant_80ef1 if s["_hour"] in ryb_hours]

    def summarize_by_band(spots):
        by_band = defaultdict(lambda: {"snrs": [], "dists": [], "reporters": set()})
        for s in spots:
            b = by_band[s["band"]]
            b["snrs"].append(s["snr"])
            b["dists"].append(s["distance"])
            b["reporters"].add(s["rx_sign"])
        result = {}
        for band, data in by_band.items():
            result[band] = {
                "avg_snr": sum(data["snrs"]) / len(data["snrs"]) if data["snrs"] else None,
                "max_dist": max(data["dists"]) if data["dists"] else 0,
                "spots": len(data["snrs"]),
                "reporters": len(data["reporters"])
            }
        return result

    def direction_bucket(azimuth):
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((azimuth + 22.5) / 45) % 8
        return dirs[idx]

    def summarize_by_direction(spots, band_filter=None):
        by_dir = defaultdict(list)
        for s in spots:
            if band_filter and s["band"] != band_filter:
                continue
            by_dir[direction_bucket(s["azimuth"])].append(s["snr"])
        return {d: sum(snrs)/len(snrs) if snrs else None for d, snrs in by_dir.items()}

    def summarize_directions_all_bands(spots):
        """Get direction analysis for all bands."""
        by_band_dir = defaultdict(lambda: defaultdict(list))
        for s in spots:
            by_band_dir[s["band"]][direction_bucket(s["azimuth"])].append(s["snr"])
        result = {}
        for band, dirs in by_band_dir.items():
            result[band] = {d: sum(snrs)/len(snrs) if snrs else None for d, snrs in dirs.items()}
        return result

    # Get time ranges
    times_80ef1 = [s["time"] for s in ant_80ef1]
    times_ryb = [s["time"] for s in ant_ryb]

    return jsonify({
        "generated": datetime.now(timezone.utc).isoformat(),
        "switch_time": SWITCH_TIME.isoformat(),
        "antennas": {
            "80ef1": {
                "description": "80m EFHW with 49:1 unun, vertical to 30', wire WSW/NNW",
                "total_spots": len(ant_80ef1),
                "matched_spots": len(ant_80ef1_matched),
                "time_range": [min(times_80ef1), max(times_80ef1)] if times_80ef1 else None,
                "by_band": summarize_by_band(ant_80ef1_matched),
                "by_direction": summarize_directions_all_bands(ant_80ef1_matched)
            },
            "ryb": {
                "description": "Rybakov 25ft vertical whip, 4:1 unun",
                "total_spots": len(ant_ryb),
                "matched_spots": len(ant_ryb),
                "time_range": [min(times_ryb), max(times_ryb)] if times_ryb else None,
                "by_band": summarize_by_band(ant_ryb),
                "by_direction": summarize_directions_all_bands(ant_ryb)
            }
        },
        "comparison_note": "Time-matched comparison (same UTC hours only) to reduce propagation bias"
    })


@bp.route("/api/wspr/antenna", methods=["GET"])
def api_wspr_antenna_get():
    """Get current WSPR antenna."""
    antenna_file = Path("/var/www/local/wspr-data/current_antenna.json")

    # Check local dev fallback
    if not antenna_file.exists():
        antenna_file = Path.home() / "wspr-data" / "current_antenna.json"

    if antenna_file.exists():
        return send_file(antenna_file, mimetype='application/json')

    return jsonify({
        "antenna": None,
        "description": None,
        "last_updated": None,
        "notes": "No antenna configured"
    })


@bp.route("/api/wspr/antenna", methods=["POST"])
def api_wspr_antenna_set():
    """Set current WSPR antenna."""
    data = request.json
    antenna_label = data.get("antenna")

    if not antenna_label:
        return jsonify({"error": "Antenna label required"}), 400

    # Get antenna details from antennas list
    antennas = antenna.get_antennas()
    if antenna_label not in antennas:
        return jsonify({"error": f"Unknown antenna: {antenna_label}"}), 400

    antenna_info = antennas[antenna_label]

    # Save to wspr-data directory
    antenna_file = Path("/var/www/local/wspr-data/current_antenna.json")
    antenna_file.parent.mkdir(parents=True, exist_ok=True)

    wspr_antenna = {
        "antenna": antenna_label,
        "description": antenna_info["description"],
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "notes": data.get("notes", "")
    }

    antenna_file.write_text(json.dumps(wspr_antenna, indent=2))

    return jsonify({
        "success": True,
        "antenna": wspr_antenna
    })


@bp.route("/health")
def health():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "ok",
        "service": "antenna-web",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


# Register blueprint
app.register_blueprint(bp)

# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    print("Starting Antenna Comparison Web UI...")
    if URL_PREFIX:
        print(f"URL Prefix: {URL_PREFIX}")
        print(f"Access at: http://localhost:{port}{URL_PREFIX}/")
    else:
        print(f"Access at: http://localhost:{port}/")
    print("Or from other devices: http://<your-ip>:{port}/")
    app.run(host="0.0.0.0", port=port, debug=True)
