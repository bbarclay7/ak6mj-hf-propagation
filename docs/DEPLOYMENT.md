# Deployment Strategy

This document covers deploying the web-based tools (antenna_web.py, future unified dashboard) to both local and remote environments.

## Overview

The codebase supports two deployment modes:
1. **Local Development** - Run tools on your local machine for testing/development
2. **Remote Deployment** - Deploy to Digital Ocean droplet for public access

Deployment credentials and server-specific config are kept in `local/deploy/` (gitignored).

## Directory Structure

```
wspr/
├── tools/
│   ├── antenna_web.py       # Flask app
│   └── ...
├── local/                    # Gitignored
│   ├── deploy/
│   │   ├── config.yaml      # Deployment configuration
│   │   ├── ssh_config       # SSH connection details
│   │   └── secrets.env      # Environment variables
│   └── ...
├── scripts/
│   └── deploy.sh            # Deployment script
└── docs/
    └── DEPLOYMENT.md        # This file
```

## Local Development

### Running Locally

```bash
# Start antenna web interface
cd tools
uv run antenna_web.py

# Access at http://localhost:5000
```

### Local Configuration

Tools read from `local/config/config.yaml` (gitignored):
```yaml
callsign: AK6MJ
grid: CM98kq
power: 23
# Local settings
```

## Remote Deployment

### Prerequisites

1. **Digital Ocean Droplet** running Ubuntu/Debian
2. **SSH access** configured
3. **Python 3.10+** and `uv` installed on server
4. **Reverse proxy** (nginx/caddy) for HTTPS (optional but recommended)

### Deployment Configuration

Create `local/deploy/config.yaml`:
```yaml
# Remote server configuration
remote:
  host: your-droplet-ip
  user: deploy-user
  port: 22
  deploy_path: /var/www/ak6mj-hf

# Application settings
app:
  port: 5000
  bind: 127.0.0.1  # Use reverse proxy
  workers: 2

# Which tools to deploy
tools:
  - antenna_web
  - future_dashboard
```

Create `local/deploy/ssh_config`:
```
Host hf-droplet
    HostName your-droplet-ip
    User deploy-user
    Port 22
    IdentityFile ~/.ssh/id_rsa_hf_deploy
    # Or use existing key
```

Create `local/deploy/secrets.env` (for app secrets):
```bash
# Flask secret key
SECRET_KEY=generate-random-secret-here

# Optional: API keys for services
PSKREPORTER_API_KEY=optional
QRZCQ_USERNAME=optional
QRZCQ_PASSWORD=optional
```

### Deployment Script

Create `scripts/deploy.sh`:
```bash
#!/usr/bin/env bash
set -e

DEPLOY_CONFIG="local/deploy/config.yaml"
REMOTE_HOST="hf-droplet"  # From ssh_config
REMOTE_PATH="/var/www/ak6mj-hf"

echo "Deploying to $REMOTE_HOST:$REMOTE_PATH"

# Sync code (excluding local/, tests/, docs/)
rsync -avz \
  --exclude='.git' \
  --exclude='local/' \
  --exclude='tests/' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  lib/ tools/ scripts/ \
  ${REMOTE_HOST}:${REMOTE_PATH}/

# Copy secrets
scp local/deploy/secrets.env ${REMOTE_HOST}:${REMOTE_PATH}/.env

# Restart service
ssh ${REMOTE_HOST} "cd ${REMOTE_PATH} && ./scripts/restart.sh"

echo "Deployment complete!"
```

### Server Setup

On your Digital Ocean droplet:

```bash
# Install dependencies
sudo apt update
sudo apt install -y python3.10 python3-pip nginx

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create deployment directory
sudo mkdir -p /var/www/ak6mj-hf
sudo chown $USER:$USER /var/www/ak6mj-hf

# Create systemd service
sudo nano /etc/systemd/system/antenna-web.service
```

**systemd service** (`/etc/systemd/system/antenna-web.service`):
```ini
[Unit]
Description=AK6MJ Antenna Web Interface
After=network.target

[Service]
Type=simple
User=deploy-user
WorkingDirectory=/var/www/ak6mj-hf/tools
EnvironmentFile=/var/www/ak6mj-hf/.env
ExecStart=/home/deploy-user/.local/bin/uv run antenna_web.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable antenna-web
sudo systemctl start antenna-web
```

### Nginx Reverse Proxy

Create `/etc/nginx/sites-available/hf-tools`:
```nginx
server {
    listen 80;
    server_name hf.yourdomain.com;  # Or use IP

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/hf-tools /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### HTTPS with Let's Encrypt (Optional)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d hf.yourdomain.com
```

## Deployment Workflow

### Initial Setup

1. Create deployment config in `local/deploy/`:
   ```bash
   mkdir -p local/deploy
   nano local/deploy/config.yaml
   nano local/deploy/ssh_config
   nano local/deploy/secrets.env
   ```

2. Set up server (one-time):
   ```bash
   ssh your-droplet-ip
   # Follow "Server Setup" above
   ```

3. Make deploy script executable:
   ```bash
   chmod +x scripts/deploy.sh
   ```

### Deploy Updates

```bash
# Deploy latest code
./scripts/deploy.sh

# Or manually:
rsync -avz --exclude='local/' tools/ hf-droplet:/var/www/ak6mj-hf/tools/
ssh hf-droplet 'sudo systemctl restart antenna-web'
```

## Security Considerations

1. **Secrets Management**
   - Never commit `local/deploy/` to git (it's gitignored)
   - Use SSH keys instead of passwords
   - Generate strong `SECRET_KEY` for Flask
   - Consider using environment variables on server

2. **Firewall**
   ```bash
   # On droplet
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

3. **HTTPS**
   - Always use HTTPS for public deployment
   - Let's Encrypt is free and automatic

4. **Authentication**
   - For public access, consider adding basic auth to nginx
   - Or implement user authentication in Flask app

## Configuration Priority

Tools load configuration in this order (first found wins):

1. Environment variables (`SECRET_KEY`, etc.)
2. `local/config/config.yaml` (local dev)
3. `/etc/ak6mj-hf/config.yaml` (system-wide on server)
4. Default built-in config

## Monitoring

### View Logs

```bash
# Systemd logs
ssh hf-droplet 'sudo journalctl -u antenna-web -f'

# Nginx logs
ssh hf-droplet 'sudo tail -f /var/log/nginx/access.log'
ssh hf-droplet 'sudo tail -f /var/log/nginx/error.log'
```

### Health Check

Add to `tools/antenna_web.py`:
```python
@app.route('/health')
def health():
    return {'status': 'ok', 'version': '1.0'}, 200
```

Monitor:
```bash
curl http://hf.yourdomain.com/health
```

## Rollback

If deployment breaks:
```bash
# SSH to server
ssh hf-droplet

# Check service status
sudo systemctl status antenna-web

# View logs
sudo journalctl -u antenna-web -n 50

# Restart service
sudo systemctl restart antenna-web

# Or restore from backup
cd /var/www/ak6mj-hf
git checkout HEAD~1  # If using git on server
sudo systemctl restart antenna-web
```

## Future: Docker Deployment

For easier deployment, consider containerization:

```dockerfile
# Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY lib/ ./lib/
COPY tools/ ./tools/
RUN pip install uv
CMD ["uv", "run", "tools/antenna_web.py"]
```

Deploy with docker-compose:
```yaml
# docker-compose.yml
services:
  antenna-web:
    build: .
    ports:
      - "127.0.0.1:5000:5000"
    env_file:
      - .env
    restart: always
```

## Summary

- **Local dev**: Just run `uv run antenna_web.py`
- **Remote deploy**: Use `./scripts/deploy.sh` with config in `local/deploy/`
- **Secrets**: Never in repo, always in `local/deploy/` (gitignored)
- **Server**: systemd service + nginx reverse proxy + Let's Encrypt
- **Updates**: rsync + systemctl restart
