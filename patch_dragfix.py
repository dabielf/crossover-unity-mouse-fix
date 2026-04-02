#!/usr/bin/env python3
"""
CrossOver Unity Mouse Fix — Drag Fix Binary Patcher

Patches a PEAK-patched win32u.so to fix drag-and-drop and hold-to-fire
by adding INCONTACT + button flags to WM_POINTERUPDATE during mouse drag.

The PEAK patch converts WM_MOUSEMOVE to WM_POINTERUPDATE but only sets
POINTER_MESSAGE_FLAG_INRANGE. This patcher adds checks for MK_LBUTTON,
MK_RBUTTON, and MK_MBUTTON in msg->wParam and sets the corresponding
INCONTACT + button flags.

Technique: Code cave injection into __TEXT,__const section padding.

Usage:
    python3 patch_dragfix.py <input_win32u.so> [output_win32u.so]

If no output path is given, writes to <input>_dragfix.so.
"""

import struct
import sys
import os


def find_pattern(data, pattern):
    """Find first occurrence of byte pattern in data."""
    idx = data.find(pattern)
    if idx == -1:
        return None
    return idx


def find_code_cave(data, min_size, search_start, search_end):
    """Find a run of zero bytes of at least min_size in the given range."""
    i = search_start
    while i < search_end:
        if data[i] == 0:
            start = i
            while i < search_end and data[i] == 0:
                i += 1
            if i - start >= min_size:
                return start
        else:
            i += 1
    return None


def patch_dragfix(input_path, output_path):
    with open(input_path, 'rb') as f:
        data = bytearray(f.read())

    print(f"Loaded: {input_path} ({len(data)} bytes)")

    # === Locate the WM_MOUSEMOVE handler ===
    # Pattern: the PEAK patch sets message = WM_POINTERUPDATE (0x245),
    # loads info->pointerFlags, ORs with INRANGE (0x2), stores, and jumps.
    #
    # We search for the specific byte sequence:
    #   orl $0x2, %ecx          (83 c9 02)
    #   movl %ecx, 0xc(%rax)    (89 48 0c)
    #   jmp <rel32>             (e9 xx xx xx xx)
    #
    # Preceded by the WM_POINTERUPDATE assignment:
    #   movl $0x245, <stack>    (c7 85 xx xx xx xx 45 02 00 00)

    # First find the POINTERUPDATE constant to narrow the search
    pointer_update_sig = bytes([0x45, 0x02, 0x00, 0x00])  # $0x245 little-endian

    # The WM_MOUSEMOVE handler: orl $0x2, %ecx; movl %ecx, 0xc(%rax); jmp rel32
    mousemove_pattern = bytes([
        0x83, 0xc9, 0x02,              # orl $0x2, %ecx
        0x89, 0x48, 0x0c,              # movl %ecx, 0xc(%rax)
        0xe9                            # jmp (first byte)
    ])

    # The WM_POINTERDOWN handler follows immediately (used to verify context):
    pointerdown_sig = bytes([0x46, 0x02, 0x00, 0x00])  # $0x246 = WM_POINTERDOWN

    # Search for the pattern
    patch_site = None
    pos = 0
    while True:
        idx = data.find(mousemove_pattern, pos)
        if idx == -1:
            break
        # Verify: the jmp is followed by a 4-byte offset, then WM_POINTERDOWN case
        jmp_end = idx + 11  # 3 + 3 + 5 bytes
        # Check a few bytes after for the 0x246 constant (WM_POINTERDOWN)
        nearby = data[jmp_end:jmp_end + 30]
        if pointerdown_sig in nearby:
            # Also verify WM_POINTERUPDATE (0x245) appears shortly before
            context_before = data[max(0, idx - 20):idx]
            if pointer_update_sig in context_before:
                patch_site = idx
                break
        pos = idx + 1

    if patch_site is None:
        print("ERROR: Could not find the WM_MOUSEMOVE handler pattern.")
        print("This binary may not have the PEAK EnableMouseInPointer patch applied,")
        print("or the binary layout differs from the expected version.")
        sys.exit(1)

    # Extract the original jmp offset
    jmp_offset_bytes = data[patch_site + 7:patch_site + 11]
    jmp_rel32 = struct.unpack('<i', jmp_offset_bytes)[0]
    jmp_target = (patch_site + 6 + 5) + jmp_rel32  # jmp is at patch_site+6, 5 bytes long
    # Actually: jmp starts at patch_site+6 (after orl+movl), offset from patch_site+6+5
    # Wait, let me recalculate:
    # patch_site+0: orl (3 bytes)
    # patch_site+3: movl (3 bytes)
    # patch_site+6: jmp (5 bytes: e9 + rel32)
    # jmp target = (patch_site + 6 + 5) + jmp_rel32
    jmp_target = (patch_site + 11) + jmp_rel32

    print(f"Found WM_MOUSEMOVE handler at 0x{patch_site:x}")
    print(f"  Original jmp target: 0x{jmp_target:x}")

    # Check if already patched (first byte would be e9 jmp, not 83 orl)
    if data[patch_site] == 0xe9:
        print("This binary appears to already have the drag fix applied.")
        sys.exit(0)

    # === Find a code cave ===
    # Look in the range after the code section for zero-filled padding
    # Typically in __TEXT,__const or similar sections
    cave_min_size = 50
    cave = find_code_cave(data, cave_min_size, patch_site + 0x10000, len(data))
    if cave is None:
        # Try searching before the code too
        cave = find_code_cave(data, cave_min_size, 0, patch_site)
    if cave is None:
        print("ERROR: Could not find a suitable code cave (50+ zero bytes).")
        sys.exit(1)

    print(f"Found code cave at 0x{cave:x}")

    # === Build the cave code ===
    cave_code = bytearray()

    # orl $0x2, %ecx  (INRANGE)
    cave_code += b'\x83\xc9\x02'

    # movq -0x10(%rbp), %rdx  (load msg pointer)
    cave_code += b'\x48\x8b\x55\xf0'

    # testb $0x1, 0x10(%rdx)  (MK_LBUTTON?)
    cave_code += b'\xf6\x42\x10\x01'
    # je +3
    cave_code += b'\x74\x03'
    # orl $0x14, %ecx  (INCONTACT | FIRSTBUTTON)
    cave_code += b'\x83\xc9\x14'

    # testb $0x2, 0x10(%rdx)  (MK_RBUTTON?)
    cave_code += b'\xf6\x42\x10\x02'
    # je +3
    cave_code += b'\x74\x03'
    # orl $0x24, %ecx  (INCONTACT | SECONDBUTTON)
    cave_code += b'\x83\xc9\x24'

    # testb $0x10, 0x10(%rdx)  (MK_MBUTTON?)
    cave_code += b'\xf6\x42\x10\x10'
    # je +3
    cave_code += b'\x74\x03'
    # orl $0x44, %ecx  (INCONTACT | THIRDBUTTON)
    cave_code += b'\x83\xc9\x44'

    # movl %ecx, 0xc(%rax)  (store pointerFlags)
    cave_code += b'\x89\x48\x0c'

    # jmp back to original target
    jmp_back_src = cave + len(cave_code)
    jmp_back_offset = jmp_target - (jmp_back_src + 5)
    cave_code += b'\xe9' + struct.pack('<i', jmp_back_offset)

    print(f"Cave code: {len(cave_code)} bytes")

    # === Build the trampoline ===
    jmp_to_cave_offset = cave - (patch_site + 5)
    trampoline = b'\xe9' + struct.pack('<i', jmp_to_cave_offset)
    trampoline += b'\x90' * 6  # NOP padding
    assert len(trampoline) == 11

    # === Apply patches ===
    data[patch_site:patch_site + 11] = trampoline
    data[cave:cave + len(cave_code)] = cave_code

    # === Write output ===
    with open(output_path, 'wb') as f:
        f.write(data)

    print(f"\nPatched binary written to: {output_path}")
    print(f"  Trampoline at 0x{patch_site:x}: jmp 0x{cave:x}")
    print(f"  Cave code at 0x{cave:x}: {len(cave_code)} bytes")
    print(f"  Jump back to 0x{jmp_target:x}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 patch_dragfix.py <input_win32u.so> [output_win32u.so]")
        print("")
        print("Applies the drag-and-drop fix to a PEAK-patched win32u.so.")
        print("The input must already have the PEAK EnableMouseInPointer patch.")
        sys.exit(1)

    input_path = sys.argv[1]
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_dragfix{ext}"

    if not os.path.exists(input_path):
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    patch_dragfix(input_path, output_path)


if __name__ == '__main__':
    main()
