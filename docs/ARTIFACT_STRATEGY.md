# Artifact Management Strategy

## Problem

The tools generate various artifacts that shouldn't be checked into git but need to be preserved and managed:

1. **Antenna comparison results** - `comparison_YYYYMMDD_HHMMSS/` directories
2. **State/session files** - `antenna_log.json`, `antennas.json`
3. **ADIF log files** - WSJT-X logs (symlinked from Windows)
4. **SQLite databases** - `wspr.db` (future dashboard)
5. **Generated reports** - Analysis outputs, charts

These artifacts are:
- Coupled to the automation (tools create/read them)
- Valuable data (don't want to lose them)
- Machine/user-specific (not portable across installs)
- Sometimes large (comparison dirs with all raw data)

## Current .gitignore Coverage

```gitignore
# Already ignored:
*.db                    # SQLite databases ✓
config.yaml             # User configs ✓
*.log                   # Log files ✓
*.tmp                   # Temp files ✓

# NOT ignored yet:
comparison_*/           # Antenna comparison artifacts ✗
antenna_log.json        # Antenna usage log ✗
antennas.json           # Antenna definitions ✗
*.adi                   # ADIF log files ✗
```

## Proposed Strategy

### 1. Single `local/` Directory (RECOMMENDED)

Keep all user-generated artifacts in a single top-level `local/` directory:

```
~/Sync/work/AK6MJ/wspr/      # Git repo
├── local/                    # All user artifacts (gitignored)
│   ├── comparisons/          # Antenna comparison results
│   │   ├── comparison_20251214_150935/
│   │   ├── comparison_20251215_083022/
│   │   └── ...
│   ├── logs/                 # Logs and databases
│   │   ├── wsjtx_log.adi -> /mnt/c/Users/admin/AppData/Local/WSJT-X/wsjtx_log.adi
│   │   ├── ALL.TXT -> /mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT
│   │   └── wspr.db
│   ├── state/                # State files
│   │   ├── antenna_log.json
│   │   └── antennas.json
│   └── config/               # User configs
│       └── config.yaml
├── .gitignore                # Ignores local/
└── ... (source code)
```

**Advantages:**
- ✓ Simple and discoverable (single location for all artifacts)
- ✓ No external symlinks to manage
- ✓ Easy to backup (`rsync local/`)
- ✓ Easy to .gitignore (single line: `local/`)
- ✓ Stays with repo (good for Sync folders)
- ✓ Clear convention (like `node_modules/`, `target/`, etc.)

**Implementation:**
```bash
# One-time setup
mkdir -p local/{comparisons,logs,state,config}

# Symlink WSJT-X logs (WSL2 → Windows)
ln -s /mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT local/logs/
ln -s /mnt/c/Users/admin/AppData/Local/WSJT-X/wsjtx_log.adi local/logs/
```

### 2. Update .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.pytest_cache/

# Virtual environments
venv/
env/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# User artifacts directory
local/

# Legacy artifacts (for migration period, remove after cleanup)
comparison_*/
antenna_log.json
antennas.json

# Test artifacts
tests/fixtures/generated_*
coverage.xml
.coverage
htmlcov/
```

**Note:** With `local/` directory, we don't need individual patterns for `*.db`, `*.adi`, `config.yaml`, etc. since they'll all be inside `local/` which is fully ignored.

### 3. Code Updates for Artifact Paths

Update tools to use `local/` directory:

**Before (antenna.py):**
```python
DATA_DIR = Path(__file__).parent
ANTENNAS_FILE = DATA_DIR / "antennas.json"
ANTENNA_LOG_FILE = DATA_DIR / "antenna_log.json"
ALL_TXT = Path("/mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT")
```

**After (antenna.py):**
```python
REPO_DIR = Path(__file__).parent
LOCAL_DIR = REPO_DIR / "local"

# Auto-create local/ subdirectories if needed
(LOCAL_DIR / "state").mkdir(parents=True, exist_ok=True)
(LOCAL_DIR / "comparisons").mkdir(parents=True, exist_ok=True)
(LOCAL_DIR / "logs").mkdir(parents=True, exist_ok=True)

ANTENNAS_FILE = LOCAL_DIR / "state" / "antennas.json"
ANTENNA_LOG_FILE = LOCAL_DIR / "state" / "antenna_log.json"
COMPARISONS_DIR = LOCAL_DIR / "comparisons"
ALL_TXT = LOCAL_DIR / "logs" / "ALL.TXT"
```

**With config support (future):**
```python
from lib.config import load_config

cfg = load_config()
LOCAL_DIR = Path(cfg.get("local_dir", Path(__file__).parent / "local"))
ANTENNAS_FILE = LOCAL_DIR / "state" / "antennas.json"
ANTENNA_LOG_FILE = LOCAL_DIR / "state" / "antenna_log.json"
COMPARISONS_DIR = LOCAL_DIR / "comparisons"
```

### 4. Sample Data for Testing

Provide sanitized sample artifacts for testing:

```
tests/fixtures/
├── sample_antennas.json        # Example antenna definitions
├── sample_antenna_log.json     # Example session log
├── sample_comparison/          # Example comparison results
│   ├── session.json
│   ├── report.txt
│   └── map_data.json
└── sample_wsjtx_log.adi        # Sanitized ADIF log
```

### 5. Documentation

**In README (Quick Start section):**
```markdown
### First-Time Setup

The `local/` directory is auto-created when you first run the tools. For WSL2 users, symlink WSJT-X logs:

```bash
# From repo root
mkdir -p local/logs
ln -s /mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT local/logs/
ln -s /mnt/c/Users/admin/AppData/Local/WSJT-X/wsjtx_log.adi local/logs/
```

**Note:** The `local/` directory is gitignored and contains all user-generated artifacts (comparisons, logs, state, config).
```

**In docs/artifact-management.md:**
- Explain `local/` directory structure
- Backup recommendations (`rsync local/`)
- Cleanup strategies (old comparisons)
- Migration from old scattered artifacts

### 6. Migration Script

Create `scripts/migrate_to_local.py` to help existing users:

```python
#!/usr/bin/env python3
"""Migrate scattered artifacts to local/ directory."""

import shutil
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
LOCAL_DIR = REPO_DIR / "local"

def migrate():
    print("Migrating artifacts to local/ directory...")

    # Create local/ subdirectories
    (LOCAL_DIR / "comparisons").mkdir(parents=True, exist_ok=True)
    (LOCAL_DIR / "state").mkdir(exist_ok=True)
    (LOCAL_DIR / "logs").mkdir(exist_ok=True)
    (LOCAL_DIR / "config").mkdir(exist_ok=True)

    # Move comparison directories
    moved_count = 0
    for comp_dir in REPO_DIR.glob("comparison_*"):
        if comp_dir.is_dir() and comp_dir.parent == REPO_DIR:
            dest = LOCAL_DIR / "comparisons" / comp_dir.name
            print(f"  Moving {comp_dir.name} → local/comparisons/")
            shutil.move(str(comp_dir), str(dest))
            moved_count += 1

    # Move state files
    state_files = ["antenna_log.json", "antennas.json"]
    for fname in state_files:
        src = REPO_DIR / fname
        if src.exists():
            dest = LOCAL_DIR / "state" / fname
            print(f"  Moving {fname} → local/state/")
            shutil.move(str(src), str(dest))

    # Move prior-ft8-work artifacts if they exist
    ft8_dir = REPO_DIR / "prior-ft8-work"
    if ft8_dir.exists():
        for fname in ["antenna_log.json", "antennas.json"]:
            src = ft8_dir / fname
            if src.exists():
                dest = LOCAL_DIR / "state" / fname
                print(f"  Moving prior-ft8-work/{fname} → local/state/")
                # Merge if dest exists, otherwise move
                if dest.exists():
                    print(f"    (Warning: {fname} already exists in local/state/, skipping)")
                else:
                    shutil.move(str(src), str(dest))

    print(f"\nMigration complete!")
    print(f"  Moved {moved_count} comparison directories")
    print(f"  Artifacts now in: {LOCAL_DIR}")
    print(f"\nNext steps:")
    print(f"  1. Review local/ directory contents")
    print(f"  2. Update .gitignore to add 'local/'")
    print(f"  3. Test tools to ensure they find artifacts")

if __name__ == "__main__":
    migrate()
```

### 7. Backup Strategy

**Simple backup approach:**

```bash
#!/bin/bash
# scripts/backup-local.sh - Backup local/ directory

REPO_DIR="$HOME/Sync/work/AK6MJ/wspr"
BACKUP_DIR="$HOME/Backups/ak6mj-hf"
DATE=$(date +%Y%m%d)

# Backup local/ directory
rsync -av --delete \
  "$REPO_DIR/local/" \
  "$BACKUP_DIR/daily-$DATE/"

# Keep last 30 days
find "$BACKUP_DIR" -type d -name "daily-*" -mtime +30 -delete

echo "Backed up to: $BACKUP_DIR/daily-$DATE/"
```

**Or just rsync manually:**
```bash
rsync -av local/ ~/Backups/ak6mj-hf/
```

**Note:** Since `local/` is inside your Sync folder, it may already be backed up by your sync service (Dropbox, OneDrive, etc.). Check if you need additional backups.

### 8. Cleanup Strategy

**For old comparisons:**

```python
# In antenna.py or separate cleanup script
def cleanup_old_comparisons(days=90):
    """Remove comparison directories older than N days."""
    cutoff = datetime.now() - timedelta(days=days)
    comparisons_dir = LOCAL_DIR / "comparisons"

    for comp_dir in comparisons_dir.glob("comparison_*"):
        # Parse timestamp from dirname
        match = re.search(r"comparison_(\d{8}_\d{6})", comp_dir.name)
        if match:
            ts = datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
            if ts < cutoff:
                print(f"Removing old comparison: {comp_dir.name}")
                shutil.rmtree(comp_dir)
```

**CLI command:**
```bash
python3 antenna.py cleanup --older-than 90
```

**Manual cleanup:**
```bash
# List comparisons by age
ls -lt local/comparisons/

# Remove specific comparison
rm -rf local/comparisons/comparison_20241214_150935/
```

## Alternative: Git LFS for Artifacts (Not Recommended)

Could use Git LFS to track large artifacts, but:

**Cons:**
- Adds complexity (LFS setup, quota limits)
- Artifacts are user/machine-specific (no value in sharing)
- Repo becomes bloated even with LFS
- Costs money for storage on GitHub

**When to use Git LFS:**
- Sample/reference data that benefits everyone
- Test fixtures
- Documentation images

**For user-generated artifacts:** External data directory is better.

## Sample .gitignore Template

Create `.gitignore-template` that users can customize:

```gitignore
# Copy this to .gitignore and customize for your setup

# Core ignores (always include)
__pycache__/
*.py[cod]
.DS_Store
*.db
config.yaml

# Data directory (using symlink strategy)
data/

# OR if storing artifacts in repo (not recommended)
#comparison_*/
#antenna_log.json
#antennas.json
#*.adi

# Your custom paths
#/mnt/c/Users/YourName/...
```

## Implementation Checklist

### Immediate (Phase 1)
- [x] Document artifact strategy (this file)
- [ ] Update .gitignore with all artifact patterns
- [ ] Test that existing artifacts are properly ignored
- [ ] Document data directory setup in README

### Near-term (Phase 2)
- [ ] Create migration script
- [ ] Update antenna.py to support data/ directory
- [ ] Update other tools (antenna_web.py, etc.)
- [ ] Test symlink strategy on macOS and WSL2
- [ ] Add sample fixtures for testing

### Future (Phase 3)
- [ ] Implement cleanup commands
- [ ] Add backup scripts to repo (in scripts/)
- [ ] Config-based data directory paths
- [ ] Archive old comparisons to compressed format

## Implementation Summary

### Immediate Actions (Do This Now)

1. **Update .gitignore**
   ```bash
   echo "local/" >> .gitignore
   ```

2. **Move existing artifacts** (if any in prior-ft8-work/)
   ```bash
   # If prior-ft8-work has artifacts, move them:
   mkdir -p local/state
   mv prior-ft8-work/antenna_log.json local/state/ 2>/dev/null || true
   mv prior-ft8-work/antennas.json local/state/ 2>/dev/null || true
   ```

3. **Create local/ structure**
   ```bash
   mkdir -p local/{comparisons,logs,state,config}
   ```

4. **Symlink WSJT-X logs** (WSL2 only)
   ```bash
   ln -s /mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT local/logs/
   ln -s /mnt/c/Users/admin/AppData/Local/WSJT-X/wsjtx_log.adi local/logs/
   ```

### Phase 1 Integration (Update Code)

When updating tools to use `local/`:
- Update path constants to use `LOCAL_DIR / "subdir"`
- Auto-create subdirectories on first run
- Maintain backwards compatibility during migration
- Test with existing artifacts

### Benefits of `local/` Approach

✓ **Simple** - Single directory, one .gitignore line
✓ **Discoverable** - Clear location for all user data
✓ **Portable** - Stays with repo in Sync folder
✓ **Standard** - Similar to `node_modules/`, `target/`, etc.
✓ **Safe** - Fully gitignored, no risk of committing secrets
