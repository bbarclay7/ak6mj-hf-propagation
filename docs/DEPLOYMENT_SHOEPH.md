# Deployment to shoeph.one (www via lighthouse)

Quick deployment guide for your specific setup: lighthouse → www (shoeph.one)

## Your Environment

- **Jump host**: lighthouse (first hop, ssh root@lighthouse)
- **Web server**: www (second hop, ssh root@www from lighthouse)
- **Domain**: shoeph.one (served by www)

## Step 1: Configure SSH ProxyJump

Add to your `~/.ssh/config`:

```ssh-config
# Jump host (first hop)
Host lighthouse
    HostName <lighthouse-ip-or-hostname>
    User root
    IdentityFile ~/.ssh/id_rsa
    Compression yes

# Web server (second hop via lighthouse)
Host www
    HostName <www-internal-ip-or-hostname>
    User root
    ProxyJump lighthouse
    IdentityFile ~/.ssh/id_rsa
    Compression yes

# Alias for deployment scripts
Host hf-deploy
    HostName <www-internal-ip>
    User root
    ProxyJump lighthouse
    IdentityFile ~/.ssh/id_rsa
```

**Test it works:**
```bash
# Should connect through lighthouse automatically
ssh www
# You should be on www now
hostname  # Should show www hostname
exit
```

## Step 2: Create Deployment Config

```bash
cd local/deploy
cp config.yaml.example config.yaml
nano config.yaml
```

**Your config.yaml:**
```yaml
remote:
  host: www  # Uses SSH config above
  user: root
  port: 22
  deploy_path: /var/www/hf-tools

app:
  port: 5000
  bind: 127.0.0.1  # nginx will proxy
```

**Create secrets.env:**
```bash
cp secrets.env.example secrets.env
python3 -c 'import secrets; print("SECRET_KEY=" + secrets.token_hex(32))' >> secrets.env
nano secrets.env  # Add any other needed vars
```

## Step 3: Prepare www Server

```bash
# Connect to www via lighthouse
ssh www

# Update system
apt update && apt upgrade -y

# Install Python 3.10+ if needed
apt install -y python3.10 python3-pip

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Create deployment directory
mkdir -p /var/www/hf-tools
cd /var/www/hf-tools

# Test uv
uv --version
```

## Step 4: Test Manual Deployment

From your local Mac:

```bash
cd /Users/bb/Sync/work/AK6MJ/wspr

# Test rsync through jump host
rsync -avz \
  --exclude='.git' \
  --exclude='local/' \
  lib/ tools/ \
  www:/var/www/hf-tools/

# Copy secrets
scp local/deploy/secrets.env www:/var/www/hf-tools/.env
```

On www:

```bash
cd /var/www/hf-tools/tools
source ../.env
uv run hello_web.py
```

Test from Mac:
```bash
# If www is publicly accessible:
curl http://shoeph.one:5000/health

# Or via SSH tunnel:
ssh -L 5000:localhost:5000 www
# Then visit http://localhost:5000 on your Mac
```

## Step 5: Set Up Systemd Service

On www:

```bash
cat > /etc/systemd/system/hf-hello.service <<'EOF'
[Unit]
Description=AK6MJ HF Hello World
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/hf-tools/tools
EnvironmentFile=/var/www/hf-tools/.env
ExecStart=/root/.local/bin/uv run hello_web.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hf-hello
systemctl start hf-hello
systemctl status hf-hello
```

## Step 6: Configure Nginx on shoeph.one

Assuming nginx already serves shoeph.one, add a location:

```bash
# On www
nano /etc/nginx/sites-available/shoeph.one
```

Add to existing server block:

```nginx
server {
    server_name shoeph.one;

    # Existing config...

    # Add HF tools
    location /hf/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /hf-health {
        proxy_pass http://127.0.0.1:5000/health;
    }
}
```

Reload nginx:
```bash
nginx -t
systemctl reload nginx
```

Test: https://shoeph.one/hf/

## Step 7: Update Deployment Script

The deployment script should work automatically with SSH config.

Test deployment:
```bash
cd /Users/bb/Sync/work/AK6MJ/wspr
./scripts/deploy.sh
```

It will:
1. Use `www` from config.yaml
2. SSH ProxyJump through lighthouse automatically
3. rsync files
4. Restart service

## Step 8: Set Up Streamlit (Optional)

For Streamlit on different URL path:

**Service:**
```bash
cat > /etc/systemd/system/hf-streamlit.service <<'EOF'
[Unit]
Description=AK6MJ HF Streamlit Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/hf-tools/tools
EnvironmentFile=/var/www/hf-tools/.env
ExecStart=/root/.local/bin/uv run streamlit run hello_streamlit.py --server.port 8501 --server.address 127.0.0.1 --server.baseUrlPath /hf-dash
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable hf-streamlit
systemctl start hf-streamlit
```

**Nginx location:**
```nginx
    location /hf-dash/ {
        proxy_pass http://127.0.0.1:8501/hf-dash/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```

Visit: https://shoeph.one/hf-dash/

## Quick Commands

```bash
# Deploy from Mac
cd /Users/bb/Sync/work/AK6MJ/wspr && ./scripts/deploy.sh

# Check status on www (from Mac)
ssh www 'systemctl status hf-hello'

# View logs
ssh www 'journalctl -u hf-hello -f'

# Restart service
ssh www 'systemctl restart hf-hello'

# Test health
curl https://shoeph.one/hf-health
```

## URLs

After deployment:
- Flask: https://shoeph.one/hf/
- Health: https://shoeph.one/hf-health
- Streamlit: https://shoeph.one/hf-dash/ (if configured)

## Troubleshooting

**SSH ProxyJump not working:**
```bash
# Test each hop
ssh lighthouse  # Should work
ssh www         # Should auto-jump through lighthouse

# Verbose mode
ssh -v www
```

**Can't connect to service:**
```bash
# On www, check if running
systemctl status hf-hello
netstat -tlnp | grep 5000

# Check nginx
nginx -t
systemctl status nginx
```

**Deployment fails:**
```bash
# Test rsync manually
rsync -avz --dry-run tools/ www:/var/www/hf-tools/tools/

# Check SSH config
cat ~/.ssh/config | grep -A10 "Host www"
```
