# Demo Vault

This is a sample Obsidian vault to preview how garmin-sync-obsidian works.
It contains real workout entries synced from Garmin Connect spanning 2024–2026.

## How to open

1. Open Obsidian → **Open another vault** → **Open folder as vault**
2. Select this `demo-vault` folder
   > Both plugins (Dataview and Heatmap Calendar) are already bundled in
   > `.obsidian/plugins/` — no installation needed.

3. **Enable JavaScript queries in Dataview:**
   Settings → Dataview → turn on **Enable JavaScript Queries**
   (the calendar uses a `dataviewjs` block and won't render without this)

4. Open **Workout view.md** to see the calendar and last month's log

## Test the sync script against this vault

```bash
python3 sync_garmin.py --vault /path/to/garmin-sync-obsidian/demo-vault
```

This will pull your real Garmin activities into the demo vault so you can
verify everything works before pointing it at your actual vault.

## What you'll see

A colour-coded activity calendar stacked by year, plus a last month's log
grouped by date showing exercise, time, distance, volume, pace/speed, and HR.

| Colour | Category | Activity types |
|--------|----------|---------------|
| 🟠 Orange | Strength | Strength training, gym, HIIT, yoga, boxing... |
| 🔴 Red | Cardio | Running, walking |
| 🟡 Yellow | Cycling | All cycling variants, e-bikes |
| 🟢 Green | Team Sports | Football, volleyball, basketball, rugby... |
| 🔵 Blue | Water Sports | Surfing, swimming, kayaking, diving, sailing... |
| 🟤 Brown | Hiking | Hiking, mountaineering, snowshoeing |
| 🩷 Pink | Climbing | Bouldering, rock climbing |
| ⬜ White | Winter Sports | Skiing, snowboarding, backcountry skiing |
