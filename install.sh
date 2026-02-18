#!/usr/bin/env bash
# install.sh — one-time setup for garmin-sync-obsidian
#
# Usage:
#   bash install.sh                  # prompts for vault path
#   bash install.sh ~/Brain          # pass vault path directly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.belzebub.garmin-sync-obsidian.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"
DEFAULT_VAULT="$SCRIPT_DIR/demo-vault"

# ── Resolve vault path ────────────────────────────────────────────────────────

if [ $# -ge 1 ]; then
    VAULT_PATH="$1"
else
    echo "Where is your Obsidian vault?"
    echo "  Press Enter to use the demo vault for testing."
    read -r -p "  Vault path [${DEFAULT_VAULT}]: " VAULT_PATH
    VAULT_PATH="${VAULT_PATH:-$DEFAULT_VAULT}"
fi

# Expand ~ to $HOME
VAULT_PATH="${VAULT_PATH/#\~/$HOME}"

echo ""
echo "  Vault: $VAULT_PATH"
echo ""

# ── Dependencies ──────────────────────────────────────────────────────────────

echo "==> Installing Python dependency..."
pip3 install garth

# ── First sync ────────────────────────────────────────────────────────────────

echo ""
echo "==> Running first sync (you'll be prompted for Garmin credentials)..."
python3 "$SCRIPT_DIR/sync_garmin.py" --vault "$VAULT_PATH"

# ── Install launchd job ───────────────────────────────────────────────────────
# Write the plist directly so the vault path and script path are baked in,
# rather than copying the repo template which has placeholder defaults.

echo ""
echo "==> Installing launchd job (daily at 09:00 + on every login)..."

cat > "$PLIST_DST" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.belzebub.garmin-sync-obsidian</string>

    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>${SCRIPT_DIR}/sync_garmin.py</string>
        <string>--vault</string>
        <string>${VAULT_PATH}</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/sync.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/sync.log</string>

    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
PLIST

launchctl load "$PLIST_DST"

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "✓ Done."
echo ""
echo "  Vault:       $VAULT_PATH"
echo "  Auto-sync:   daily at 09:00 and on every login/restart"
echo "  Logs:        $SCRIPT_DIR/sync.log"
echo "  Manual sync: python3 $SCRIPT_DIR/sync_garmin.py --vault $VAULT_PATH"
echo ""
echo "  To uninstall the scheduled job:"
echo "    launchctl unload $PLIST_DST && rm $PLIST_DST"
