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
Access at: http://localhost:5000 or behind proxy at https://shoeph.one/hf/
"""

from flask import Flask, Blueprint, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timezone
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import os

import antenna

# Determine if running behind proxy at /hf/
URL_PREFIX = os.getenv('URL_PREFIX', '')

app = Flask(__name__)

# Support running behind reverse proxy
if URL_PREFIX:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    app.config['APPLICATION_ROOT'] = URL_PREFIX

# Create blueprint with URL prefix
bp = Blueprint('antenna', __name__, url_prefix=URL_PREFIX)

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
