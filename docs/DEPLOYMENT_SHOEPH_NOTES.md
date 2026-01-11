# shoeph.one Deployment Notes

Quick reference for managing HF tools deployment on shoeph.one (www via lighthouse).

## Server Access

```bash
# Direct access (using ProxyJump from ~/.ssh/config)
ssh www

# From your Mac, www is accessible as:
# - ssh www (via ProxyJump through lighthouse)
# - rsync ... www:/path/  (also uses ProxyJump)
```

## Apache Configuration

**Config file:** `/etc/apache2/sites-available/shoeph.one-le-ssl.conf`

**Backup before changes:**
```bash
ssh www 'cp /etc/apache2/sites-available/shoeph.one-le-ssl.conf /etc/apache2/sites-available/shoeph.one-le-ssl.conf.backup'
```

**HF Tools proxy section (added):**
```apache
# HF Tools proxy configuration
<Location /hf>
    ProxyPass http://127.0.0.1:5000/
    ProxyPassReverse http://127.0.0.1:5000/
</Location>
```

**Test and reload Apache:**
```bash
ssh www 'apache2ctl configtest'
ssh www 'systemctl reload apache2'
```

**View Apache logs:**
```bash
ssh www 'tail -f /var/log/apache2/error.log'
ssh www 'tail -f /var/log/apache2/access.log'
```

## Flask Application

**Location:** `/var/www/hf-tools/`

**Manual start/stop:**
```bash
# Start in background
ssh www 'cd /var/www/hf-tools && nohup /root/.local/bin/uv run hello_web.py > /var/log/hf-hello.log 2>&1 &'

# Stop
ssh www 'pkill -f hello_web.py'

# Check if running
ssh www 'ps aux | grep hello_web'

# View logs
ssh www 'tail -f /var/log/hf-hello.log'
```

**Test locally on server:**
```bash
ssh www 'curl http://localhost:5000/health'
```

**Test through Apache:**
```bash
curl -sk https://shoeph.one/hf/health
```

## Systemd Service (Future - Not Yet Configured)

To make it start on boot, create `/etc/systemd/system/hf-hello.service`:

```ini
[Unit]
Description=AK6MJ HF Hello World
After=network.target apache2.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/hf-tools
ExecStart=/root/.local/bin/uv run hello_web.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/hf-hello.log
StandardError=append:/var/log/hf-hello.log

[Install]
WantedBy=multi-user.target
```

Then:
```bash
ssh www 'systemctl daemon-reload'
ssh www 'systemctl enable hf-hello'
ssh www 'systemctl start hf-hello'
ssh www 'systemctl status hf-hello'
```

## Deployment from Mac

**Manual deployment:**
```bash
# From /Users/bb/Sync/work/AK6MJ/wspr
rsync -avz \
  --exclude='.git' \
  --exclude='local/' \
  --exclude='tests/' \
  lib/ tools/ \
  www:/var/www/hf-tools/

# Restart app
ssh www 'pkill -f hello_web.py'
ssh www 'cd /var/www/hf-tools && nohup /root/.local/bin/uv run hello_web.py > /var/log/hf-hello.log 2>&1 &'
```

**Automated deployment (once configured):**
```bash
./scripts/deploy.sh
```

## URLs

- **Main page:** https://shoeph.one/hf/
- **Health check:** https://shoeph.one/hf/health
- **Antenna tools:** https://shoeph.one/hf/antenna (placeholder)
- **WSPR control:** https://shoeph.one/hf/wspr (placeholder)

## Troubleshooting

### App not responding

```bash
# Check if Flask is running
ssh www 'ps aux | grep hello_web'

# Check if port 5000 is listening
ssh www 'netstat -tlnp | grep 5000'

# View Flask logs
ssh www 'tail -50 /var/log/hf-hello.log'

# Restart manually
ssh www 'pkill -f hello_web.py && cd /var/www/hf-tools && nohup /root/.local/bin/uv run hello_web.py > /var/log/hf-hello.log 2>&1 &'
```

### Apache proxy not working

```bash
# Check Apache is running
ssh www 'systemctl status apache2'

# Test Apache syntax
ssh www 'apache2ctl configtest'

# View Apache error log
ssh www 'tail -50 /var/log/apache2/error.log'

# Check proxy modules enabled
ssh www 'apache2ctl -M | grep proxy'
```

### Can't access from browser

```bash
# Test from server itself
ssh www 'curl http://localhost:5000/health'

# Test Apache proxy from server
ssh www 'curl http://localhost/hf/health'

# Test externally (should work)
curl -sk https://shoeph.one/hf/health

# Check firewall (probably not the issue since Apache works)
ssh www 'ufw status'
```

### Need to rollback Apache config

```bash
# Restore backup
ssh www 'cp /etc/apache2/sites-available/shoeph.one-le-ssl.conf.backup /etc/apache2/sites-available/shoeph.one-le-ssl.conf'

# Reload
ssh www 'systemctl reload apache2'
```

## Quick Commands Reference

```bash
# Deploy code
rsync -avz tools/hello_web.py www:/var/www/hf-tools/

# Restart app
ssh www 'pkill -f hello_web.py && cd /var/www/hf-tools && nohup /root/.local/bin/uv run hello_web.py > /var/log/hf-hello.log 2>&1 &'

# Check health
curl -sk https://shoeph.one/hf/health

# View logs
ssh www 'tail -f /var/log/hf-hello.log'

# Check Apache config
ssh www 'apache2ctl configtest'

# Reload Apache
ssh www 'systemctl reload apache2'
```

## Server Environment

- **OS:** Debian 12 (Bookworm)
- **Python:** 3.11.2
- **uv:** 0.9.24 (installed at /root/.local/bin/uv)
- **Apache:** 2.x with mod_proxy, mod_proxy_http, mod_ssl
- **rsync:** 3.2.7
- **Working directory:** /var/www/hf-tools/
- **Log file:** /var/log/hf-hello.log

## Security Notes

- Currently running as root (not ideal for production)
- No authentication on /hf/ endpoints (add if needed)
- SSL/TLS handled by Apache (Let's Encrypt cert for shoeph.one)
- Flask app binds to 127.0.0.1:5000 (not exposed to internet)
- Only accessible via Apache reverse proxy

## Future Improvements

- [ ] Create dedicated user for Flask app (not root)
- [ ] Set up systemd service for auto-start on boot
- [ ] Add basic auth or other authentication to /hf/ location
- [ ] Set up proper logging rotation
- [ ] Add monitoring/health checks
- [ ] Deploy full antenna_web.py instead of hello_web.py
- [ ] Add Streamlit dashboard at /hf-dash/
