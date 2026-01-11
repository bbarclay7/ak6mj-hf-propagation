# Deployment Test Guide

Step-by-step guide to test deployment to your Digital Ocean droplet.

## Step 1: Test Locally

First verify both apps work locally:

### Flask Test (hello_web.py)

```bash
cd tools
uv run hello_web.py
```

Visit http://localhost:5000 - you should see:
- ✅ Green terminal-style page
- Server time, hostname, Python version
- Links to /health, /antenna, /wspr
- Health check returns JSON

Press Ctrl+C to stop.

### Streamlit Test (hello_streamlit.py)

```bash
cd tools
uv run streamlit run hello_streamlit.py
```

Visit http://localhost:8501 - you should see:
- ✅ Streamlit dashboard
- Tabs for Overview/WSPR/Antenna
- Interactive controls
- Sidebar with status

Press Ctrl+C to stop.

## Step 2: Set Up Deployment Config

Create deployment configuration:

```bash
cd local/deploy

# Copy templates
cp config.yaml.example config.yaml
cp secrets.env.example secrets.env

# Edit config
nano config.yaml
```

**Minimal config.yaml:**
```yaml
remote:
  host: YOUR_DROPLET_IP
  user: YOUR_USERNAME
  port: 22
  deploy_path: /home/YOUR_USERNAME/ak6mj-hf

app:
  port: 5000
  bind: 0.0.0.0  # For testing; use 127.0.0.1 with nginx
```

**Minimal secrets.env:**
```bash
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
FLASK_ENV=production
```

## Step 3: Prepare Your Droplet

SSH to your droplet and set up the environment:

```bash
# SSH to droplet
ssh YOUR_USERNAME@YOUR_DROPLET_IP

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3.10 python3-pip

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # Reload to get uv in PATH

# Create deployment directory
mkdir -p ~/ak6mj-hf
cd ~/ak6mj-hf

# Test uv works
uv --version
```

## Step 4: Manual Test Deployment

Let's manually deploy the hello_web.py first to test:

### On Your Local Machine:

```bash
# From wspr/ directory
cd /Users/bb/Sync/work/AK6MJ/wspr

# Manual sync (replace with your droplet info)
rsync -avz \
  --exclude='.git' \
  --exclude='local/' \
  --exclude='tests/' \
  lib/ tools/ \
  YOUR_USERNAME@YOUR_DROPLET_IP:~/ak6mj-hf/

# Copy secrets
scp local/deploy/secrets.env YOUR_USERNAME@YOUR_DROPLET_IP:~/ak6mj-hf/.env
```

### On Your Droplet:

```bash
cd ~/ak6mj-hf/tools

# Load environment
set -a
source ../.env
set +a

# Run Flask test
uv run hello_web.py
```

You should see:
```
Starting AK6MJ HF Tools (Hello World)
Listening on http://0.0.0.0:5000
Debug mode: False
```

### Test from Local Machine:

```bash
# Test from your Mac
curl http://YOUR_DROPLET_IP:5000/health
```

You should get JSON:
```json
{
  "status": "ok",
  "service": "ak6mj-hf-tools",
  "callsign": "AK6MJ",
  ...
}
```

Also visit in browser: `http://YOUR_DROPLET_IP:5000`

Press Ctrl+C on droplet to stop.

## Step 5: Set Up Systemd Service

Create a systemd service for persistent running:

### On Droplet:

```bash
# Create service file
sudo nano /etc/systemd/system/hf-hello.service
```

**Content:**
```ini
[Unit]
Description=AK6MJ HF Hello World Test
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/ak6mj-hf/tools
EnvironmentFile=/home/YOUR_USERNAME/ak6mj-hf/.env
ExecStart=/home/YOUR_USERNAME/.local/bin/uv run hello_web.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable hf-hello
sudo systemctl start hf-hello

# Check status
sudo systemctl status hf-hello

# View logs
sudo journalctl -u hf-hello -f
```

Test: `curl http://YOUR_DROPLET_IP:5000/health`

## Step 6: Test Automated Deployment

Now test the deploy.sh script:

### On Local Machine:

```bash
cd /Users/bb/Sync/work/AK6MJ/wspr

# Edit deploy script to use hf-hello service
# (We'll update it next)

# For now, just test rsync works
./scripts/deploy.sh
```

## Step 7: Set Up Nginx (Optional but Recommended)

For production with HTTPS:

### On Droplet:

```bash
sudo apt install -y nginx

# Create nginx config
sudo nano /etc/nginx/sites-available/hf-tools
```

**Content:**
```nginx
server {
    listen 80;
    server_name YOUR_DROPLET_IP;  # Or yourdomain.com

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable:**
```bash
sudo ln -s /etc/nginx/sites-available/hf-tools /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Update app to bind to localhost
# Edit ~/ak6mj-hf/.env:
# Change bind in config to 127.0.0.1
sudo systemctl restart hf-hello
```

Test: `curl http://YOUR_DROPLET_IP/health`

## Step 8: Set Up Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (for later)
sudo ufw enable
sudo ufw status
```

## Step 9: Test Streamlit (Optional)

Streamlit runs on port 8501 by default:

```bash
# On droplet
cd ~/ak6mj-hf/tools
uv run streamlit run hello_streamlit.py --server.port 8501 --server.address 0.0.0.0
```

Visit: `http://YOUR_DROPLET_IP:8501`

**For production with systemd:**
```ini
# /etc/systemd/system/hf-streamlit.service
[Unit]
Description=AK6MJ HF Streamlit Dashboard
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/ak6mj-hf/tools
EnvironmentFile=/home/YOUR_USERNAME/ak6mj-hf/.env
ExecStart=/home/YOUR_USERNAME/.local/bin/uv run streamlit run hello_streamlit.py --server.port 8501 --server.address 127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
```

**Add nginx location:**
```nginx
    location /streamlit/ {
        proxy_pass http://127.0.0.1:8501/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u hf-hello -n 50

# Check if port is in use
sudo lsof -i :5000

# Test command manually
cd ~/ak6mj-hf/tools
uv run hello_web.py
```

### Can't Connect from Browser

```bash
# Check firewall
sudo ufw status

# Check service is listening
sudo netstat -tlnp | grep 5000

# Check nginx
sudo nginx -t
sudo systemctl status nginx
```

### Deployment Script Fails

```bash
# Test SSH manually
ssh YOUR_USERNAME@YOUR_DROPLET_IP

# Test rsync
rsync -avz --dry-run tools/ YOUR_USERNAME@YOUR_DROPLET_IP:~/ak6mj-hf/tools/

# Check SSH config
cat local/deploy/config.yaml
```

## Success Criteria

✅ Local Flask app works: `uv run tools/hello_web.py`
✅ Local Streamlit works: `uv run streamlit run tools/hello_streamlit.py`
✅ Can SSH to droplet
✅ Can manually rsync files
✅ Flask app runs on droplet
✅ Health endpoint returns JSON: `curl http://DROPLET/health`
✅ Can view page in browser
✅ Systemd service starts on boot
✅ Nginx proxies requests (optional)
✅ Deployment script works

## Next Steps

Once hello world works:
1. Deploy actual antenna_web.py
2. Set up HTTPS with Let's Encrypt
3. Add authentication if needed
4. Set up monitoring/alerts
