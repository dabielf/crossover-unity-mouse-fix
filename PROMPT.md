# AI Assistant Installation Guide

Use these instructions to install the CrossOver Unity Mouse Fix on a user's Mac.

## Prerequisites

- macOS (Intel or Apple Silicon)
- CrossOver 26.0 installed at `/Applications/CrossOver.app`
- CrossOver must be fully quit (no Wine processes running)

## Step-by-step

### 1. Verify CrossOver is not running

```bash
pgrep -f wine && echo "STOP: Kill Wine first" || echo "OK: No Wine processes"
pgrep -f CrossOver && echo "STOP: Quit CrossOver first" || echo "OK: CrossOver not running"
```

If processes are running, kill them:
```bash
pkill -9 -f wine; pkill -9 -f CrossOver; pkill -9 -f conhost
```

### 2. Clone the repo

```bash
git clone https://github.com/dabielf/crossover-unity-mouse-fix.git /tmp/crossover-unity-mouse-fix
cd /tmp/crossover-unity-mouse-fix
```

### 3. Run the installer

```bash
chmod +x install.sh
./install.sh
```

This will:
- Back up original files to `~/Desktop/crossover-unity-mouse-fix-backup/`
- Copy 3 patched files into CrossOver:
  - `x86_64-windows/win32u.dll` (replaced)
  - `x86_64-unix/win32u.so` (replaced)
  - `x86_64-windows/user32.dll` (added — does not exist in stock)
- Re-sign the app with `sudo xattr -cr` + `sudo codesign --force --deep --sign -`

The re-signing step requires sudo (user's password).

### 4. Verify

Ask the user to:
1. Launch CrossOver
2. Start Steam (or whichever launcher)
3. Launch a Unity game that had the mouse bug
4. Test: mouse clicks, drag-and-drop, hold-to-fire

### 5. If something breaks

Run the uninstaller to restore original files:
```bash
cd /tmp/crossover-unity-mouse-fix
./uninstall.sh
```

## Important Notes

- **All 3 files must be installed together.** A partial install causes `conhost.exe` infinite spawn loops.
- **user32.dll does not exist in stock CrossOver 26.0** for x86_64. The installer *adds* it — this is expected.
- **After CrossOver updates**, the fix needs to be re-applied. Check the repo for updated binaries.
- **Do not modify bottle environment variables** like `DXMT_ENABLE_NVEXT` or `D3DM_ENABLE_METALFX` — these can trigger instability with the patch.

## What this fixes

Unity games using `EnableMouseInPointer` (Unity 6 and recent builds) get broken mouse input under Wine/CrossOver because the API is not implemented. This patch implements it, converting `WM_MOUSE` events to `WM_POINTER` events with correct button state for drag operations.

Symptom in the game's Player.log:
```
EnableMouseInPointer failed with the following error: Call not implemented.
```

## Uninstall

```bash
cd /tmp/crossover-unity-mouse-fix
chmod +x uninstall.sh
./uninstall.sh
```
