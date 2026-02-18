# Demo Vault

This is a sample Obsidian vault to preview how garmin-sync-obsidian works.
It contains 94 dummy workout entries spanning 2024–2026.

## How to open

1. Open Obsidian → **Open another vault** → **Open folder as vault**
2. Select this `demo-vault` folder
3. Install the two required community plugins:
   - **Dataview** — queries the workout notes
   - **Heatmap Calendar** — renders the GitHub-style calendar

   > The plugins are already listed in `.obsidian/community-plugins.json` and
   > will be auto-enabled once installed.

4. **Enable JavaScript queries in Dataview:**
   Settings → Dataview → turn on **Enable JavaScript Queries**
   (the calendar uses a `dataviewjs` block and won't render without this)

5. Open **Workout routine.md** to see the calendar

## Test the sync script against this vault

```bash
python3 sync_garmin.py --vault /path/to/garmin-sync-obsidian/demo-vault
```

This will pull your real Garmin activities into the demo vault so you can
verify everything works before pointing it at your actual vault.

## What you'll see

A colour-coded activity calendar stacked by year (2024 → 2026):

| Colour | Activity types |
|--------|---------------|
| 🟠 Orange | Strength Training, Gym, Calisthenics |
| 🔴 Red | Running, Walking, Hiking, Cycling |
| 🟢 Green | Soccer, Volleyball |
| 🔵 Blue | Surfing, Swimming |
| ⬜ White/Gray | Skiing, Backcountry Skiing |
| 🩷 Pink | Bouldering |
