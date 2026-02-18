# garmin-sync-obsidian

Pulls activities from Garmin Connect and creates workout notes in your Obsidian Brain vault (`~/Brain/workouts/`), compatible with the Heatmap Calendar in `Workout routine.md`.

## Setup (once)

```bash
bash install.sh
```

This will:
1. Install the `garth` Python library
2. Prompt for your Garmin Connect credentials (used once to get an OAuth token — your password is never stored)
3. Run the first sync immediately
4. Install a macOS launchd job that syncs every day at 09:00

## Manual sync

```bash
python3 sync_garmin.py
```

## How it works

- **Auth**: [garth](https://github.com/matin/garth) authenticates against Garmin Connect and saves an OAuth token to `~/.garth/`. You only enter your password once.
- **Deduplication**: The last synced activity timestamp is saved in `.sync_state.json`. Re-runs only create notes for new activities.
- **Note format**: Each activity becomes one `.md` file in `~/Brain/workouts/` with YAML frontmatter matching the vault's workout template.

## Activity → color mapping

| Color | Types |
|---|---|
| 🟠 Orange | Strength Training, Gym, Calisthenics |
| 🔴 Red | Running, Walking, Hiking, Cycling |
| 🟢 Green | Soccer, Volleyball |
| 🔵 Blue | Surfing, Swimming |
| ⬜ White | Skiing, Backcountry Skiing |
| 🩷 Pink | Bouldering |

## Adding new Garmin activity types

If a new activity type appears in the log as `Unknown Garmin type`, add it to `TYPE_MAP` in `sync_garmin.py`.

## Logs

Stored in `sync.log` in this directory.

## Uninstall scheduled job

```bash
launchctl unload ~/Library/LaunchAgents/com.belzebub.garmin-sync-obsidian.plist
rm ~/Library/LaunchAgents/com.belzebub.garmin-sync-obsidian.plist
```
