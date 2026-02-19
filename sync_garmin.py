#!/usr/bin/env python3
"""
Garmin Connect → Obsidian Brain sync script.

Pulls activities from Garmin Connect and creates workout notes in the vault.
Tracks the last synced activity timestamp so re-runs are always safe (no duplicates).

First run:  python3 sync_garmin.py          (will prompt for Garmin credentials)
Subsequent: python3 sync_garmin.py          (uses saved token in ~/.garth/)
"""

import argparse
import getpass
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path

try:
    import garth
except ImportError:
    print("garth is not installed. Run:  pip3 install garth")
    sys.exit(1)

# ── CLI args ──────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Sync Garmin activities to Obsidian workout notes.")
    p.add_argument(
        "--vault",
        default=str(Path(__file__).parent / "demo-vault"),
        metavar="PATH",
        help="Path to Obsidian vault (default: demo-vault/ next to this script)",
    )
    return p.parse_args()

# ── Paths ─────────────────────────────────────────────────────────────────────
# VAULT_WORKOUTS and STATE_FILE are module-level so all functions see them.
# __main__ overrides them from --vault before calling sync().

VAULT_WORKOUTS = Path.home() / "Brain" / "workouts"
STATE_FILE     = Path(__file__).parent / ".sync_state.json"
GARTH_HOME     = Path.home() / ".garth"
LOG_FILE       = Path(__file__).parent / "sync.log"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Activity type mapping ─────────────────────────────────────────────────────
# Garmin typeKey → vault `type` field

TYPE_MAP = {
    "strength_training":                "Strength Training",
    "soccer_football":                  "Soccer",
    "soccer":                           "Soccer",
    "football":                         "Soccer",
    "running":                          "Running",
    "trail_running":                    "Running",
    "treadmill_running":                "Running",
    "cycling":                          "Cycling",
    "road_biking":                      "Cycling",
    "mountain_biking":                  "Cycling",
    "indoor_cycling":                   "Cycling",
    "surfing":                          "Surfing",
    "open_water_swimming":              "Swimming",
    "swimming":                         "Swimming",
    "lap_swimming":                     "Swimming",
    "pool_swimming":                    "Swimming",
    "hiking":                           "Hiking",
    "bouldering":                       "Bouldering",
    "rock_climbing":                    "Bouldering",
    "resort_skiing_snowboarding_ws":    "Skiing",
    "resort_skiing":                    "Skiing",
    "skate_skiing_ws":                  "Skiing",
    "backcountry_skiing_ws":            "Backcountry Skiing",
    "backcountry_skiing":               "Backcountry Skiing",
    "volleyball":                       "Volleyball",
    "walking":                          "Walking",
    "fitness_equipment":                "Gym",
    "indoor_cardio":                    "Gym",
    "elliptical":                       "Gym",
    "indoor_rowing":                    "Gym",
    "yoga":                             "Gym",
    "pilates":                          "Gym",
}

EXERCISE_MAP = {
    "Strength Training":  "Strength Training",
    "Soccer":             "Football",
    "Running":            "Running",
    "Cycling":            "Cycling",
    "Surfing":            "Surfing",
    "Swimming":           "Swimming",
    "Hiking":             "Hiking",
    "Bouldering":         "Bouldering",
    "Skiing":             "Skiing",
    "Backcountry Skiing": "Backcountry Skiing",
    "Volleyball":         "Volleyball",
    "Walking":            "Walking",
    "Gym":                "Gym",
}

# ── Auth ──────────────────────────────────────────────────────────────────────

def authenticate():
    """Load saved Garmin tokens, or prompt for login on first run."""
    if GARTH_HOME.exists():
        try:
            garth.resume(str(GARTH_HOME))
            log.info("Loaded saved Garmin session from %s", GARTH_HOME)
            return
        except Exception:
            log.warning("Saved session invalid or expired — re-authenticating.")

    print("\nFirst-time setup: enter your Garmin Connect credentials.")
    print("These are used once to get an OAuth token saved to ~/.garth/")
    print("Your password is never stored in this project.\n")
    email    = input("Garmin Connect email: ").strip()
    password = getpass.getpass("Garmin Connect password: ")

    garth.login(email, password)
    garth.save(str(GARTH_HOME))
    log.info("Authenticated. Tokens saved to %s", GARTH_HOME)

# ── State ─────────────────────────────────────────────────────────────────────

def load_last_sync() -> datetime:
    """
    Return the datetime of the last successfully synced activity.
    Defaults to 2020-01-01 (fetch everything) if no state file exists.
    """
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            return datetime.fromisoformat(state["last_sync"])
        except Exception:
            pass

    log.info("No state file found — fetching all activities from Garmin.")
    return datetime(2020, 1, 1)


def save_last_sync(dt: datetime):
    STATE_FILE.write_text(json.dumps({"last_sync": dt.isoformat()}, indent=2))

# ── Vault scan ────────────────────────────────────────────────────────────────

def scan_vault() -> tuple:
    """
    Scan existing vault files to build deduplication indexes.

    Returns:
        existing_ids : set of garmin_id integers already in the vault
        csv_counts   : defaultdict[(date_str, workout_type) → int] for files
                       that have no garmin_id (i.e. CSV-imported)
    """
    existing_ids = set()
    csv_counts   = defaultdict(int)

    for f in VAULT_WORKOUTS.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue

        id_match = re.search(r'^garmin_id:\s*"?(\d+)"?', text, re.MULTILINE)
        if id_match:
            existing_ids.add(int(id_match.group(1)))
        else:
            # CSV-imported — count by (date, type) so we can skip matching Garmin activities
            date_m = re.search(r'^date_of_workout:\s*"?([^"\n]+)"?', text, re.MULTILINE)
            type_m = re.search(r'^type:\s*"?([^"\n]+)"?', text, re.MULTILINE)
            if date_m and type_m:
                key = (date_m.group(1).strip(), type_m.group(1).strip())
                csv_counts[key] += 1

    log.info(
        "Vault scan: %d garmin_id'd notes, %d CSV-imported (date,type) buckets.",
        len(existing_ids), len(csv_counts),
    )
    return existing_ids, csv_counts

# ── Garmin fetch ──────────────────────────────────────────────────────────────

def fetch_activities(since: datetime) -> list:
    """Fetch all activities from Garmin Connect with startTimeLocal > since."""
    activities = []
    start = 0
    limit = 100
    since_date = since.date()

    while True:
        batch = garth.connectapi(
            "/activitylist-service/activities/search/activities",
            params={
                "limit":     limit,
                "start":     start,
                "startDate": since_date.isoformat(),
            },
        )
        if not batch:
            break
        activities.extend(batch)
        if len(batch) < limit:
            break
        start += limit

    log.info("Fetched %d activities from Garmin (since %s).", len(activities), since_date)
    return activities

# ── File creation ─────────────────────────────────────────────────────────────

def seconds_to_hms(seconds) -> str:
    try:
        s = int(float(seconds))
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    except Exception:
        return "00:00:00"


def free_filename(date_str: str, created_this_run: set) -> str:
    """Return a filename that doesn't exist on disk and wasn't created this run."""
    count = 0
    while True:
        name = f"{date_str}-.md" if count == 0 else f"{date_str}-{count}.md"
        if not (VAULT_WORKOUTS / name).exists() and name not in created_this_run:
            return name
        count += 1


def make_note(date_str, workout_type, exercise, calories, duration,
              sets="0", reps="0", garmin_id=None) -> str:
    garmin_id_line = f'\ngarmin_id: "{garmin_id}"' if garmin_id is not None else ""
    return f"""---
date_of_workout: "{date_str}"
exercise: "{exercise}"
sets: "{sets}"
reps: "{reps}"
time: "{duration}"
weight: "0"
type: "{workout_type}"
calories: "{calories}"{garmin_id_line}
---
#workouts
"""

# ── Main sync ─────────────────────────────────────────────────────────────────

def sync():
    authenticate()

    last_sync = load_last_sync()
    raw       = fetch_activities(last_sync)

    existing_ids, csv_counts = scan_vault()
    skipped_counts = defaultdict(int)  # tracks CSV-matched skips per (date, type)

    created_this_run = set()
    latest_seen      = last_sync
    new_count        = 0
    skip_count       = 0
    unknown_types    = set()

    for act in raw:
        # Parse start time
        start_str = act.get("startTimeLocal") or act.get("startTimeGMT", "")
        try:
            act_time = datetime.strptime(start_str[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            log.warning("Skipping activity %s — unparseable date: %r",
                        act.get("activityId"), start_str)
            continue

        # Track latest timestamp regardless (so state file advances properly)
        if act_time > latest_seen:
            latest_seen = act_time

        # Skip anything before our baseline
        if act_time <= last_sync:
            continue

        date_str = act_time.strftime("%Y-%m-%d")

        # Map type
        garmin_key   = (act.get("activityType") or {}).get("typeKey", "").lower()
        workout_type = TYPE_MAP.get(garmin_key)
        if workout_type is None:
            unknown_types.add(garmin_key)
            workout_type = "Gym"   # safe fallback
        exercise = EXERCISE_MAP.get(workout_type, workout_type)

        garmin_id = act.get("activityId")

        # ── Deduplication ──────────────────────────────────────────────────────

        # 1) Already synced by garmin_id (from a previous garmin-sync run)
        if garmin_id and int(garmin_id) in existing_ids:
            skip_count += 1
            continue

        # 2) Matches a CSV-imported note (same date + type, within count)
        key = (date_str, workout_type)
        if skipped_counts[key] < csv_counts[key]:
            skipped_counts[key] += 1
            skip_count += 1
            continue

        # ── Create note ───────────────────────────────────────────────────────

        calories = int(act.get("calories") or 0)
        duration = seconds_to_hms(act.get("duration") or 0)
        sets = str(int(act.get("activeSets") or 0))
        reps = str(int(act.get("totalReps")  or 0))

        filename = free_filename(date_str, created_this_run)
        created_this_run.add(filename)

        (VAULT_WORKOUTS / filename).write_text(
            make_note(date_str, workout_type, exercise, calories, duration,
                      sets, reps, garmin_id),
            encoding="utf-8",
        )
        log.info("  Created %-30s (%s, %d cal)", filename, workout_type, calories)
        new_count += 1

    if unknown_types:
        log.warning(
            "Unknown Garmin type(s) mapped to 'Gym' — add them to TYPE_MAP if needed: %s",
            ", ".join(sorted(unknown_types)),
        )

    if skip_count:
        log.info("Skipped %d activit(ies) already in vault.", skip_count)

    # Always save state so next run knows where to resume from
    save_last_sync(latest_seen)
    log.info("Done — %d new note(s) created.", new_count)


if __name__ == "__main__":
    args = parse_args()
    # Override module-level paths before sync() runs
    VAULT_WORKOUTS = Path(args.vault) / "workouts"  # noqa: F811
    STATE_FILE     = Path(__file__).parent / ".sync_state.json"  # noqa: F811
    VAULT_WORKOUTS.mkdir(parents=True, exist_ok=True)
    sync()
