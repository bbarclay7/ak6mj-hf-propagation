# Rybakov vs 80m EFHW Antenna Comparison Test

## Objective
Compare performance and pattern of Rybakov 25ft telescopic whip against baseline 80m EFHW inverted-L on 20m, 15m, and 10m bands.

## Antennas
| Label | Description |
|-------|-------------|
| 80ef1 | 80m EFHW inverted-L (baseline) |
| ryb   | Rybakov 25ft telescopic whip |

---

## Test Series

**Key principle:** Alternate antennas within each band to minimize propagation drift effects and maximize common station overlap.

### 1. Start Session
```bash
python3 antenna.py start
```
This captures current solar conditions (SFI, K-index, A-index) for the record.

### 2. Band-by-Band A/B Testing

For each band, alternate between antennas. **Transmit during each interval** so PSKReporter captures TX performance alongside RX.

#### 20m Band
```bash
python3 wsjtx_control.py switch 20m

# Antenna A
python3 antenna.py use 80ef1
# TX: Call CQ or answer calls for 10 min

# Antenna B
python3 antenna.py use ryb
# TX: Call CQ or answer calls for 10 min

# (Optional) Antenna A again for more data
python3 antenna.py use 80ef1
# TX: 10 min
```

#### 15m Band
```bash
python3 wsjtx_control.py switch 15m

python3 antenna.py use 80ef1
# TX: 10 min

python3 antenna.py use ryb
# TX: 10 min
```

#### 10m Band
```bash
python3 wsjtx_control.py switch 10m

python3 antenna.py use 80ef1
# TX: 10 min

python3 antenna.py use ryb
# TX: 10 min
```

### 3. End Session
```bash
python3 antenna.py stop
```

---

## Analysis

### View Session Log
```bash
python3 antenna.py log
```

### Run Analysis
```bash
# For Folsom QTH
python3 antenna.py analyze CM98kq

# For Freeland QTH
python3 antenna.py analyze CN88ra
```

### What the Analysis Shows

**RX Analysis** (from ALL.TXT - who you heard):
1. Comparison by Band - Average SNR for stations heard by both antennas
2. Comparison by Bearing + Band - Pattern analysis by direction

**TX Analysis** (from PSKReporter - who heard you):
1. Comparison by Band - Average SNR reported by stations that heard both antennas
2. Comparison by Bearing + Band - TX pattern analysis by direction

Note: TX analysis requires transmitting during each interval and is limited to sessions within the last 24 hours (PSKReporter data retention limit).

### Interpreting Results

| Delta | Meaning |
|-------|---------|
| +3 dB | Test antenna noticeably better |
| +1-2 dB | Test antenna slightly better |
| 0 dB | No significant difference |
| -1-2 dB | Baseline slightly better |
| -3 dB | Baseline noticeably better |

Pattern differences by bearing reveal directional characteristics:
- EFHW inverted-L: expect some directivity based on wire orientation
- Rybakov vertical: expect more omnidirectional pattern

**RX vs TX differences:** If RX and TX results differ significantly, consider:
- Antenna reciprocity issues (rare but possible with ground effects)
- Local noise affecting RX but not TX
- Different propagation during RX vs TX intervals

---

## Cleanup (if needed)

Clear session data to start fresh:
```bash
python3 antenna.py clear
```

---

## Notes

- Total test time: ~60-90 min per complete cycle (both antennas, all 3 bands)
- Best results when band conditions are stable
- Check solar conditions before starting:
  ```bash
  python3 antenna.py solar
  ```
