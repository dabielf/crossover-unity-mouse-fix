#!/bin/bash
set -euo pipefail

# CrossOver Unity Mouse Fix — Installer
# Patches CrossOver to fix mouse input in Unity games using EnableMouseInPointer.
# Fixes: clicks, drag-and-drop, and hold-to-fire.

CX_APP="/Applications/CrossOver.app"
WINE_LIB="$CX_APP/Contents/SharedSupport/CrossOver/lib/wine"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Detect CrossOver version
CX_VERSION=$(defaults read "$CX_APP/Contents/Info" CFBundleShortVersionString 2>/dev/null || echo "unknown")
echo "Detected CrossOver version: $CX_VERSION"

# Check for matching binaries
MAJOR_VERSION=$(echo "$CX_VERSION" | grep -oE '^[0-9]+\.[0-9]+' || echo "")
BIN_DIR="$SCRIPT_DIR/binaries/crossover-$MAJOR_VERSION"

if [ ! -d "$BIN_DIR" ]; then
    echo "ERROR: No pre-patched binaries found for CrossOver $MAJOR_VERSION"
    echo "Available versions:"
    ls "$SCRIPT_DIR/binaries/" 2>/dev/null || echo "  (none)"
    echo ""
    echo "You may need to update this repo or build from source."
    exit 1
fi

# Check that CrossOver is not running
if pgrep -f "CrossOver" > /dev/null 2>&1 || pgrep -f "wine" > /dev/null 2>&1; then
    echo "ERROR: CrossOver or Wine processes are still running."
    echo "Please quit CrossOver completely before installing."
    echo ""
    echo "To force-kill all Wine processes:"
    echo "  pkill -9 -f wine; pkill -9 -f CrossOver"
    exit 1
fi

# Verify target paths exist
if [ ! -d "$WINE_LIB/x86_64-windows" ] || [ ! -d "$WINE_LIB/x86_64-unix" ]; then
    echo "ERROR: CrossOver wine lib directory not found at expected path."
    echo "Expected: $WINE_LIB"
    exit 1
fi

# Backup originals
BACKUP_DIR="$HOME/Desktop/crossover-unity-mouse-fix-backup"
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Backing up original files to $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    cp "$WINE_LIB/x86_64-windows/win32u.dll" "$BACKUP_DIR/" 2>/dev/null || true
    cp "$WINE_LIB/x86_64-unix/win32u.so" "$BACKUP_DIR/" 2>/dev/null || true
    # user32.dll may not exist in stock — that's expected
    cp "$WINE_LIB/x86_64-windows/user32.dll" "$BACKUP_DIR/" 2>/dev/null || true
    echo "  Backup saved."
else
    echo "Backup already exists at $BACKUP_DIR — skipping."
fi

# Install patched files
echo "Installing patched files..."
cp "$BIN_DIR/win32u.dll" "$WINE_LIB/x86_64-windows/win32u.dll"
cp "$BIN_DIR/win32u.so" "$WINE_LIB/x86_64-unix/win32u.so"
cp "$BIN_DIR/user32.dll" "$WINE_LIB/x86_64-windows/user32.dll"
echo "  3 files installed."

# Verify
echo "Verifying..."
if [ -f "$BIN_DIR/SHA256SUMS" ]; then
    cd "$WINE_LIB"
    while IFS='  ' read -r expected_hash filepath; do
        actual_hash=$(shasum -a 256 "$filepath" 2>/dev/null | awk '{print $1}')
        if [ "$actual_hash" = "$expected_hash" ]; then
            echo "  OK: $filepath"
        else
            echo "  MISMATCH: $filepath"
            echo "    expected: $expected_hash"
            echo "    actual:   $actual_hash"
        fi
    done < "$BIN_DIR/SHA256SUMS"
    cd "$SCRIPT_DIR"
else
    echo "  (no SHA256SUMS file — skipping verification)"
fi

# Re-sign
echo ""
echo "Re-signing CrossOver.app (requires sudo)..."
sudo xattr -cr "$CX_APP"
sudo codesign --force --deep --sign - "$CX_APP"
echo "  Done."

echo ""
echo "Installation complete!"
echo "Launch CrossOver and test a Unity game."
echo ""
echo "To uninstall, run: ./uninstall.sh"
