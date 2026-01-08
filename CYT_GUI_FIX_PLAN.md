# CYT GUI Fix Plan - Next Session

## Problem Diagnosis (COMPLETE)

**Error**: `disk I/O error` when GUI tries to connect to Kismet database

**Root Cause Identified**:
- GUI tries to open `logs/kismet` as a database file
- `logs/kismet` is a **directory**, not a file
- The actual database files are **inside** that directory (e.g., `Kismet-20251220-03-45-16-1.kismet`)

**Evidence**:
```
[INFO   ] [Using direct Kismet DB path] logs/kismet
[ERROR  ] [Failed to connect to database logs/kismet] disk I/O error
```

**Why CLI Works but GUI Doesn't**:
- CLI (`chasing_your_tail.py`) has logic to search for the latest `.kismet` file in the directory
- GUI (`cyt_gui.py`) likely tries to use the path directly without searching for files

---

## Fix Strategy

### Step 1: Read cyt_gui.py and locate database connection code
**File**: `~/Chasing-Your-Tail-NG/cyt_gui.py`

**What to look for**:
- How it reads `config['paths']['kismet_logs']`
- Where it tries to open the database connection
- Compare with `chasing_your_tail.py` lines 96-120 (successful implementation)

### Step 2: Implement the same logic as CLI

**CLI's working approach** (from `chasing_your_tail.py`):
```python
db_path_pattern = self.config['paths']['kismet_logs']

# Check if it's a directory or a file pattern
if os.path.isdir(db_path_pattern):
    # It's a directory - find the latest .kismet file
    search_pattern = os.path.join(db_path_pattern, '*.kismet')
    kismet_files = glob.glob(search_pattern)
    if kismet_files:
        # Sort by modification time, get most recent
        self.latest_kismet_db = max(kismet_files, key=os.path.getmtime)
    else:
        logging.error(f"No .kismet files found in {db_path_pattern}")
        return False
else:
    # It's a file pattern - use directly
    self.latest_kismet_db = db_path_pattern
```

**Apply this same logic to cyt_gui.py**

### Step 3: Test the fix

**In VM**:
```bash
cd ~/Chasing-Your-Tail-NG
source venv/bin/activate
python3 cyt_gui.py
```

**Expected results after fix**:
- No "disk I/O error"
- GUI shows device list from Kismet database
- Behavioral detection data displays
- No database errors in output

### Step 4: Commit the fix

**In macOS terminal**:
```bash
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG

# Copy fixed file from VM (if edited in VM)
# OR edit in macOS and copy to VM for testing

git status
git diff cyt_gui.py  # Review changes
git add cyt_gui.py
git commit -m "Fix GUI database connection to find latest .kismet file

GUI was trying to open 'logs/kismet' directory as a database file,
causing 'disk I/O error'. Now uses same logic as CLI to search for
the latest .kismet file within the directory.

Fixes:
- Added directory detection and .kismet file search
- Uses glob.glob() to find database files
- Selects most recent file by modification time

Tested on: Kali Linux VM with Kismet 2022.08.R1
Resolves: GUI 'disk I/O error' on startup

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git push origin main
```

### Step 5: Create final production snapshot

**After GUI fix is verified working**:
```bash
prlctl snapshot "{f058900f-7772-4cd7-8443-655c19cf868c}" \
  --name "CYT-Production-Ready" \
  --description "100% Complete - CLI working, GPS integrated, GUI fixed, all systems operational"
```

---

## Files to Review Next Session

**Primary file to fix**: 
- `cyt_gui.py` - Need to add Kismet file search logic

**Reference files** (working examples):
- `chasing_your_tail.py` lines 96-120 - Shows correct implementation
- `config.json` - Confirms `kismet_logs` is `logs/kismet` (directory)

**Files in VM to check**:
- `~/Chasing-Your-Tail-NG/cyt_gui.py`
- `~/Chasing-Your-Tail-NG/logs/kismet/` - Contains actual .kismet files

---

## Expected Code Changes

**Location**: cyt_gui.py (exact line numbers to be determined)

**Before (broken)**:
```python
db_path = config['paths']['kismet_logs']
# Tries to open directory as database -> disk I/O error
```

**After (fixed)**:
```python
import glob
import os

db_path_pattern = config['paths']['kismet_logs']

# Check if it's a directory
if os.path.isdir(db_path_pattern):
    search_pattern = os.path.join(db_path_pattern, '*.kismet')
    kismet_files = glob.glob(search_pattern)
    if kismet_files:
        db_path = max(kismet_files, key=os.path.getmtime)
        logging.info(f"Using latest Kismet DB: {db_path}")
    else:
        logging.error(f"No .kismet files found in {db_path_pattern}")
        db_path = None
else:
    db_path = db_path_pattern
```

---

## Success Criteria

✅ GUI starts without "disk I/O error"  
✅ GUI displays device list from Kismet  
✅ GUI shows behavioral detection data  
✅ No database errors in logs  
✅ Fix committed to Git  
✅ Final snapshot created  
✅ **CYT 100% Production Ready**

---

## Time Estimate

- **Code review and fix**: 10-15 minutes
- **Testing**: 5 minutes  
- **Git commit**: 2 minutes
- **Snapshot creation**: 1 minute

**Total**: ~20-25 minutes

---

## Current Status

- ✅ Problem diagnosed: GUI tries to open directory as database
- ✅ Root cause identified: Missing file search logic
- ✅ Fix strategy documented
- ⏳ Code changes pending (next session)

---

**Session End**: 2025-12-20
**Ready for Next Session**: YES - Clear plan documented
