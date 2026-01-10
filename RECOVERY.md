# WSPR Beacon Recovery Guide

## GPS Auto-Grid Reboot Loop

If your beacon is stuck in a reboot loop showing repeated "WSPR Beacon V1.06 by BG6JJI" messages, you likely configured GPS auto-grid without a GPS antenna attached.

### Symptoms
```
WSPR Beacon V1.06 by BG6JJI
WSPR Beacon V1.06 by BG6JJI
WSPR Beacon V1.06 by BG6JJI
```

The device boots, tries to get GPS lock, fails, and reboots. This continues indefinitely because the GPS auto-grid config is saved in EEPROM.

### Recovery Options

#### Option 1: Attach GPS Antenna (Recommended)
1. Power off the beacon
2. Attach the GPS antenna to the GPS connector
3. Place antenna with clear view of sky (preferably outdoors or by window)
4. Power on and wait 5-10 minutes for GPS lock
5. Once GPS locks, device should stabilize
6. Use script to switch to explicit grid: `./wspr_band.py 20m -g CM98`
7. Remove GPS antenna if desired

#### Option 2: Rapid CONFIG During Boot Window
This is tricky but possible if you're quick:

1. Monitor the serial port: `make monitor`
2. Watch for the boot message
3. Immediately after "WSPR Beacon V1.06 by BG6JJI", send a CONFIG command before next reboot
4. Use a very short timeout:
   ```bash
   # In another terminal, quickly run:
   ./wspr_band.py 20m -g CM98
   ```
5. You have about 3-6 seconds before device reboots again
6. May need multiple attempts - be ready to hit up-arrow + Enter quickly

#### Option 3: Factory Reset (If Available)
Check the device manual for factory reset instructions. Common methods:
- Hold button during power-on
- Short specific pins on the board
- Send special serial command

Consult the manual at `20251121043600wsprbeacon.pdf` for reset procedure.

### Prevention
- **Never use GPS auto-grid without GPS antenna attached**
- Default config now uses explicit grid (CM98) for safety
- Only use `grid: auto` if you have GPS antenna connected and working
- Test GPS functionality before configuring auto-grid

### Testing GPS Auto-Grid Safely
If you want to use GPS auto-grid in the future:

1. Attach GPS antenna
2. Place in location with clear sky view
3. Monitor serial output: `make monitor`
4. Wait for GPS lock indicators in serial output
5. Verify GPS is working before configuring auto-grid
6. Then use: `./wspr_band.py 20m -g auto`

## Other Recovery Scenarios

### Device Not Responding
1. Check USB cable connection
2. Verify correct serial device: `ls /dev/cu.* /dev/ttyUSB*`
3. Check if another program has port open: `lsof /dev/cu.usbserial-10`
4. Try different USB port
5. Power cycle device

### Wrong Frequency/Band
1. Monitor to see current config: `make monitor`
2. Wait for TX line showing current settings
3. Send new config with desired band: `make 20m`

### Configuration File Issues
1. Check config location: `~/.config/wspr-beacon/config.yaml`
2. Verify YAML syntax is correct
3. Use `./wspr_band.py --dump-config` to see defaults
4. Override with command-line flags to bypass config file
