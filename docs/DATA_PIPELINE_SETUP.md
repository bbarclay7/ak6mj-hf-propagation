# Data Pipeline Setup: hamtop1 → www

Quick setup checklist for FT8 data pipeline.

## Current Status

- ✅ Web interface operational at https://shoeph.one/hf/
- ✅ antenna.py library expects ALL.TXT data
- ⏳ SSH access to hamtop1 WSL2 (needs setup)
- ⏳ Automated data sync (needs setup)

## Architecture

```
hamtop1 (Windows + WSL2)
  ├─ WSJT-X writes to: C:\Users\admin\AppData\Local\WSJT-X\ALL.TXT
  ├─ WSL2 sees as: /mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT
  ├─ SSH server in WSL2 (port 22 → Windows port 2222)
  └─ Tailscale IP: 100.116.44.83

           ↓ rsync over SSH every 15 min

www.shoeph.one
  ├─ Receives: /var/www/local/ft8-tools/ALL.TXT
  ├─ antenna_web.py reads data
  └─ Analysis results viewable at /hf/
```

## Setup Steps

### 1. Enable SSH on hamtop1 (15 minutes)

Follow `HAMTOP1_SSH_SETUP.md` steps 1-7:

**Quick version**:
```bash
# On hamtop1 WSL2
sudo apt install -y openssh-server
sudo service ssh start

# On hamtop1 Windows PowerShell (as Admin)
$wslIP = (wsl hostname -I).Trim()
netsh interface portproxy add v4tov4 listenport=2222 listenaddress=0.0.0.0 connectport=22 connectaddress=$wslIP
New-NetFirewallRule -DisplayName "WSL2 SSH" -Direction Inbound -LocalPort 2222 -Protocol TCP -Action Allow

# Test from www
ssh -p 2222 admin@100.116.44.83
```

### 2. Configure SSH Keys (5 minutes)

```bash
# On www
ssh-keygen -t ed25519 -C "www-to-hamtop1"
ssh-copy-id -p 2222 admin@100.116.44.83

# Add to ~/.ssh/config
cat >> ~/.ssh/config <<'EOF'
Host hamtop1
    HostName 100.116.44.83
    Port 2222
    User admin
    IdentityFile ~/.ssh/id_ed25519
    Compression yes
EOF

# Test
ssh hamtop1 'ls /mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT'
```

### 3. Test Manual Sync (2 minutes)

```bash
# On www
rsync -avz hamtop1:/mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT /var/www/local/ft8-tools/
```

### 4. Deploy Sync Script (3 minutes)

```bash
# From your Mac, deploy scripts
rsync -avz scripts/ root@www:/var/www/hf-tools/scripts/

# On www, make executable
ssh root@www 'chmod +x /var/www/hf-tools/scripts/sync_from_hamtop1.sh'

# Test
ssh root@www '/var/www/hf-tools/scripts/sync_from_hamtop1.sh'
```

### 5. Set Up Cron Job (2 minutes)

```bash
# On www
ssh root@www 'crontab -e'
```

Add:
```cron
# Sync FT8 data from hamtop1 every 15 minutes
*/15 * * * * /var/www/hf-tools/scripts/sync_from_hamtop1.sh >> /var/log/ft8-sync.log 2>&1
```

### 6. Verify Everything Works (5 minutes)

```bash
# Check hamtop1 is reachable
ssh root@www 'ssh hamtop1 hostname'

# Check ALL.TXT exists on hamtop1
ssh root@www 'ssh hamtop1 "ls -lh /mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT"'

# Check sync runs
ssh root@www '/var/www/hf-tools/scripts/sync_from_hamtop1.sh'

# Check file arrived
ssh root@www 'ls -lh /var/www/local/ft8-tools/ALL.TXT'

# Wait 15 minutes, check cron ran
ssh root@www 'tail -20 /var/log/ft8-sync.log'

# Check from web interface
curl -sk https://shoeph.one/hf/ | grep -i "antenna"
```

## Troubleshooting

### hamtop1 appears offline in tailscale

- Check tailscale is running on Windows: `tailscale status`
- Restart tailscale service if needed

### Can't SSH to hamtop1

- Verify SSH server running in WSL2: `wsl sudo service ssh status`
- Check port forwarding: `netsh interface portproxy show all`
- Test locally first: `ssh -p 2222 admin@localhost` (from Windows)
- Check Windows Firewall allows port 2222

### rsync fails with "connection refused"

- Tailscale IP may have changed - check `tailscale ip -4`
- Update ~/.ssh/config on www with new IP

### rsync fails with "no such file"

- Verify path in WSL2: `wsl ls /mnt/c/Users/admin/AppData/Local/WSJT-X/`
- WSJT-X may not be installed or path different

### Cron job not running

- Check cron logs: `grep CRON /var/log/syslog`
- Check ft8-sync logs: `tail -f /var/log/ft8-sync.log`
- Verify script is executable: `ls -l /var/www/hf-tools/scripts/sync_from_hamtop1.sh`

## Monitoring

### Check sync status

```bash
# On www
tail -f /var/log/ft8-sync.log

# Or via journalctl
journalctl -t ft8-sync -f

# Check last sync time
ssh root@www 'stat /var/www/local/ft8-tools/ALL.TXT' | grep Modify
```

### Manual sync trigger

```bash
ssh root@www '/var/www/hf-tools/scripts/sync_from_hamtop1.sh'
```

## Next Steps

Once data pipeline is working:
1. Test antenna comparison workflow end-to-end
2. Add monitoring/alerting for sync failures
3. Consider bidirectional sync for analysis results
4. Document analysis workflows in web interface
