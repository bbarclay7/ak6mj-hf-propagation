# WSPR Beacon Cron Setup

## Automated Band Rotation

The `wspr-cron.sh` script automatically rotates the WSPR beacon through bands based on UTC time. Runs every 2 hours for predictable, repeatable patterns.

### Band Schedule (UTC)

Optimized for CM98kq (Folsom, CA) winter propagation during solar maximum. PST = UTC-8.

| UTC Hours  | Band | Local Time (PST) | Notes                                    |
|------------|------|------------------|------------------------------------------|
| 00-01      | 40m  | 4-5pm PST        | Sunset transition, 40m opens             |
| 02-03      | 40m  | 6-7pm PST        | Evening, reliable DX                     |
| 04-05      | 40m  | 8-9pm PST        | Night                                    |
| 06-07      | 80m  | 10-11pm PST      | Late night, 80m opens                    |
| 08-09      | 80m  | 12-1am PST       | Graveyard shift, EU gray line            |
| 10-11      | 80m  | 2-3am PST        | Deep night, best 80m                     |
| 12-13      | 40m  | 4-5am PST        | Pre-dawn                                 |
| 14-15      | 40m  | 6-7am PST        | Sunrise, EU/Asia                         |
| 16-17      | 20m  | 8-9am PST        | Morning, 20m opens                       |
| 18-19      | 15m  | 10-11am PST      | 15m peak (solar max, best antenna perf)  |
| 20-21      | 15m  | 12-1pm PST       | Midday, 15m wide open                    |
| 22-23      | 10m  | 2-3pm PST        | Afternoon, 10m good at solar max         |

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

**Seasonal Adjustments:**

The current schedule is optimized for winter solar maximum. As conditions change:

- **Spring/Summer** (longer days, later sunset ~8pm):
  - Shift higher bands (15m/10m) later: 00-05 UTC (4-9pm PST)
  - Move 40m/80m earlier to catch pre-dawn hours
  - Consider 20m for late afternoon (20-23 UTC = 12-3pm)

- **Fall** (earlier sunset ~5pm, similar to winter):
  - Keep current schedule mostly intact
  - May shift 80m earlier as nights lengthen

- **Solar Minimum** (2029-2031):
  - Replace 15m/10m daytime slots with 20m/17m
  - Increase 40m coverage during day
  - Add 30m for daytime NVIS and regional contacts

**Edit the schedule:**

```bash
# Edit scripts/wspr-cron.sh
case $((HOUR / 2)) in
    0)  BAND="40m" ;;   # Change to your preferred band
    1)  BAND="40m" ;;
    # ... etc
esac
```

**Change rotation frequency:**
- `0 */2 * * *` - Every 2 hours (current, recommended)
- `0 */4 * * *` - Every 4 hours (less frequent, more time per band)
- `0 * * * *` - Every hour (more frequent, less coverage per band)
- `0,30 */1 * * *` - Every 90 minutes (compromise)

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
