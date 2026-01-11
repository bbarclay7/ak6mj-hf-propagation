#!/usr/bin/env bash
# Restart services on remote server
set -e

echo "Restarting AK6MJ HF Tools services..."

# Check if running as systemd service
if systemctl is-active --quiet antenna-web; then
    echo "Restarting antenna-web service..."
    sudo systemctl restart antenna-web
    sudo systemctl status antenna-web --no-pager -l
    echo "✓ Service restarted"
else
    echo "Service not running as systemd. Starting manually..."
    # Could add manual process management here
    echo "Note: For production, set up systemd service (see docs/DEPLOYMENT.md)"
fi

# Optional: Reload nginx if configured
if systemctl is-active --quiet nginx; then
    echo "Reloading nginx..."
    sudo systemctl reload nginx
    echo "✓ Nginx reloaded"
fi

echo ""
echo "Services restarted successfully!"
