# Setting Up SSH Access to hamtop1 WSL2

Guide for enabling SSH access to WSL2 on hamtop1 (Windows) from www server.

## Overview

WSL2 runs in a Hyper-V VM with NAT networking. To access it remotely:
1. Install SSH server in WSL2
2. Forward Windows port to WSL2
3. Configure Windows Firewall
4. Access via tailscale IP

## Step 1: Install SSH Server in WSL2 (on hamtop1)

Open WSL2 terminal on hamtop1:

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install OpenSSH server
sudo apt install -y openssh-server

# Configure SSH
sudo nano /etc/ssh/sshd_config
```

**Key settings in sshd_config**:
```
Port 22
PermitRootLogin no
PasswordAuthentication yes          # Or 'no' if using keys only
PubkeyAuthentication yes
X11Forwarding no
```

**Start and enable SSH**:
```bash
# Start SSH service
sudo service ssh start

# Check status
sudo service ssh status

# Get WSL2 IP address
ip addr show eth0 | grep "inet "
```

You should see something like `172.x.x.x` - this is your WSL2 IP.

## Step 2: Configure SSH to Start on Boot

WSL2 doesn't use systemd by default, so SSH won't start automatically.

**Option A: WSL2 systemd (Ubuntu 22.04+)**
```bash
# Edit /etc/wsl.conf
sudo nano /etc/wsl.conf
```

Add:
```ini
[boot]
systemd=true
```

Then restart WSL2 from PowerShell:
```powershell
wsl --shutdown
wsl
```

Now enable SSH:
```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

**Option B: Manual start script (if systemd not available)**

Create Windows startup script to start SSH when WSL2 starts.

## Step 3: Configure Port Forwarding (Windows side)

On hamtop1, open PowerShell **as Administrator**:

```powershell
# Get WSL2 IP address
wsl hostname -I

# Example: 172.25.240.155
$wslIP = "172.25.240.155"  # Replace with actual IP from above

# Forward Windows port 2222 to WSL2 port 22
netsh interface portproxy add v4tov4 listenport=2222 listenaddress=0.0.0.0 connectport=22 connectaddress=$wslIP

# Verify
netsh interface portproxy show all
```

**Important**: WSL2 IP changes on restart! For permanent solution:
- Use the script below to auto-update port forwarding

## Step 4: Configure Windows Firewall

Still in PowerShell as Administrator:

```powershell
# Allow inbound SSH on port 2222
New-NetFirewallRule -DisplayName "WSL2 SSH" -Direction Inbound -LocalPort 2222 -Protocol TCP -Action Allow

# Verify rule exists
Get-NetFirewallRule -DisplayName "WSL2 SSH"
```

## Step 5: Auto-Update Port Forwarding on Boot

WSL2's IP changes on reboot. Create a script to update port forwarding automatically.

**Create** `C:\Scripts\wsl2-ssh-forward.ps1`:

```powershell
# Get WSL2 IP address
$wslIP = (wsl hostname -I).Trim()

Write-Host "WSL2 IP: $wslIP"

# Remove old rule if exists
netsh interface portproxy delete v4tov4 listenport=2222 listenaddress=0.0.0.0

# Add new rule
netsh interface portproxy add v4tov4 listenport=2222 listenaddress=0.0.0.0 connectport=22 connectaddress=$wslIP

Write-Host "Port forwarding updated: 0.0.0.0:2222 -> $wslIP:22"

# Start SSH in WSL2 if not running
wsl sudo service ssh start
```

**Schedule via Task Scheduler**:
1. Open Task Scheduler
2. Create Task:
   - Name: "WSL2 SSH Port Forward"
   - Trigger: At startup
   - Action: Run program
     - Program: `powershell.exe`
     - Arguments: `-ExecutionPolicy Bypass -File C:\Scripts\wsl2-ssh-forward.ps1`
   - Run with highest privileges: Yes

## Step 6: Set Up SSH Keys (Recommended)

On www server:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "www-to-hamtop1"

# Copy public key to clipboard
cat ~/.ssh/id_ed25519.pub
```

On hamtop1 WSL2:

```bash
# Create .ssh directory if it doesn't exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add www server's public key
nano ~/.ssh/authorized_keys
# Paste the public key from www

# Set permissions
chmod 600 ~/.ssh/authorized_keys
```

## Step 7: Test Connection from www

Get hamtop1's tailscale IP:

```bash
# On hamtop1 (Windows PowerShell or WSL2)
tailscale ip -4
```

From www server:

```bash
# Test connection (use port 2222)
ssh -p 2222 <username>@<hamtop1-tailscale-ip>

# Example:
ssh -p 2222 <username>@<hamtop1-tailscale-ip>
```

If successful, add to SSH config on www:

```bash
# Edit ~/.ssh/config
nano ~/.ssh/config
```

Add:
```ssh-config
Host hamtop1
    HostName <hamtop1-tailscale-ip>
    Port 2222
    User <username>            # Your WSL2 username
    IdentityFile ~/.ssh/id_ed25519
    Compression yes
```

Now you can simply: `ssh hamtop1`

## Step 8: Set Up Automated Data Pull

Once SSH works, create a cron job on www to pull ALL.TXT:

```bash
# On www server
crontab -e
```

Add:
```cron
# Sync FT8 data from hamtop1 every 15 minutes
*/15 * * * * rsync -avz hamtop1:/mnt/c/Users/<username>/AppData/Local/WSJT-X/ALL.TXT /var/www/local/ft8-tools/ 2>&1 | logger -t ft8-sync
```

Or use a dedicated sync script (see below).

## Troubleshooting

### Can't connect to WSL2 SSH

1. Check SSH is running in WSL2:
   ```bash
   sudo service ssh status
   ```

2. Check WSL2 IP hasn't changed:
   ```bash
   ip addr show eth0 | grep "inet "
   ```

3. Verify port forwarding:
   ```powershell
   netsh interface portproxy show all
   ```

4. Check Windows firewall:
   ```powershell
   Get-NetFirewallRule -DisplayName "WSL2 SSH"
   ```

5. Test locally first from Windows:
   ```powershell
   ssh -p 2222 <username>@localhost
   ```

### Connection times out from www

- Verify tailscale is running on hamtop1 (Windows)
- Check Windows Firewall allows tailscale traffic
- Try pinging hamtop1 from www: `ping <hamtop1-tailscale-ip>`

### WSL2 IP keeps changing

- This is normal on Windows restart
- Use the PowerShell auto-update script
- Or use Windows Task Scheduler to run the script on boot

## Alternative: Access via Windows SSH Server

If WSL2 SSH is too complex, you could:
1. Install OpenSSH Server on Windows (Settings → Apps → Optional Features)
2. Access Windows SSH (port 22)
3. Use `wsl` command to run WSL2 commands

This avoids port forwarding but requires extra `wsl` wrapper.

## Next Steps

Once SSH is working:
1. Test rsync from www to hamtop1
2. Create automated sync script
3. Set up monitoring/alerts for sync failures
