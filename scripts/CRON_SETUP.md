# WSPR Beacon Cron Setup

## Automated Band Rotation

The `wspr-cron.sh` script automatically rotates the WSPR beacon through bands based on UTC time. Runs every 2 hours for predictable, repeatable patterns.

### Band Schedule (UTC)

| UTC Hours  | Band | Notes                        |
|------------|------|------------------------------|
| 00-01      | 80m  | Night, low band propagation  |
| 02-03      | 40m  | Night, reliable DX           |
| 04-05      | 40m  | Pre-dawn, EU opens           |
| 06-07      | 30m  | Dawn transition              |
| 08-09      | 20m  | Morning, primary DX band     |
| 10-11      | 20m  | Midday, long path            |
| 12-13      | 17m  | Afternoon, higher band       |
| 14-15      | 15m  | Afternoon peak               |
| 16-17      | 20m  | Late afternoon               |
| 18-19      | 20m  | Evening, short path          |
| 20-21      | 30m  | Sunset transition            |
| 22-23      | 40m  | Night, reliable DX           |

### Installation

1. **Make script executable:**
   ```bash
   chmod +x ~/work/ak6mj-hf-propagation/scripts/wspr-cron.sh
   ```

2. **Test the script manually:**
   ```bash
   ~/work/ak6mj-hf-propagation/scripts/wspr-cron.sh
   ```

3. **Check the log:**
   ```bash
   tail -20 ~/work/ak6mj-hf-propagation/local/logs/band-rotation.log
   ```

4. **Install crontab entry:**
   ```bash
   crontab -e
   ```

   Add this line (runs at the top of every even UTC hour):
   ```cron
   0 */2 * * * $HOME/work/ak6mj-hf-propagation/scripts/wspr-cron.sh
   ```

   Or for more frequent rotation (every 90 minutes):
   ```cron
   0,30 */1 * * * $HOME/work/ak6mj-hf-propagation/scripts/wspr-cron.sh
   ```

5. **Verify crontab:**
   ```bash
   crontab -l
   ```

### Monitoring

**View rotation log:**
```bash
tail -f ~/work/ak6mj-hf-propagation/local/logs/band-rotation.log
```

**Check current band on PSKReporter:**
https://pskreporter.info/pskmap.html?callsign=AK6MJ

**Manual override:**
```bash
cd ~/work/ak6mj-hf-propagation
make 20m  # Switch to specific band
```

The cron will switch it back at the next scheduled rotation.

### Customizing the Schedule

Edit `scripts/wspr-cron.sh` and modify the `case` statement to change bands:

```bash
case $((HOUR / 2)) in
    0)  BAND="80m" ;;   # Change this to your preferred band
    1)  BAND="40m" ;;
    # ... etc
esac
```

You can also change the rotation frequency by adjusting the cron schedule:
- `0 */2 * * *` - Every 2 hours (recommended)
- `0 */4 * * *` - Every 4 hours (less frequent)
- `0 * * * *` - Every hour (more frequent, less time per band)

### Troubleshooting

**Cron not running?**
```bash
# Check if cron service is running
systemctl status cron

# Check system logs for cron errors
journalctl -u cron | tail -20
```

**Script failing?**
```bash
# Run manually to see errors
bash -x ~/work/ak6mj-hf-propagation/scripts/wspr-cron.sh
```

**Serial port busy?**
The script waits for the previous transmission to complete (~3-4 minutes). If you see "port busy" errors, the timing is working correctly - the beacon is still transmitting.

### Advanced: Seasonal Adjustment

For more sophisticated scheduling (adjusting for sunrise/sunset), you could:

1. **Use astronomical calculations:**
   - Install `sunwait` package: `sudo apt-get install sunwait`
   - Calculate sunrise/sunset in the script
   - Adjust band selection based on solar position

2. **Use external data:**
   - Query solar indices from HamQSL
   - Adjust to higher bands when SFI > 150
   - Stay on lower bands during geomagnetic storms

3. **Machine learning approach:**
   - Log PSKReporter reception reports
   - Analyze which bands/times give best results
   - Optimize schedule based on historical performance

For now, the simple UTC-based rotation provides good coverage without complexity.
