# CrossOver Unity Mouse Fix

Fixes mouse input for Unity games running in CrossOver on macOS. Solves the `EnableMouseInPointer` issue that causes Unity 6+ games to ignore mouse clicks, drag-and-drop, and hold-to-fire.

## The Problem

Newer Unity builds use `EnableMouseInPointer` to receive `WM_POINTER` events instead of classic `WM_MOUSE` events. Wine/CrossOver only has stubs for this API, so the cursor moves but all mouse interactions are ignored in-game.

You'll see this in the game's `Player.log`:
```
EnableMouseInPointer failed with the following error: Call not implemented.
```

## What This Fixes

| Action | Before | After |
|--------|--------|-------|
| Mouse clicks | Ignored | Working |
| Hover / tooltips | Ignored | Working |
| Drag and drop | Ignored | Working |
| Hold-to-fire / long press | Ignored | Working |
| Right / middle click | Ignored | Working |

## Quick Install (CrossOver 26.0)

Pre-patched binaries are included for CrossOver 26.0. No compilation needed.

```bash
git clone https://github.com/dabielf/crossover-unity-mouse-fix.git
cd crossover-unity-mouse-fix
chmod +x install.sh uninstall.sh
./install.sh
```

The installer will:
1. Back up your original files to `~/Desktop/crossover-unity-mouse-fix-backup/`
2. Copy the patched `win32u.dll`, `win32u.so`, and `user32.dll` into CrossOver
3. Re-sign the app (requires sudo)

**Important:** Quit CrossOver completely before running the installer.

## Uninstall

```bash
./uninstall.sh
```

Restores the original files from backup and re-signs the app.

## AI-Assisted Install

If you use an AI coding assistant (Claude Code, Cursor, etc.), point it at [`PROMPT.md`](PROMPT.md) for step-by-step installation instructions it can follow directly.

## Tested Games

- Magicraft
- Loopler
- Sritchy Scratchy
- Vampire Crawlers Demo
- Everything Is Crab Demo
- Should work with any Unity game using `EnableMouseInPointer`

## How It Works

This fix has two layers:

### Layer 1: EnableMouseInPointer Implementation

Based on the [PEAK CrossOver Mouse Fix](https://github.com/kiku-jw/peak-crossover-mouse-fix) by [@kiku-jw](https://github.com/kiku-jw). This patch implements the `EnableMouseInPointer` API by intercepting `WM_MOUSE` events in Wine's message pipeline and converting them to `WM_POINTER` events. Three files are patched:

- `win32u.dll` (x86_64-windows) - EnableMouseInPointer entry point
- `win32u.so` (x86_64-unix) - Message conversion in `process_mouse_message()`
- `user32.dll` (x86_64-windows) - `GetPointerInfo()` implementation

**All three files must be installed together.** A partial install causes Wine instability (conhost.exe infinite loop).

Note: `user32.dll` does not exist in stock CrossOver 26.0 for x86_64 - it must be *added*, not replaced.

### Layer 2: Drag-and-Drop Fix

The PEAK patch has a bug: when converting `WM_MOUSEMOVE` to `WM_POINTERUPDATE`, it only sets `POINTER_MESSAGE_FLAG_INRANGE`. On Windows, when a mouse button is held during movement (dragging), the pointer update also carries `POINTER_MESSAGE_FLAG_INCONTACT` and the corresponding button flag. Without these, Unity sees a hovering pointer instead of a drag.

This fix adds button-state checks to the `WM_MOUSEMOVE` handler by reading `msg->wParam` for `MK_LBUTTON`, `MK_RBUTTON`, and `MK_MBUTTON`, and setting the correct flags.

The fix is applied as a binary patch (42 bytes of x86_64 assembly injected into a code cave) to preserve ABI compatibility with the rest of CrossOver.

See [`patches/02-fix-drag-incontact.patch`](patches/02-fix-drag-incontact.patch) for the source-level equivalent.

## Other CrossOver Versions

For CrossOver versions other than 26.0, you'll need updated PEAK binaries for your version, then apply the drag fix on top:

```bash
python3 patch_dragfix.py /path/to/peak-patched/win32u.so /path/to/output/win32u.so
```

The patcher automatically finds the correct patch site and a suitable code cave.

## Requirements

- CrossOver 26.0 (pre-patched binaries included)
- macOS (Intel or Apple Silicon)
- Python 3 (only needed if using `patch_dragfix.py` for other versions)

## Credits

- [PEAK CrossOver Mouse Fix](https://github.com/kiku-jw/peak-crossover-mouse-fix) by [@kiku-jw](https://github.com/kiku-jw) - the original EnableMouseInPointer implementation that makes this possible
- [Wine Bug #53847](https://bugs.winehq.org/show_bug.cgi?id=53847) - upstream tracking issue
- [rbernon (CodeWeavers)](https://gitlab.winehq.org/rbernon) - upstream Wine EnableMouseInPointer work

## License

The Wine patches are under the LGPL-2.1 license, consistent with Wine's licensing.
