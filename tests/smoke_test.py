"""Headless smoke test for the Seaglass Save Editor core.

Runs without a display (Qt offscreen). Exercises:
  * imports of all modules
  * save checksum verification (if a sample save is present)
  * party + box decoding, save write with checksum revalidation
  * .pk3 export produces a 100-byte file with a valid checksum
  * a GUI construction + selection pass (offscreen)

Sample files (optional) are looked up via environment variables:
  SEAGLASS_SAVE  path to a .sav
  SEAGLASS_ROM   path to the .gba
If they are not set/found, the data-dependent parts are skipped and only the
import/construction checks run. Exits non-zero on any failure.
"""
import os
import sys
import struct

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

failures = []


def check(name, cond):
    status = "ok" if cond else "FAIL"
    print(f"[{status}] {name}")
    if not cond:
        failures.append(name)


def main():
    # 1. imports
    try:
        import seaglass_inspect as si
        import seaglass_write as sw
        import seaglass_editor as se
        check("import modules", True)
    except Exception as e:  # pragma: no cover
        check(f"import modules ({e})", False)
        return 1

    # 2. optional data path
    save_path = os.environ.get("SEAGLASS_SAVE")
    rom_path = os.environ.get("SEAGLASS_ROM")
    # 3. pk3 shiny-export self-test (needs only a sample shiny-by-flag pk3)
    run_pk3_tests(sw)

    if save_path and rom_path and os.path.exists(save_path) and os.path.exists(rom_path):
        run_data_tests(si, sw, se, save_path, rom_path)
    else:
        print("[skip] data tests (set SEAGLASS_SAVE and SEAGLASS_ROM to enable)")
        run_gui_construction(se)

    if failures:
        print(f"\n{len(failures)} check(s) FAILED")
        return 1
    print("\nall checks passed")
    return 0


def run_data_tests(si, sw, se, save_path, rom_path):
    rom = si.Rom(rom_path)
    save = si.Save(save_path)
    check("save checksums valid", not save.verify_checksums())

    n, party = save.party(rom)
    print(f"       party size: {n}")
    if party:
        m = party[0]
        # round-trip: write unchanged -> checksums still valid
        touched = sw.write_party_mon(save, 0, sw.EditableMon(m.raw, rom).to_raw())
        check("write party revalidates checksums", not save.verify_checksums())
        # gender string is non-empty
        check("gender derivable", isinstance(rom.gender(m.species, m.pid), str))
        # pk3 export
        data = sw.to_pk3(m.raw, level=m.level)
        check("pk3 is 100 bytes", len(data) == 100)
        pid = struct.unpack_from("<I", data, 0)[0]
        otid = struct.unpack_from("<I", data, 4)[0]
        key = pid ^ otid
        enc = bytearray(data[0x20:0x50])
        for i in range(0, 48, 4):
            struct.pack_into("<I", enc, i, struct.unpack_from("<I", enc, i)[0] ^ key)
        chk = sum(struct.unpack_from("<24H", bytes(enc), 0)) & 0xFFFF
        stored = struct.unpack_from("<H", data, 0x1C)[0]
        check("pk3 checksum valid", chk == stored)

    boxes = save.read_boxes(rom)
    check("14 boxes", len(boxes) == 14)


def run_gui_construction(se):
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        win = se.Editor()
        check("gui constructs", win is not None)
    except Exception as e:  # pragma: no cover
        check(f"gui constructs ({e})", False)


def run_pk3_tests(sw):
    """Verify to_pk3(want_shiny=True) produces a standard-shiny 100-byte file
    while leaving PID and the visible Trainer ID unchanged, and fixes lang."""
    import struct
    candidates = [
        os.path.join(ROOT, "junk", "sunny_Sunflora.pk3"),
        os.path.join(ROOT, "junk", "sunny_fixed.pk3"),
    ]
    sample = next((p for p in candidates if os.path.exists(p)), None)
    if not sample:
        print("[skip] pk3 shiny test (no sample pk3 in junk/)")
        return
    raw = open(sample, "rb").read()
    pid = struct.unpack_from("<I", raw, 0)[0]
    otid = struct.unpack_from("<I", raw, 4)[0]

    def xorv(p, o):
        return (p & 0xFFFF) ^ ((p >> 16) & 0xFFFF) ^ (o & 0xFFFF) ^ ((o >> 16) & 0xFFFF)

    out = sw.to_pk3(raw, want_shiny=True)
    pid2 = struct.unpack_from("<I", out, 0)[0]
    otid2 = struct.unpack_from("<I", out, 4)[0]
    check("pk3 want_shiny -> 100 bytes", len(out) == 100)
    check("pk3 want_shiny -> standard shiny (<8)", xorv(pid2, otid2) < 8)
    check("pk3 want_shiny keeps PID", pid == pid2)
    check("pk3 want_shiny keeps visible TID", (otid & 0xFFFF) == (otid2 & 0xFFFF))
    check("pk3 lang sanitized (1-7)", out[0x12] in (1, 2, 3, 4, 5, 6, 7))
    key = (pid2 ^ otid2) & 0xFFFFFFFF
    enc = bytearray(out[0x20:0x50])
    for i in range(0, 48, 4):
        struct.pack_into("<I", enc, i, struct.unpack_from("<I", enc, i)[0] ^ key)
    chk = sum(struct.unpack_from("<24H", bytes(enc), 0)) & 0xFFFF
    check("pk3 want_shiny checksum valid", chk == struct.unpack_from("<H", out, 0x1C)[0])


if __name__ == "__main__":
    sys.exit(main())
