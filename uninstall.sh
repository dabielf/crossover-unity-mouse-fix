#!/bin/bash
set -euo pipefail

# CrossOver Unity Mouse Fix — Uninstaller
# Restores original CrossOver files from backup.

CX_APP="/Applications/CrossOver.app"
WINE_LIB="$CX_APP/Contents/SharedSupport/CrossOver/lib/wine"
BACKUP_DIR="$HOME/Desktop/crossover-unity-mouse-fix-backup"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: No backup found at $BACKUP_DIR"
    echo "Cannot uninstall without the original files."
    exit 1
fi

# Check that CrossOver is not running
if pgrep -x "CrossOver" > /dev/null 2>&1 || pgrep -f "wineserver" > /dev/null 2>&1; then
    echo "ERROR: CrossOver or Wine processes are still running."
    echo "Please quit CrossOver completely before uninstalling."
    exit 1
fi

echo ""
read -p "Restore original CrossOver files from backup? [y/N] " confirm
if [[ ! "$confirm" =~ ^[yY]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo "Restoring original files from $BACKUP_DIR..."

cp "$BACKUP_DIR/win32u.dll" "$WINE_LIB/x86_64-windows/win32u.dll"
cp "$BACKUP_DIR/win32u.so" "$WINE_LIB/x86_64-unix/win32u.so"

# Remove user32.dll from x86_64-windows if backup doesn't have one (stock didn't have it)
if [ -f "$BACKUP_DIR/user32.dll" ]; then
    cp "$BACKUP_DIR/user32.dll" "$WINE_LIB/x86_64-windows/user32.dll"
else
    rm -f "$WINE_LIB/x86_64-windows/user32.dll"
fi

echo "  Files restored."

echo ""
echo "Re-signing CrossOver.app (requires sudo)..."
sudo xattr -cr "$CX_APP"
sudo codesign --force --deep --sign - "$CX_APP"
echo "  Done."

echo ""
echo "Uninstall complete. CrossOver is back to stock."
