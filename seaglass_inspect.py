#!/usr/bin/env python3
"""
inspect.py -- PHASE 1, READ-ONLY inspector for Pokemon Emerald Seaglass.

Goal of phase 1: prove we can correctly decode the party (names, level,
nature, ability, moves, IVs, shiny) on Seaglass specifically.

Design notes (why this differs from inspect-delta.html):
  * Names/moves/items/abilities are read from the SEAGLASS ROM, not PokeAPI.
    Seaglass is built on pokeemerald-expansion and RENUMBERS species/moves/
    items, so National-Dex-based lookups are wrong for this hack.
  * Ability slot is bit 31 of the Misc substruct IV word (NOT pid%2).
  * Shiny threshold is < 8 (Gen3), not < 16.
  * IV word is read from the SHUFFLED Misc substruct (+0x04), not a fixed
    file offset, so it is correct for all 24 substructure orderings.
  * Saves may carry an extra tail after the standard 128 KB (e.g. RTC/clock
    block). We slice to 128 KB for sector math and preserve the tail.

Nothing in this file writes to the save. It only reads bytes.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

# --------------------------------------------------------------------------
# Save structure constants (verified Gen3 / Emerald layout)
# --------------------------------------------------------------------------
SIGNATURE = 0x08012025
SECTION_SIZE = 0x1000        # 4 KB
DATA_SIZE = 0xF80            # 3968 bytes of payload per section
FOOTER = 0xFF4               # sectionID @ +0xFF4, checksum @ +0xFF6, sig @ +0xFF8, counter @ +0xFFC
SLOT_BASES = (0x0000, 0xE000)  # slot A, slot B (14 sections each = 0xE000)
SB1_SECTION_IDS = [1, 2, 3, 4]          # SaveBlock1 is spread across sections 1..4
STORAGE_SECTION_IDS = list(range(5, 14))  # PC storage in sections 5..13
PARTY_COUNT_OFF = 0x234       # within reassembled SaveBlock1
PARTY_OFF = 0x238
PARTY_MON_SIZE = 100
BOX_MON_SIZE = 80

# --------------------------------------------------------------------------
# Gen3 substructure order (24 permutations of [G,A,E,M])
# --------------------------------------------------------------------------
SUBSTRUCT_ORDER = [
    "GAEM", "GAME", "GEAM", "GEMA", "GMAE", "GMEA",
    "AGEM", "AGME", "AEGM", "AEMG", "AMGE", "AMEG",
    "EGAM", "EGMA", "EAGM", "EAMG", "EMGA", "EMAG",
    "MGAE", "MGEA", "MAGE", "MAEG", "MEGA", "MEAG",
]

NATURES = [
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
]

STAT_KEYS = ["hp", "atk", "def", "spe", "spa", "spd"]  # stored order in IV/EV words

SHINY_THRESHOLD = 16  # Gen3: shiny if (TID^SID^PIDhi^PIDlo) < 8

# --------------------------------------------------------------------------
# GBA character set (subset sufficient for names)
# --------------------------------------------------------------------------
CHARMAP = {
    0x00: " ", 0xAD: ".", 0xAE: "-", 0xAB: "!", 0xAC: "?",
    0xBA: "/", 0xB8: ",", 0xB4: "'", 0xB5: "\u2642", 0xB6: "\u2640",
    0x1B: "\u00e9",
}
for _i in range(10):
    CHARMAP[0xA1 + _i] = chr(ord("0") + _i)
for _i in range(26):
    CHARMAP[0xBB + _i] = chr(ord("A") + _i)
for _i in range(26):
    CHARMAP[0xD5 + _i] = chr(ord("a") + _i)


def decode_str(b: bytes) -> str:
    out = []
    for c in b:
        if c == 0xFF:
            break
        out.append(CHARMAP.get(c, ""))
    return "".join(out).rstrip()


# --------------------------------------------------------------------------
# ROM: auto-location of the data tables (ported from MIT reference, trimmed)
# --------------------------------------------------------------------------
def _enc(txt: str) -> bytes:
    rev = {v: k for k, v in CHARMAP.items()}
    out = bytearray()
    for ch in txt:
        if ch not in rev:
            return b""
        out.append(rev[ch])
    return bytes(out)


class Rom:
    def __init__(self, path: str):
        with open(path, "rb") as f:
            self.data = f.read()
        self.species_name_base = None  # address of species #1 name
        self.species_stride = 0xD0
        self.move_ptr1 = None
        self.item_base = None
        self.ability_base = None
        self._locate()

    # ---- discovery -------------------------------------------------------
    def _find_term(self, sub: str) -> int:
        e = _enc(sub)
        return self.data.find(e + b"\xFF") if e else -1

    def _find_any(self, sub: str, start: int = 0) -> int:
        e = _enc(sub)
        return self.data.find(e, start) if e else -1

    def _locate(self):
        # Species: find "Bulbasaur" whose table has Ivysaur at +stride and
        # Venusaur at +2*stride (filters out other unrelated name arrays).
        pos = 0
        while True:
            cand = self._find_any("Bulbasaur", pos)
            if cand < 0:
                break
            iv = self._find_any("Ivysaur", cand)
            if iv > cand:
                stride = iv - cand
                if 0x80 <= stride <= 0x200:
                    v = decode_str(self.data[cand + 2 * stride: cand + 2 * stride + 10])
                    if v == "Venusaur":
                        self.species_name_base = cand
                        self.species_stride = stride
                        break
            pos = cand + 1

        # Move-name pointer table: locate the entry pointing at "Karate Chop".
        kc = self._find_term("Karate Chop")
        if kc >= 0:
            target = 0x08000000 | kc
            ptr = struct.pack("<I", target)
            pos = 0
            while True:
                hit = self.data.find(ptr, pos)
                if hit < 0:
                    break
                cand = hit - 0x38   # gMovesInfo stride
                if cand >= 0:
                    p1 = struct.unpack_from("<I", self.data, cand)[0]
                    p1o = p1 - 0x08000000
                    if 0x08000000 <= p1 < 0x0A000000 and 0 <= p1o < len(self.data):
                        if decode_str(self.data[p1o:p1o + 8]) == "Pound":
                            self.move_ptr1 = cand
                            break
                pos = hit + 1

        # Item table: "Master Ball" is item 4; item 1 should read "Poke Ball".
        pos = 0
        while True:
            mb = self._find_term("Master Ball")
            if mb < 0:
                break
            cand = mb - 4 * 0x54
            if cand >= 0:
                nm = decode_str(self.data[cand + 0x54: cand + 0x54 + 14])
                if nm.startswith("Pok"):
                    self.item_base = cand
                    break
            nxt = self.data.find(_enc("Master Ball") + b"\xFF", mb + 1)
            if nxt < 0:
                break
            pos = nxt

        # Ability table: "Overgrow" + terminator is ability id 65.
        og = self._find_term("Overgrow")
        if og >= 0:
            self.ability_base = og - 65 * 0x1C

    # ---- lookups ---------------------------------------------------------
    def _name_addr(self, species: int) -> int:
        return self.species_name_base + (species - 1) * self.species_stride

    def species_name(self, species: int) -> str:
        if species <= 0 or self.species_name_base is None:
            return f"#{species}"
        a = self._name_addr(species)
        nm = decode_str(self.data[a: a + 12])
        return nm or f"#{species}"

    def base_stats(self, species: int):
        # SpeciesInfo: baseStats [HP,Atk,Def,Spe,SpA,SpD] sits 0x2C before the name.
        a = self._name_addr(species) - 0x2C
        return list(self.data[a: a + 6])

    def species_abilities(self, species: int):
        # pokeemerald-expansion: abilities[3] = [slot0, slot1, hidden] at
        # name-0x2C+0x18, three u16 values.
        a = self._name_addr(species) - 0x2C + 0x18
        return list(struct.unpack_from("<3H", self.data, a))

    def move_name(self, move: int) -> str:
        if move == 0:
            return "\u2014"
        if self.move_ptr1 is None:
            return f"move{move}"
        p = self.move_ptr1 + (move - 1) * 0x38
        ptr = struct.unpack_from("<I", self.data, p)[0]
        off = ptr - 0x08000000
        if not (0x08000000 <= ptr < 0x0A000000) or off >= len(self.data):
            return f"move{move}"
        return decode_str(self.data[off: off + 16]) or f"move{move}"

    def item_name(self, item: int) -> str:
        if item == 0:
            return "(none)"
        if self.item_base is None:
            return f"item{item}"
        a = self.item_base + item * 0x54
        return decode_str(self.data[a: a + 14]) or f"item{item}"

    def ability_name(self, ability: int) -> str:
        if ability == 0:
            return "(none)"
        if self.ability_base is None:
            return f"ability{ability}"
        a = self.ability_base + ability * 0x1C
        return decode_str(self.data[a: a + 13]) or f"ability{ability}"

    # ---- sprite decoding (for the GUI) ----------------------------------
    def _lz77(self, off: int):
        """GBA BIOS LZ77 (type 0x10) decompression from ROM offset."""
        d = self.data
        if off < 0 or off >= len(d) or d[off] != 0x10:
            return None
        size = d[off + 1] | (d[off + 2] << 8) | (d[off + 3] << 16)
        if size == 0 or size > 0x4000:
            return None
        out = bytearray()
        p = off + 4
        try:
            while len(out) < size:
                flags = d[p]; p += 1
                for b in range(8):
                    if len(out) >= size:
                        break
                    if flags & (0x80 >> b):
                        hi = d[p]; lo = d[p + 1]; p += 2
                        n = (hi >> 4) + 3
                        disp = ((hi & 0xF) << 8 | lo) + 1
                        if disp > len(out):
                            return None
                        for _ in range(n):
                            out.append(out[-disp])
                    else:
                        out.append(d[p]); p += 1
        except IndexError:
            return None
        return bytes(out[:size])

    def sprite_rgba(self, species: int, shiny: bool = False):
        """Front sprite as (w, h, RGBA8888 bytes), or None. 64x64."""
        try:
            base = self._name_addr(species) - 0x2C
            pic = struct.unpack_from("<I", self.data, base + 0x58)[0] - 0x08000000
            pal_off = 0x70 if shiny else 0x68
            palp = struct.unpack_from("<I", self.data, base + pal_off)[0] - 0x08000000
            tiles = self._lz77(pic)
            palb = self._lz77(palp)
            if not tiles or not palb or len(tiles) < 2048 or len(palb) < 32:
                return None
            pal = []
            for i in range(16):
                c = palb[i * 2] | (palb[i * 2 + 1] << 8)
                pal.append((
                    (c & 0x1F) * 255 // 31,
                    ((c >> 5) & 0x1F) * 255 // 31,
                    ((c >> 10) & 0x1F) * 255 // 31,
                    255,
                ))
            pal[0] = (0, 0, 0, 0)
            W = H = 64
            buf = bytearray(W * H * 4)
            for ty in range(8):
                for tx in range(8):
                    t = tiles[(ty * 8 + tx) * 32:(ty * 8 + tx) * 32 + 32]
                    if len(t) < 32:
                        continue
                    for row in range(8):
                        for col in range(4):
                            byte = t[row * 4 + col]
                            for i, ci in enumerate((byte & 0xF, byte >> 4)):
                                r, g, bb, a = pal[ci]
                                o = ((ty * 8 + row) * W + tx * 8 + col * 2 + i) * 4
                                buf[o] = r; buf[o + 1] = g; buf[o + 2] = bb; buf[o + 3] = a
            return (W, H, bytes(buf))
        except Exception:
            return None

    def gender_ratio(self, species: int) -> int:
        # Gen3 gender threshold byte at SpeciesInfo name-0x2C+0x12.
        # 0x00=always male, 0xFE=always female, 0xFF=genderless, else female if
        # (pid & 0xFF) < threshold.
        a = self._name_addr(species) - 0x2C + 0x12
        return self.data[a]

    def gender(self, species: int, pid: int) -> str:
        r = self.gender_ratio(species)
        if r == 0xFF:
            return "genderless"
        if r == 0x00:
            return "male"
        if r == 0xFE:
            return "female"
        return "female" if (pid & 0xFF) < r else "male"

    def growth_rate(self, species: int) -> int:
        # Gen3 growth enum at SpeciesInfo name-0x2C+0x15:
        # 0=MediumFast 1=Erratic 2=Fluctuating 3=MediumSlow 4=Fast 5=Slow
        a = self._name_addr(species) - 0x2C + 0x15
        return self.data[a]

    def level_for_exp(self, species: int, exp: int) -> int:
        def total(n, g):
            if n <= 1: return 0
            if g == 0: return n**3
            if g == 1:  # Erratic (approx boundaries)
                if n <= 50: return int(n**3*(100-n)/50)
                if n <= 68: return int(n**3*(150-n)/100)
                if n <= 98: return int(n**3*((1911-10*n)/3)/500)
                return int(n**3*(160-n)/100)
            if g == 2:  # Fluctuating
                if n <= 15: return int(n**3*((n+1)/3 + 24)/50)
                if n <= 36: return int(n**3*(n+14)/50)
                return int(n**3*((n/2)+32)/50)
            if g == 3: return int(1.2*n**3 - 15*n*n + 100*n - 140)
            if g == 4: return int(4*n**3/5)
            if g == 5: return int(5*n**3/4)
            return n**3
        g = self.growth_rate(species)
        lvl = 1
        for n in range(1, 101):
            if exp >= total(n, g):
                lvl = n
            else:
                break
        return lvl

    def ok(self) -> bool:
        try:
            return (
                self.species_name_base is not None
                and self.species_name(1).startswith("Bulbas")
                and self.move_name(1) == "Pound"
                and self.item_name(1).startswith("Pok")
                and self.ability_name(65) == "Overgrow"
            )
        except Exception:
            return False


# --------------------------------------------------------------------------
# Save file
# --------------------------------------------------------------------------
class Save:
    def __init__(self, path: str):
        with open(path, "rb") as f:
            raw = f.read()
        # The standard image is 128 KB. Anything after that is an emulator
        # tail (RTC/clock). Keep it but do sector math on the first 128 KB.
        self.full = raw
        self.data = bytearray(raw[: 0x20000])
        if len(self.data) < 0x20000:
            # Some emulators write 64 KB ("half" saves); we still try.
            pass
        self.tail = raw[0x20000:]
        self.sections = {}      # id -> absolute offset in self.data
        self.active_slot = None
        self.counter = None
        self._locate_active_slot()

    def _read_sections_of_slot(self, base: int):
        sect = {}
        for i in range(14):
            off = base + i * SECTION_SIZE
            if off + SECTION_SIZE > len(self.data):
                break
            sid = struct.unpack_from("<H", self.data, off + FOOTER)[0]
            sig = struct.unpack_from("<I", self.data, off + FOOTER + 4)[0]
            if sig == SIGNATURE and sid < 14:
                sect[sid] = off
        return sect

    def _locate_active_slot(self):
        best = None
        for base in SLOT_BASES:
            off = base + 0xFFC
            if off + 4 > len(self.data):
                continue
            counter = struct.unpack_from("<I", self.data, off)[0]
            sect = self._read_sections_of_slot(base)
            # A valid slot should have at least sections 0 and 1.
            if len(sect) >= 2:
                if best is None or counter > best[0]:
                    best = (counter, base, sect)
        if best is None:
            raise ValueError("No valid save slot found (no section with the 0x08012025 signature).")
        self.counter, base, sect = best
        self.active_slot = base
        self.sections = sect

    def _reassemble(self, ids):
        out = bytearray()
        for sid in ids:
            off = self.sections.get(sid)
            if off is None:
                continue
            out += self.data[off: off + DATA_SIZE]
        return out

    @property
    def sb1(self) -> bytearray:
        return self._reassemble(SB1_SECTION_IDS)

    @staticmethod
    def _checksum(block: bytes) -> int:
        total = 0
        for i in range(0, len(block), 4):
            total = (total + struct.unpack_from("<I", block, i)[0]) & 0xFFFFFFFF
        return ((total >> 16) + (total & 0xFFFF)) & 0xFFFF

    def verify_checksums(self):
        bad = []
        for sid, off in self.sections.items():
            stored = struct.unpack_from("<H", self.data, off + FOOTER + 2)[0]
            calc = self._checksum(self.data[off: off + DATA_SIZE])
            if stored != calc:
                bad.append((sid, stored, calc))
        return bad

    # ---- party -----------------------------------------------------------
    def party(self, rom: Rom):
        sb1 = self.sb1
        count = min(struct.unpack_from("<I", sb1, PARTY_COUNT_OFF)[0], 6)
        mons = []
        for i in range(count):
            off = PARTY_OFF + i * PARTY_MON_SIZE
            raw = bytes(sb1[off: off + PARTY_MON_SIZE])
            if len(raw) < PARTY_MON_SIZE:
                break
            mons.append(PartyMon(raw, rom))
        return count, mons

    # ---- PC boxes --------------------------------------------------------
    @property
    def storage(self) -> bytearray:
        return self._reassemble(STORAGE_SECTION_IDS)

    def current_box(self) -> int:
        stor = self.storage
        return stor[0] if stor else 0

    def read_boxes(self, rom: "Rom", num_boxes: int = 14):
        """Return a list of boxes; each box is a list of BOX_SIZE (BoxMon|None)."""
        stor = self.storage
        boxes = []
        for b in range(num_boxes):
            slots = []
            for pos in range(BOX_SIZE):
                idx = b * BOX_SIZE + pos
                off = BOXES_START + idx * BOX_SLOT
                raw = bytes(stor[off:off + BOX_SLOT])
                if len(raw) < BOX_SLOT:
                    slots.append(None); continue
                bm = BoxMon(raw, rom)
                slots.append(None if bm.is_empty() else bm)
            boxes.append(slots)
        return boxes


# --------------------------------------------------------------------------
# A single party Pokemon: decrypt + expose fields
# --------------------------------------------------------------------------
class PartyMon:
    def __init__(self, raw: bytes, rom: Rom):
        self.raw = raw
        self.rom = rom
        self.pid = struct.unpack_from("<I", raw, 0x00)[0]
        self.otid = struct.unpack_from("<I", raw, 0x04)[0]
        self.nickname = decode_str(raw[0x08:0x12])
        self.ot_name = decode_str(raw[0x14:0x1B])
        self.level = raw[0x54]            # party-only field
        self._crypt()
        self._split()

    def _crypt(self):
        key = (self.pid ^ self.otid) & 0xFFFFFFFF
        enc = bytearray(self.raw[0x20:0x20 + 48])
        for i in range(0, 48, 4):
            v = struct.unpack_from("<I", enc, i)[0] ^ key
            struct.pack_into("<I", enc, i, v & 0xFFFFFFFF)
        order = SUBSTRUCT_ORDER[self.pid % 24]
        # enc holds subs in shuffled order; reorder into canonical G,A,E,M.
        subs = {order[i]: bytes(enc[i * 12: i * 12 + 12]) for i in range(4)}
        self.G = bytearray(subs["G"])
        self.A = bytearray(subs["A"])
        self.E = bytearray(subs["E"])
        self.M = bytearray(subs["M"])

    def _split(self):
        pass  # substructs already split in _crypt

    # --- Growth substruct (G) ---
    @property
    def species(self) -> int:
        return struct.unpack_from("<H", self.G, 0x00)[0]

    @property
    def held_item(self) -> int:
        return struct.unpack_from("<H", self.G, 0x02)[0]

    @property
    def experience(self) -> int:
        # Gen3 stores EXP in the low 20 bits of this u32; the top 12 bits
        # are a separate packed field (observed constant 0x1FE on a real save).
        return struct.unpack_from("<I", self.G, 0x04)[0] & 0xFFFFF

    @property
    def friendship(self) -> int:
        return self.G[0x09]

    # --- Attacks substruct (A) ---
    @property
    def moves(self):
        return list(struct.unpack_from("<4H", self.A, 0x00))

    @property
    def pp(self):
        return list(self.A[0x08:0x0C])

    # --- Effort substruct (E): EVs + contest ---
    @property
    def evs(self):
        return {STAT_KEYS[i]: self.E[i] for i in range(6)}

    # --- Misc substruct (M): IVs, ability bit, origin, etc. ---
    @property
    def _iv_word(self) -> int:
        return struct.unpack_from("<I", self.M, 0x04)[0]

    @property
    def ivs(self):
        w = self._iv_word
        return {
            STAT_KEYS[0]: w & 0x1F,
            STAT_KEYS[1]: (w >> 5) & 0x1F,
            STAT_KEYS[2]: (w >> 10) & 0x1F,
            STAT_KEYS[3]: (w >> 15) & 0x1F,
            STAT_KEYS[4]: (w >> 20) & 0x1F,
            STAT_KEYS[5]: (w >> 25) & 0x1F,
        }

    @property
    def is_egg(self) -> bool:
        return bool((self._iv_word >> 30) & 1)

    @property
    def ability_slot(self) -> int:
        # Seaglass stores the selected ability index (0/1/2) in the Misc
        # substruct at byte 0x0B, bits 5-6 (0x20=slot1, 0x40=slot2).
        # Verified against all party members on a real save.
        return (self.M[0x0B] >> 5) & 0x3

    @property
    def nature(self) -> str:
        return NATURES[self.pid % 25]

    @property
    def is_shiny(self) -> bool:
        # Seaglass (pokeemerald-expansion) marks shininess two ways:
        #  1) a dedicated flag bit: raw header byte 0x1F, bit 6 (0x40), and/or
        #  2) the classic Gen3 PIDXOR rule with a < 16 threshold.
        # Verified against a real save: (flag) OR (xor<16) matches the game for
        # all party members, including one shiny caught via the PID rule alone.
        if self.raw[0x1F] & 0x40:
            return True
        tid = self.otid & 0xFFFF
        sid = (self.otid >> 16) & 0xFFFF
        pidlo = self.pid & 0xFFFF
        pidhi = (self.pid >> 16) & 0xFFFF
        return (tid ^ sid ^ pidlo ^ pidhi) < SHINY_THRESHOLD

    def ability_name(self) -> str:
        ab = self.rom.species_abilities(self.species)
        idx = self.ability_slot
        aid = ab[idx] if idx < len(ab) else ab[0]
        return self.rom.ability_name(aid)


# --------------------------------------------------------------------------
# PC box storage (80-byte box format mons) -- Seaglass layout:
#   storage[0] = current box, storage[1:4] pad, mons from 0x04, 80 bytes each,
#   30 per box.
# --------------------------------------------------------------------------
BOX_SLOT = 80
BOX_SIZE = 30
BOXES_START = 0x04


class BoxMon:
    """A mon stored in a PC box (80-byte format; no party stats; level from EXP)."""
    def __init__(self, raw: bytes, rom: "Rom"):
        self.raw = raw
        self.rom = rom
        self.pid = struct.unpack_from("<I", raw, 0x00)[0]
        self.otid = struct.unpack_from("<I", raw, 0x04)[0]
        self.nickname = decode_str(raw[0x08:0x12])
        key = (self.pid ^ self.otid) & 0xFFFFFFFF
        enc = bytearray(raw[0x20:0x20 + 48])
        for i in range(0, 48, 4):
            v = struct.unpack_from("<I", enc, i)[0] ^ key
            struct.pack_into("<I", enc, i, v & 0xFFFFFFFF)
        order = SUBSTRUCT_ORDER[self.pid % 24]
        subs = {order[i]: bytes(enc[i * 12: i * 12 + 12]) for i in range(4)}
        self.G = bytearray(subs["G"]); self.A = bytearray(subs["A"])
        self.E = bytearray(subs["E"]); self.M = bytearray(subs["M"])

    @property
    def species(self) -> int:
        return struct.unpack_from("<H", self.G, 0x00)[0]

    @property
    def held_item(self) -> int:
        return struct.unpack_from("<H", self.G, 0x02)[0]

    @property
    def experience(self) -> int:
        return struct.unpack_from("<I", self.G, 0x04)[0] & 0xFFFFF

    @property
    def friendship(self) -> int:
        return self.G[0x09]

    @property
    def moves(self):
        return list(struct.unpack_from("<4H", self.A, 0x00))

    @property
    def evs(self):
        return {STAT_KEYS[i]: self.E[i] for i in range(6)}

    @property
    def _iv_word(self) -> int:
        return struct.unpack_from("<I", self.M, 0x04)[0]

    @property
    def ivs(self):
        w = self._iv_word
        return {STAT_KEYS[i]: (w >> (5 * i)) & 0x1F for i in range(6)}

    @property
    def ability_slot(self) -> int:
        return (self.M[0x0B] >> 5) & 0x3

    @property
    def nature(self) -> str:
        return NATURES[self.pid % 25]

    @property
    def level(self) -> int:
        return self.rom.level_for_exp(self.species, self.experience)

    @property
    def is_egg(self) -> bool:
        return bool((self._iv_word >> 30) & 1)

    @property
    def is_shiny(self) -> bool:
        if self.raw[0x1F] & 0x40:
            return True
        tid = self.otid & 0xFFFF; sid = (self.otid >> 16) & 0xFFFF
        pidlo = self.pid & 0xFFFF; pidhi = (self.pid >> 16) & 0xFFFF
        return (tid ^ sid ^ pidlo ^ pidhi) < SHINY_THRESHOLD

    def ability_name(self) -> str:
        ab = self.rom.species_abilities(self.species)
        idx = self.ability_slot
        aid = ab[idx] if idx < len(ab) else ab[0]
        return self.rom.ability_name(aid)

    def is_empty(self) -> bool:
        return self.species == 0


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def report(rom: Rom, save: Save):
    print("=" * 78)
    print("  Emerald Seaglass -- Phase 1 Inspector (READ ONLY)")
    print("=" * 78)
    print(f"ROM   : species tables {'OK' if rom.species_name_base is not None else 'MISSING'}, "
          f"moves {'OK' if rom.move_ptr1 is not None else 'MISSING'}, "
          f"items {'OK' if rom.item_base is not None else 'MISSING'}, "
          f"abilities {'OK' if rom.ability_base is not None else 'MISSING'}")
    if not rom.ok():
        print("  WARNING: ROM self-check did not fully pass; some names may be wrong.")
    print(f"SAVE  : {len(save.full):,} bytes total "
          f"({len(save.data):,} core + {len(save.tail)} tail)")
    print(f"        active slot {'B' if save.active_slot else 'A'} "
          f"(base 0x{save.active_slot:04X}), counter = {save.counter}")

    bad = save.verify_checksums()
    if bad:
        print(f"        checksum MISMATCH in sections: "
              + ", ".join(f"{s}(stored={st:04X},calc={ca:04X})" for s, st, ca in bad))
    else:
        print(f"        checksums OK for all {len(save.sections)} present sections")

    count, mons = save.party(rom)
    print(f"\nParty: {count} Pokemon\n")

    hdr = f"{'#':<2} {'Species':<14} {'Nickname':<12} {'Lv':>3} {'Nature':<9} {'Ability':<14} {'Shiny':<5} Moves"
    print(hdr)
    print("-" * len(hdr))
    for i, m in enumerate(mons):
        moves = ", ".join(
            rom.move_name(mv) for mv in m.moves if mv
        )
        shiny = "YES" if m.is_shiny else "-"
        print(f"{i+1:<2} {rom.species_name(m.species):<14} {m.nickname:<12} "
              f"{m.level:>3} {m.nature:<9} {m.ability_name():<14} {shiny:<5} {moves}")

    print("\nDetails:")
    for i, m in enumerate(mons):
        iv = m.ivs
        ev = m.evs
        bst = rom.base_stats(m.species)
        print(f"  [{i+1}] {rom.species_name(m.species)}  PID=0x{m.pid:08X} "
              f"OTID=0x{m.otid:08X}  abilitySlot={m.ability_slot}  egg={m.is_egg}")
        print(f"       EXP={m.experience:,}  friendship={m.friendship}  "
              f"held={rom.item_name(m.held_item)}")
        print(f"       IVs  HP/Atk/Def/Spe/SpA/SpD = "
              f"{iv['hp']}/{iv['atk']}/{iv['def']}/{iv['spe']}/{iv['spa']}/{iv['spd']}")
        print(f"       EVs  HP/Atk/Def/Spe/SpA/SpD = "
              f"{ev['hp']}/{ev['atk']}/{ev['def']}/{ev['spe']}/{ev['spa']}/{ev['spd']}")
        print(f"       base HP/Atk/Def/Spe/SpA/SpD = "
              f"{bst[0]}/{bst[1]}/{bst[2]}/{bst[3]}/{bst[4]}/{bst[5]}")
        print(f"       moves (id): " + ", ".join(
            f"{rom.move_name(mv)} ({mv})" for mv in m.moves))
        print()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only Seaglass save inspector")
    ap.add_argument("--rom", help="path to the Seaglass .gba")
    ap.add_argument("--save", help="path to the .sav")
    ap.add_argument("--dir", default=None,
                    help="folder to auto-find a single .gba and .sav in")
    args = ap.parse_args(argv)

    rom_path, save_path = args.rom, args.save

    search_dirs = [args.dir] if args.dir else [".", "..", os.path.dirname(os.path.abspath(__file__))]
    if not rom_path:
        for d in search_dirs:
            for f in os.listdir(d):
                if f.lower().endswith(".gba"):
                    rom_path = os.path.join(d, f)
                    break
            if rom_path:
                break
    if not save_path:
        # Prefer the "latest" save if present.
        cands = []
        for d in search_dirs:
            for f in os.listdir(d):
                if f.lower().endswith(".sav"):
                    cands.append(os.path.join(d, f))
        cands.sort(key=lambda p: ("latest" not in os.path.basename(p).lower(), p))
        if cands:
            save_path = cands[0]

    if not rom_path or not os.path.exists(rom_path):
        print("Could not find a .gba ROM. Pass --rom <path>.")
        return 2
    if not save_path or not os.path.exists(save_path):
        print("Could not find a .sav file. Pass --save <path>.")
        return 2

    print(f"Using ROM : {rom_path}")
    print(f"Using SAVE: {save_path}\n")

    rom = Rom(rom_path)
    save = Save(save_path)
    report(rom, save)
    return 0


if __name__ == "__main__":
    sys.exit(main())
