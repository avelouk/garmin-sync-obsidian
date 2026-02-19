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
- **Note format**: Each activity becomes one `.md` file in `<vault>/workouts/` with YAML frontmatter matching the vault's workout template.

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
launchctl unload ~/Library/LaunchAgents/com.avelouk.garmin-sync-obsidian.plist
rm ~/Library/LaunchAgents/com.avelouk.garmin-sync-obsidian.plist
```
