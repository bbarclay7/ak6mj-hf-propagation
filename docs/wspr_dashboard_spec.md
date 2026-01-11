# WSPR/FT8 Propagation Dashboard Spec

## Purpose
Answer: "Is now exceptional? What's open? Should I grab the antenna?"
Alert when new DXCC/grids available on bands you need.

## User Context
- Callsign: AK6MJ
- Grid: CM98 (Folsom, CA)
- WSPR beacon: 40m, 200mW, 24/7 unattended
- FT8 operating: All bands (80/40 night, 20/17/15/12/10 day)
- Goal: Chase new DXCCs and grids per band

## Inputs

### 1. PSKReporter API
- Poll every 15 minutes
- Query: `https://retrieve.pskreporter.info/query?senderCallsign=AK6MJ&flowStartSeconds=-7200`
- Returns XML with `<receptionReport>` elements
- Captures both WSPR and FT8 spots (mode field distinguishes)
- Key fields: receiverCallsign, receiverLocator, frequency, flowStartSeconds, mode, sNR

### 2. WSJT-X Log (ADIF)
- Poll every 5 minutes
- Path: `/mnt/c/Users/Brandon/AppData/Local/WSJT-X/wsjtx_log.adi` (configurable)
- Parse for worked QSOs to track needed DXCC/grid per band

## Storage (SQLite)

```sql
-- Raw PSKReporter spots
CREATE TABLE spots (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER,           -- flowStartSeconds
    receiver_call TEXT,
    receiver_grid TEXT,
    receiver_dxcc TEXT,
    frequency INTEGER,
    band TEXT,                   -- derived from frequency
    mode TEXT,                   -- WSPR or FT8
    snr INTEGER,
    distance_km INTEGER,         -- calculated from grids
    azimuth INTEGER,             -- degrees from CM98
    UNIQUE(timestamp, receiver_call, frequency)
);

-- Parsed QSOs from wsjtx_log.adi
CREATE TABLE worked (
    id INTEGER PRIMARY KEY,
    call TEXT,
    grid TEXT,
    dxcc TEXT,
    band TEXT,
    mode TEXT,
    timestamp INTEGER,
    UNIQUE(call, band, mode)
);

-- Derived: DXCC confirmed per band
CREATE TABLE worked_dxcc_band (
    dxcc TEXT,
    band TEXT,
    first_call TEXT,
    first_timestamp INTEGER,
    UNIQUE(dxcc, band)
);

-- Derived: Grid (4-char) confirmed per band
CREATE TABLE worked_grid_band (
    grid TEXT,
    band TEXT,
    first_call TEXT,
    first_timestamp INTEGER,
    UNIQUE(grid, band)
);

-- Hourly rollup for trends/baselines
CREATE TABLE hourly_stats (
    date TEXT,                   -- YYYY-MM-DD
    hour_utc INTEGER,            -- 0-23
    band TEXT,
    spot_count INTEGER,
    unique_receivers INTEGER,
    unique_grids INTEGER,
    unique_dxcc INTEGER,
    min_snr INTEGER,
    max_snr INTEGER,
    avg_snr REAL,
    max_distance_km INTEGER,
    furthest_call TEXT,
    furthest_grid TEXT,
    UNIQUE(date, hour_utc, band)
);

-- Alert tracking to prevent duplicates
CREATE TABLE alerts_sent (
    id INTEGER PRIMARY KEY,
    alert_type TEXT,             -- 'dxcc' or 'grid'
    target TEXT,                 -- DXCC name or grid square
    band TEXT,
    first_spotted INTEGER,
    alerted_at INTEGER,
    UNIQUE(alert_type, target, band)
);
```

## Derived Calculations

### Band from frequency
```python
def freq_to_band(hz):
    freq_mhz = hz / 1_000_000
    if 1.8 <= freq_mhz <= 2.0: return "160m"
    elif 3.5 <= freq_mhz <= 4.0: return "80m"
    elif 7.0 <= freq_mhz <= 7.3: return "40m"
    elif 10.1 <= freq_mhz <= 10.15: return "30m"
    elif 14.0 <= freq_mhz <= 14.35: return "20m"
    elif 18.068 <= freq_mhz <= 18.168: return "17m"
    elif 21.0 <= freq_mhz <= 21.45: return "15m"
    elif 24.89 <= freq_mhz <= 24.99: return "12m"
    elif 28.0 <= freq_mhz <= 29.7: return "10m"
    return "unknown"
```

### Distance and azimuth from grid squares
- Use Maidenhead grid to lat/lon conversion
- Haversine formula for distance
- Calculate azimuth from CM98 to receiver grid

## CLI Tools

### wspr_ingest.py
```
wspr_ingest.py --db ~/wspr.db [--lookback 7200] [--verbose]
```
- Fetch PSKReporter, insert new spots
- Update hourly_stats rollup
- Check for alert conditions, send if warranted
- Exit 0 on success, suitable for cron

### wspr_log_sync.py
```
wspr_log_sync.py --db ~/wspr.db --log /path/to/wsjtx_log.adi [--verbose]
```
- Parse ADIF log
- Update worked, worked_dxcc_band, worked_grid_band tables

### Cron setup
```
*/15 * * * * /path/to/wspr_ingest.py --db ~/wspr.db
*/5  * * * * /path/to/wspr_log_sync.py --db ~/wspr.db --log /mnt/c/Users/Brandon/AppData/Local/WSJT-X/wsjtx_log.adi
```

## Dashboard (Streamlit)

### wspr_dashboard.py
```
streamlit run wspr_dashboard.py -- --db ~/wspr.db
```

### Panels

#### 1. Right Now (last 2 hours)
- Total spots, unique grids, unique DXCCs
- Best DX: callsign, grid, distance, SNR

#### 2. Band Scoreboard
```
40m: ████████░░ 18 spots, 12 grids, best DX: 9200km (CN2AA)
20m: ██░░░░░░░░  4 spots,  3 grids, best DX: 4100km (W1AW)
```

#### 3. Azimuthal Summary
```
NE (0-60°):    Europe      ████ 8 spots, -12 dB avg
E  (60-120°):  Japan       █░░░ 2 spots, -24 dB avg
SE (120-180°): Pacific     ░░░░ quiet
S  (180-240°): S. America  ░░░░ quiet
SW (240-300°): Africa      ██░░ 3 spots, -19 dB avg
NW (300-360°): Alaska      █░░░ 1 spot
```

#### 4. Conditions One-liner (auto-generated)
- "40m: EU/Africa open, Pacific quiet. Spotty but some DX."
- "20m: Domestic only. Poor conditions."
- "Wide open! Spots on 5 continents."
- "Band appears dead."

Logic:
- spot_count < 3 → "Band appears dead"
- spots clustered in one azimuth → "[Region] open, rest quiet"
- spots spread across 4+ azimuth bins → "Wide open"

#### 5. Recent Spots Table
- Last 20 spots
- Columns: Time (UTC), Call, Grid, DXCC, Band, Mode, SNR, Distance
- Highlight rows where DXCC or grid is needed

#### 6. Needed Highlight
- Flag spots where DXCC/band not in worked_dxcc_band
- Flag spots where grid/band not in worked_grid_band

## Alerts (Pushover)

### Configuration
```yaml
pushover_token: "app_token_here"
pushover_user: "uvreenf2ag41xvgutmv66hp5bpk9vg"
```

### Alert Types

#### New DXCC/band needed
- Trigger: DXCC spotted that's not in worked_dxcc_band for that band
- Consistency filter: At least 2 spots spanning 30+ minutes
- Throttle: Once per DXCC/band until worked
- Message: "🎯 South Africa on 20m - ZS6ABC, ZS1A heard over 45 min. Best SNR: -12"

#### New grids/band needed
- Trigger: Grid spotted that's not in worked_grid_band for that band
- Consistency filter: At least 2 spots spanning 30+ minutes
- Throttle: Batched summary every 2 hours
- Message: "📍 3 new grids on 20m: KG33 (ZS6ABC), JN48 (DL1ABC), PM95 (JA1XYZ)"

### Alert Schedule

| Day | Time | Mode |
|-----|------|------|
| Mon-Fri | 00:00-08:00 | Silent |
| Mon-Fri | 08:00-18:00 | High bar (normal for now, tunable later) |
| Mon-Fri | 18:00-24:00 | Normal |
| Sat-Sun | 00:00-08:00 | Silent |
| Sat-Sun | 08:00-24:00 | Normal |

### Pushover send function
```python
import requests

def notify(title, message, url=None):
    requests.post('https://api.pushover.net/1/messages.json', data={
        'token': PUSHOVER_APP_TOKEN,
        'user': PUSHOVER_USER_KEY,
        'title': title,
        'message': message,
        'url': url
    })
```

## Configuration File

`~/.config/wspr-dashboard/config.yaml`
```yaml
callsign: AK6MJ
grid: CM98
log_path: /mnt/c/Users/Brandon/AppData/Local/WSJT-X/wsjtx_log.adi
db_path: ~/wspr.db

pushover:
  token: "app_token_here"
  user: "user_key_here"

ingest:
  lookback_seconds: 7200
  poll_interval_minutes: 15

log_sync:
  poll_interval_minutes: 5

alerts:
  consistency_minutes: 30
  grid_batch_hours: 2
  quiet_hours:
    start: 0   # midnight
    end: 8     # 8am
  work_hours:
    start: 8
    end: 18
    weekdays_only: true
    high_bar: false  # toggle for stricter filtering later
```

## Future Enhancements (not in v1)
- Azimuthal map visualization (colored wedges)
- Baseline comparisons ("2.5x typical for this hour")
- Similar day pattern matching
- Solar index correlation (NOAA data)
- Web-888 RX integration
- Automated antenna switching
