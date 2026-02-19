# garmin-sync-obsidian

Pulls activities from Garmin Connect and creates workout notes in your Obsidian vault, compatible with the Heatmap Calendar.

## Setup (once)

Pass your vault path as an argument, or leave it out to be prompted:

```bash
bash install.sh ~/path/to/your-vault   # e.g. bash install.sh ~/Brain
```

This will:
1. Install the `garth` Python library
2. Prompt for your Garmin Connect credentials (used once to get an OAuth token — your password is never stored)
3. Run the first sync immediately
4. Install a macOS launchd job that syncs every day at 09:00 **and** on every login/restart

## Manual sync

```bash
python3 sync_garmin.py --vault ~/path/to/your-vault
```

## Demo vault

Open `demo-vault/` as an Obsidian vault to see what the calendar looks like
with pre-populated dummy data — no Garmin account needed.
See [`demo-vault/README.md`](demo-vault/README.md) for instructions.

## How it works

- **Auth**: [garth](https://github.com/matin/garth) authenticates against Garmin Connect and saves an OAuth token to `~/.garth/`. You only enter your password once.
- **Deduplication**: Each synced note stores a `garmin_id` in its frontmatter. On every run the vault is scanned first, so activities already present are never duplicated — even if you imported historical data from a Garmin CSV export before setting this up. The last synced timestamp is saved in `.sync_state.json` to limit future API calls.
- **Note format**: Each activity becomes one `.md` file in `<vault>/workouts/` with YAML frontmatter only — no body content, so all fields are queryable via Dataview.

## Note fields

Every note contains a `type` (broad category for color coding) and an `exercise` (specific activity name). Additional fields are included based on the activity category:

| Category | Extra fields |
|---|---|
| Strength | `volume` (kg), `exercises` (named list), `avg_hr`, `max_hr` |
| Cardio | `distance` (km), `pace` (min/km), `avg_hr`, `max_hr` |
| Cycling | `distance` (km), `avg_speed` (km/h), `avg_hr`, `max_hr` |
| Winter Sports | `distance` (km), `max_speed` (km/h), `elevation_gain` (m) |
| Hiking | `distance` (km), `elevation_gain` (m), `avg_hr`, `max_hr` |
| Water Sports | `distance` (km), `avg_hr`, `max_hr` |
| Climbing | `attempts`, `sends`, `max_grade` (Vermin scale), `avg_hr`, `max_hr` |
| Team Sports | `avg_hr`, `max_hr` |

## Heatmap color mapping

| Color | Category | Activity types |
|---|---|---|
| 🟠 Orange | Strength | Strength training, gym, HIIT, yoga, boxing... |
| 🔴 Red | Cardio | Running, walking |
| 🟡 Yellow | Cycling | All cycling variants, e-bikes |
| 🟢 Green | Team Sports | Football, volleyball, basketball, rugby... |
| 🔵 Blue | Water Sports | Surfing, swimming, kayaking, diving, sailing... |
| 🟤 Brown | Hiking | Hiking, mountaineering, snowshoeing |
| 🩷 Pink | Climbing | Bouldering, rock climbing |
| ⬜ White | Winter Sports | Skiing, snowboarding, backcountry skiing |

## Adding new Garmin activity types

If a new activity type appears in the log as `Unknown Garmin type`, add it to `TYPE_MAP` and `EXERCISE_MAP` in `sync_garmin.py`.

## Logs

Stored in `sync.log` in this directory.

## Uninstall scheduled job

```bash
launchctl unload ~/Library/LaunchAgents/com.avelouk.garmin-sync-obsidian.plist
rm ~/Library/LaunchAgents/com.avelouk.garmin-sync-obsidian.plist
```
