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

# Garmin typeKey → broad category (used for `type` field and heatmap color)
# 8 categories: Cardio | Cycling | Strength | Team Sports | Water Sports |
#               Hiking | Climbing | Winter Sports
TYPE_MAP = {
    # ── Cardio (Running + Walking) ────────────────────────────────────────────
    "running":                          "Cardio",
    "street_running":                   "Cardio",
    "track_running":                    "Cardio",
    "trail_running":                    "Cardio",
    "treadmill_running":                "Cardio",
    "indoor_running":                   "Cardio",
    "indoor_track":                     "Cardio",
    "ultra_run":                        "Cardio",
    "obstacle_run":                     "Cardio",
    "virtual_run":                      "Cardio",
    "wheelchair_push_run":              "Cardio",
    "walking":                          "Cardio",
    "casual_walking":                   "Cardio",
    "speed_walking":                    "Cardio",
    "indoor_walking":                   "Cardio",
    "indoor_walk":                      "Cardio",
    "step_tracking_and_walking":        "Cardio",
    "steps":                            "Cardio",
    "rucking":                          "Cardio",
    "wheelchair_push_walk":             "Cardio",

    # ── Cycling ───────────────────────────────────────────────────────────────
    "cycling":                          "Cycling",
    "road_biking":                      "Cycling",
    "mountain_biking":                  "Cycling",
    "gravel_cycling":                   "Cycling",
    "indoor_cycling":                   "Cycling",
    "indoor_bike":                      "Cycling",
    "track_cycling":                    "Cycling",
    "cyclocross":                       "Cycling",
    "recumbent_cycling":                "Cycling",
    "downhill_biking":                  "Cycling",
    "enduro_mtb":                       "Cycling",
    "bmx":                              "Cycling",
    "hand_cycling":                     "Cycling",
    "indoor_hand_cycling":              "Cycling",
    "virtual_ride":                     "Cycling",
    "e_bike_fitness":                   "Cycling",
    "e_bike_mountain":                  "Cycling",
    "e_enduro_mtb":                     "Cycling",
    "unbound_gravel_cycling":           "Cycling",

    # ── Strength ──────────────────────────────────────────────────────────────
    "strength_training":                "Strength",
    "fitness_equipment":                "Strength",
    "cardio_training":                  "Strength",
    "indoor_cardio":                    "Strength",
    "elliptical":                       "Strength",
    "stair_climbing":                   "Strength",
    "indoor_rowing":                    "Strength",
    "floor_climbing":                   "Strength",
    "jump_rope":                        "Strength",
    "hiit":                             "Strength",
    "yoga":                             "Strength",
    "pilates":                          "Strength",
    "meditation":                       "Strength",
    "breathwork":                       "Strength",
    "mobility":                         "Strength",
    "boxing":                           "Strength",
    "mixed_martial_arts":               "Strength",
    "toe_to_toe":                       "Strength",
    "toe_to_toe_no_tm":                 "Strength",
    "dance":                            "Strength",
    "other":                            "Strength",
    "uncategorized":                    "Strength",
    "multi_sport":                      "Strength",
    "triathlon":                        "Strength",
    "transition":                       "Strength",
    "para_sports":                      "Strength",
    "wheelchair_pushes":                "Strength",
    "pushes":                           "Strength",

    # ── Team Sports ───────────────────────────────────────────────────────────
    "soccer":                           "Team Sports",
    "soccer_football":                  "Team Sports",
    "football":                         "Team Sports",
    "american_football":                "Team Sports",
    "rugby":                            "Team Sports",
    "field_hockey":                     "Team Sports",
    "lacrosse":                         "Team Sports",
    "ultimate_disc":                    "Team Sports",
    "team_sports":                      "Team Sports",
    "volleyball":                       "Team Sports",
    "basketball":                       "Team Sports",
    "baseball":                         "Team Sports",
    "softball":                         "Team Sports",
    "ice_hockey":                       "Team Sports",
    "cricket":                          "Team Sports",
    "tennis":                           "Team Sports",
    "table_tennis":                     "Team Sports",
    "badminton":                        "Team Sports",
    "squash":                           "Team Sports",
    "racquetball":                      "Team Sports",
    "paddelball":                       "Team Sports",
    "platform_tennis":                  "Team Sports",
    "pickleball":                       "Team Sports",
    "racket_sports":                    "Team Sports",
    "racquet_sports":                   "Team Sports",
    "disc_golf":                        "Team Sports",

    # ── Water Sports ──────────────────────────────────────────────────────────
    "surfing":                          "Water Sports",
    "surfing_v2":                       "Water Sports",
    "stand_up_paddleboarding":          "Water Sports",
    "kiteboarding":                     "Water Sports",
    "wind_kite_surfing":                "Water Sports",
    "windsurfing":                      "Water Sports",
    "wakeboarding":                     "Water Sports",
    "wakesurfing":                      "Water Sports",
    "waterskiing":                      "Water Sports",
    "water_tubing":                     "Water Sports",
    "whitewater_rafting":               "Water Sports",
    "whitewater_rafting_kayaking":      "Water Sports",
    "kayaking":                         "Water Sports",
    "paddling":                         "Water Sports",
    "paddle_sports":                    "Water Sports",
    "sailing":                          "Water Sports",
    "boating":                          "Water Sports",
    "water_sports":                     "Water Sports",
    "rowing":                           "Water Sports",
    "swimming":                         "Water Sports",
    "lap_swimming":                     "Water Sports",
    "pool_swimming":                    "Water Sports",
    "open_water_swimming":              "Water Sports",
    "pool_apnea":                       "Water Sports",
    "snorkeling":                       "Water Sports",
    "diving":                           "Water Sports",
    "single_gas_diving":                "Water Sports",
    "multi_gas_diving":                 "Water Sports",
    "gauge_diving":                     "Water Sports",
    "apnea_diving":                     "Water Sports",
    "apnea_hunting":                    "Water Sports",
    "ccr_diving":                       "Water Sports",
    "offshore_grinding":                "Water Sports",
    "onshore_grinding":                 "Water Sports",

    # ── Hiking ────────────────────────────────────────────────────────────────
    "hiking":                           "Hiking",
    "mountaineering":                   "Hiking",
    "hunting":                          "Hiking",
    "hunting_fishing":                  "Hiking",
    "fishing":                          "Hiking",
    "horseback_riding":                 "Hiking",
    "overland":                         "Hiking",
    "snow_shoe":                        "Hiking",
    "golf":                             "Hiking",

    # ── Climbing ──────────────────────────────────────────────────────────────
    "bouldering":                       "Climbing",
    "rock_climbing":                    "Climbing",
    "indoor_climbing":                  "Climbing",

    # ── Winter Sports ─────────────────────────────────────────────────────────
    "winter_sport":                     "Winter Sports",
    "resort_skiing":                    "Winter Sports",
    "resort_skiing_snowboarding":       "Winter Sports",
    "resort_skiing_snowboarding_ws":    "Winter Sports",   # GPX variant
    "resort_snowboarding":              "Winter Sports",
    "snowboarding":                     "Winter Sports",
    "snow_skiing":                      "Winter Sports",
    "cross_country_skiing":             "Winter Sports",
    "skate_skiing":                     "Winter Sports",
    "skate_skiing_ws":                  "Winter Sports",   # GPX variant
    "backcountry_skiing":               "Winter Sports",
    "backcountry_skiing_ws":            "Winter Sports",   # GPX variant
    "backcountry_skiing_snowboarding":  "Winter Sports",
    "backcountry_snowboarding":         "Winter Sports",
    "skating":                          "Winter Sports",
    "inline_skating":                   "Winter Sports",
    "snowmobiling":                     "Winter Sports",
}

# Garmin typeKey → specific exercise display name (used for `exercise` field)
EXERCISE_MAP = {
    # Cardio — Running
    "running":                          "Running",
    "street_running":                   "Street Running",
    "track_running":                    "Track Running",
    "trail_running":                    "Trail Running",
    "treadmill_running":                "Treadmill Running",
    "indoor_running":                   "Indoor Running",
    "indoor_track":                     "Indoor Track",
    "ultra_run":                        "Ultra Running",
    "obstacle_run":                     "Obstacle Course",
    "virtual_run":                      "Virtual Running",
    "wheelchair_push_run":              "Wheelchair Running",
    # Cardio — Walking
    "walking":                          "Walking",
    "casual_walking":                   "Walking",
    "speed_walking":                    "Speed Walking",
    "indoor_walking":                   "Indoor Walking",
    "indoor_walk":                      "Indoor Walking",
    "step_tracking_and_walking":        "Walking",
    "steps":                            "Walking",
    "rucking":                          "Rucking",
    "wheelchair_push_walk":             "Wheelchair Walking",
    # Cycling
    "cycling":                          "Cycling",
    "road_biking":                      "Road Cycling",
    "mountain_biking":                  "Mountain Biking",
    "gravel_cycling":                   "Gravel Cycling",
    "indoor_cycling":                   "Indoor Cycling",
    "indoor_bike":                      "Indoor Cycling",
    "track_cycling":                    "Track Cycling",
    "cyclocross":                       "Cyclocross",
    "recumbent_cycling":                "Recumbent Cycling",
    "downhill_biking":                  "Downhill MTB",
    "enduro_mtb":                       "Enduro MTB",
    "bmx":                              "BMX",
    "hand_cycling":                     "Handcycling",
    "indoor_hand_cycling":              "Indoor Handcycling",
    "virtual_ride":                     "Virtual Cycling",
    "e_bike_fitness":                   "E-Bike",
    "e_bike_mountain":                  "E-Mountain Bike",
    "e_enduro_mtb":                     "E-Enduro MTB",
    "unbound_gravel_cycling":           "Gravel Cycling",
    # Strength
    "strength_training":                "Strength Training",
    "fitness_equipment":                "Gym",
    "cardio_training":                  "Cardio Training",
    "indoor_cardio":                    "Cardio",
    "elliptical":                       "Elliptical",
    "stair_climbing":                   "Stair Climber",
    "indoor_rowing":                    "Rowing Machine",
    "floor_climbing":                   "Floor Climbing",
    "jump_rope":                        "Jump Rope",
    "hiit":                             "HIIT",
    "yoga":                             "Yoga",
    "pilates":                          "Pilates",
    "meditation":                       "Meditation",
    "breathwork":                       "Breathwork",
    "mobility":                         "Mobility",
    "boxing":                           "Boxing",
    "mixed_martial_arts":               "MMA",
    "toe_to_toe":                       "Toe-to-Toe",
    "toe_to_toe_no_tm":                 "Toe-to-Toe",
    "dance":                            "Dance",
    "multi_sport":                      "Multisport",
    "triathlon":                        "Triathlon",
    "transition":                       "Transition",
    "para_sports":                      "Para Sports",
    "wheelchair_pushes":                "Wheelchair",
    "pushes":                           "Wheelchair",
    "other":                            "Other",
    "uncategorized":                    "Other",
    # Team Sports
    "soccer":                           "Football",
    "soccer_football":                  "Football",
    "football":                         "Football",
    "american_football":                "American Football",
    "rugby":                            "Rugby",
    "field_hockey":                     "Field Hockey",
    "lacrosse":                         "Lacrosse",
    "ultimate_disc":                    "Ultimate Disc",
    "team_sports":                      "Team Sports",
    "volleyball":                       "Volleyball",
    "basketball":                       "Basketball",
    "baseball":                         "Baseball",
    "softball":                         "Softball",
    "ice_hockey":                       "Ice Hockey",
    "cricket":                          "Cricket",
    "tennis":                           "Tennis",
    "table_tennis":                     "Table Tennis",
    "badminton":                        "Badminton",
    "squash":                           "Squash",
    "racquetball":                      "Racquetball",
    "paddelball":                       "Padel",
    "platform_tennis":                  "Platform Tennis",
    "pickleball":                       "Pickleball",
    "racket_sports":                    "Racket Sports",
    "racquet_sports":                   "Racket Sports",
    "disc_golf":                        "Disc Golf",
    # Water Sports
    "surfing":                          "Surfing",
    "surfing_v2":                       "Surfing",
    "stand_up_paddleboarding":          "SUP",
    "kiteboarding":                     "Kiteboarding",
    "wind_kite_surfing":                "Windsurfing",
    "windsurfing":                      "Windsurfing",
    "wakeboarding":                     "Wakeboarding",
    "wakesurfing":                      "Wakesurfing",
    "waterskiing":                      "Waterskiing",
    "water_tubing":                     "Tubing",
    "whitewater_rafting":               "Whitewater Rafting",
    "whitewater_rafting_kayaking":      "Whitewater Kayaking",
    "kayaking":                         "Kayaking",
    "paddling":                         "Canoeing",
    "paddle_sports":                    "Paddling",
    "sailing":                          "Sailing",
    "boating":                          "Boating",
    "water_sports":                     "Water Sports",
    "rowing":                           "Rowing",
    "swimming":                         "Swimming",
    "lap_swimming":                     "Pool Swimming",
    "pool_swimming":                    "Pool Swimming",
    "open_water_swimming":              "Open Water Swimming",
    "pool_apnea":                       "Pool Apnea",
    "snorkeling":                       "Snorkeling",
    "diving":                           "Diving",
    "single_gas_diving":                "Diving",
    "multi_gas_diving":                 "Diving",
    "gauge_diving":                     "Diving",
    "apnea_diving":                     "Apnea Diving",
    "apnea_hunting":                    "Apnea Hunting",
    "ccr_diving":                       "CCR Diving",
    "offshore_grinding":                "Offshore Grinding",
    "onshore_grinding":                 "Onshore Grinding",
    # Hiking
    "hiking":                           "Hiking",
    "mountaineering":                   "Mountaineering",
    "hunting":                          "Hunting",
    "hunting_fishing":                  "Hunting & Fishing",
    "fishing":                          "Fishing",
    "horseback_riding":                 "Horseback Riding",
    "overland":                         "Overland",
    "snow_shoe":                        "Snowshoeing",
    "golf":                             "Golf",
    # Climbing
    "bouldering":                       "Bouldering",
    "rock_climbing":                    "Rock Climbing",
    "indoor_climbing":                  "Indoor Climbing",
    # Winter Sports
    "winter_sport":                     "Winter Sports",
    "resort_skiing":                    "Skiing",
    "resort_skiing_snowboarding":       "Skiing",
    "resort_skiing_snowboarding_ws":    "Skiing",
    "resort_snowboarding":              "Snowboarding",
    "snowboarding":                     "Snowboarding",
    "snow_skiing":                      "Skiing",
    "cross_country_skiing":             "Cross-Country Skiing",
    "skate_skiing":                     "Skate Skiing",
    "skate_skiing_ws":                  "Skate Skiing",
    "backcountry_skiing":               "Backcountry Skiing",
    "backcountry_skiing_ws":            "Backcountry Skiing",
    "backcountry_skiing_snowboarding":  "Backcountry Skiing",
    "backcountry_snowboarding":         "Backcountry Snowboarding",
    "skating":                          "Skating",
    "inline_skating":                   "Inline Skating",
    "snowmobiling":                     "Snowmobiling",
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


def get_stat_fields(act, workout_type) -> dict:
    """
    Return extra frontmatter fields tailored to the activity category.
    All numeric values are Python numbers (not strings) so Dataview sorts them.
    """
    fields = {}

    distance_m = float(act.get("distance") or 0)
    avg_speed  = float(act.get("averageSpeed") or 0)
    max_speed  = float(act.get("maxSpeed") or 0)
    avg_hr     = act.get("averageHR")
    max_hr     = act.get("maxHR")
    elev_gain  = act.get("elevationGain")

    if avg_hr:  fields["avg_hr"]  = int(avg_hr)
    if max_hr:  fields["max_hr"]  = int(max_hr)

    if workout_type == "Cardio":
        if distance_m > 0:
            fields["distance"] = round(distance_m / 1000, 2)
        if avg_speed > 0:
            secs = 1000 / avg_speed
            fields["pace"] = f"{int(secs // 60)}:{int(secs % 60):02d} /km"

    elif workout_type == "Cycling":
        if distance_m > 0:
            fields["distance"] = round(distance_m / 1000, 2)
        if avg_speed > 0:
            fields["avg_speed"] = round(avg_speed * 3.6, 1)

    elif workout_type == "Strength":
        ex_sets   = act.get("summarizedExerciseSets") or []
        volume_g  = sum(float(s.get("volume", 0)) for s in ex_sets)
        if volume_g > 0:
            fields["volume"] = round(volume_g / 1000, 1)
        if ex_sets:
            names = []
            for s in ex_sets:
                raw = s.get("subCategory") or s.get("category", "")
                names.append(raw.replace("_", " ").title())
            fields["exercises"] = ", ".join(names)

    elif workout_type == "Winter Sports":
        if distance_m > 0:
            fields["distance"] = round(distance_m / 1000, 2)
        if max_speed > 0:
            fields["max_speed"] = round(max_speed * 3.6, 1)
        if elev_gain:
            fields["elevation_gain"] = int(elev_gain)

    elif workout_type == "Hiking":
        if distance_m > 0:
            fields["distance"] = round(distance_m / 1000, 2)
        if elev_gain:
            fields["elevation_gain"] = int(elev_gain)

    elif workout_type == "Water Sports":
        if distance_m > 0:
            fields["distance"] = round(distance_m / 1000, 2)

    elif workout_type == "Climbing":
        fields["attempts"] = 0
        fields["sends"]    = 0

    return fields


def make_note(date_str, workout_type, exercise, calories, duration,
              sets="0", reps="0", garmin_id=None, extra_fields=None) -> str:
    garmin_id_line = f'\ngarmin_id: "{garmin_id}"' if garmin_id is not None else ""
    extra_lines = ""
    if extra_fields:
        for key, val in extra_fields.items():
            extra_lines += f'\n{key}: "{val}"' if isinstance(val, str) else f'\n{key}: {val}'
    return f"""---
date_of_workout: "{date_str}"
exercise: "{exercise}"
sets: "{sets}"
reps: "{reps}"
time: "{duration}"
weight: "0"
type: "{workout_type}"
calories: "{calories}"{garmin_id_line}{extra_lines}
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
            workout_type = "Strength"   # safe fallback
        exercise = EXERCISE_MAP.get(garmin_key, garmin_key.replace("_", " ").title())

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
        extra_fields = get_stat_fields(act, workout_type)

        filename = free_filename(date_str, created_this_run)
        created_this_run.add(filename)

        (VAULT_WORKOUTS / filename).write_text(
            make_note(date_str, workout_type, exercise, calories, duration,
                      sets, reps, garmin_id, extra_fields),
            encoding="utf-8",
        )
        log.info("  Created %-30s (%s, %d cal)", filename, workout_type, calories)
        new_count += 1

    if unknown_types:
        log.warning(
            "Unknown Garmin type(s) mapped to 'Strength' — add them to TYPE_MAP if needed: %s",
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
