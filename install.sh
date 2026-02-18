#!/usr/bin/env bash
# install.sh — one-time setup for garmin-sync-obsidian
# Run once: bash install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.belzebub.garmin-sync-obsidian.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "==> Installing Python dependency..."
pip3 install garth

echo ""
echo "==> Running first sync (you'll be prompted for Garmin credentials)..."
python3 "$SCRIPT_DIR/sync_garmin.py"

echo ""
echo "==> Installing launchd job (daily at 09:00)..."
cp "$PLIST_SRC" "$PLIST_DST"
launchctl load "$PLIST_DST"

echo ""
echo "✓ Done."
echo ""
echo "  The script will now run automatically every day at 09:00."
echo "  Logs:        $SCRIPT_DIR/sync.log"
echo "  Manual sync: python3 $SCRIPT_DIR/sync_garmin.py"
echo ""
echo "  To uninstall the scheduled job:"
echo "    launchctl unload $PLIST_DST && rm $PLIST_DST"
