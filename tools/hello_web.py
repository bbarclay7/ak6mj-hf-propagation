#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "flask",
# ]
# ///
"""
Simple Flask test app for deployment verification.
Run with: uv run hello_web.py
"""

from flask import Flask, render_template_string
import os
from datetime import datetime

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AK6MJ HF Tools - Hello World</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #1a1a1a;
            color: #00ff00;
        }
        h1 {
            border-bottom: 2px solid #00ff00;
            padding-bottom: 10px;
        }
        .status { color: #00ff00; }
        .info { margin: 20px 0; }
        .code {
            background: #000;
            padding: 10px;
            border-left: 3px solid #00ff00;
            margin: 10px 0;
        }
        a {
            color: #00ffff;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>✓ AK6MJ HF Propagation Tools</h1>

    <div class="info">
        <p><strong>Status:</strong> <span class="status">Online</span></p>
        <p><strong>Server Time:</strong> {{ server_time }}</p>
        <p><strong>Callsign:</strong> AK6MJ</p>
        <p><strong>Grid:</strong> CM98kq (Folsom, CA)</p>
    </div>

    <h2>Deployment Info</h2>
    <div class="code">
        <p>Environment: {{ env }}</p>
        <p>Python Version: {{ python_version }}</p>
        <p>Host: {{ hostname }}</p>
    </div>

    <h2>Available Services</h2>
    <ul>
        <li><a href="/health">Health Check</a> - Service health status</li>
        <li><a href="/antenna">Antenna Tools</a> - Coming soon</li>
        <li><a href="/wspr">WSPR Beacon Control</a> - Coming soon</li>
    </ul>

    <h2>Quick Test</h2>
    <div class="info">
        <p>This page confirms your deployment is working!</p>
        <p>Next steps:</p>
        <ol>
            <li>Verify HTTPS is working (if configured)</li>
            <li>Test health endpoint: <code>curl {{ base_url }}/health</code></li>
            <li>Deploy full antenna_web.py</li>
        </ol>
    </div>

    <hr>
    <p style="text-align: center; color: #666;">
        🤖 Generated at {{ server_time }}<br>
        <a href="https://github.com/bbarclay7/ak6mj-hf-propagation">GitHub Repo</a>
    </p>
</body>
</html>
"""

@app.route('/')
def index():
    import sys
    import socket

    return render_template_string(
        HTML_TEMPLATE,
        server_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        env=os.getenv('FLASK_ENV', 'production'),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        hostname=socket.gethostname(),
        base_url=os.getenv('BASE_URL', 'http://localhost:5000')
    )

@app.route('/health')
def health():
    return {
        'status': 'ok',
        'service': 'ak6mj-hf-tools',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'callsign': 'AK6MJ',
        'grid': 'CM98kq'
    }, 200

@app.route('/antenna')
def antenna():
    return render_template_string("""
        <html><body style="font-family: monospace; background: #1a1a1a; color: #00ff00; padding: 50px;">
        <h1>Antenna Tools</h1>
        <p>Coming soon - antenna comparison and analysis</p>
        <p><a href="/" style="color: #00ffff;">Back to home</a></p>
        </body></html>
    """)

@app.route('/wspr')
def wspr():
    return render_template_string("""
        <html><body style="font-family: monospace; background: #1a1a1a; color: #00ff00; padding: 50px;">
        <h1>WSPR Beacon Control</h1>
        <p>Coming soon - remote beacon control</p>
        <p><a href="/" style="color: #00ffff;">Back to home</a></p>
        </body></html>
    """)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'

    print(f"Starting AK6MJ HF Tools (Hello World)")
    print(f"Listening on http://0.0.0.0:{port}")
    print(f"Debug mode: {debug}")

    app.run(host='0.0.0.0', port=port, debug=debug)
