"""
seaglass_write.py -- editing/writing helpers for Emerald Seaglass saves.

Builds on seaglass_inspect (read side) and adds:
  * PartyMon editing setters (nickname, level, exp, ability slot, held item,
    moves, IVs, EVs, friendship, shiny flag).
  * Re-serialization: rebuild the 4 substructs, re-shuffle per PID order,
    re-XOR-encrypt, write back into SaveBlock1, and recompute the checksums
    of any sector that changed.

Design rules:
  * We do NOT change PID or species (species editing is out of scope; changing
    PID would alter nature/shiny/sub-order). Nature is therefore read-only.
  * Shiny is toggled via the flag bit raw[0x1F] & 0x40 (verified in-game).
  * Only the sectors actually touched get their checksum recomputed.
  * Writes go to a NEW file; the caller decides the path.
"""

from __future__ import annotations

import struct

from seaglass_inspect import (
    Save, PartyMon, Rom,
    SUBSTRUCT_ORDER, STAT_KEYS, NATURES,
    SB1_SECTION_IDS, PARTY_OFF, PARTY_MON_SIZE, DATA_SIZE, FOOTER,
    decode_str, _enc, CHARMAP,
)


def encode_str(s: str, length: int) -> bytes:
    """Encode ASCII(ish) to the GBA charset, padded with 0xFF, exactly `length`."""
    rev = {v: k for k, v in CHARMAP.items()}
    out = bytearray()
    for ch in s[:length]:
        out.append(rev.get(ch, 0x00))
    # terminator then pad
    if len(out) < length:
        out.append(0xFF)
    while len(out) < length:
        out.append(0xFF)
    return bytes(out[:length])


class EditableMon:
    """Wraps a PartyMon's raw 100-byte slot and applies setters, then re-serializes."""

    def __init__(self, raw: bytes, rom: Rom):
        self.raw = bytearray(raw)
        self.rom = rom
        self.pid = struct.unpack_from("<I", self.raw, 0x00)[0]
        self.otid = struct.unpack_from("<I", self.raw, 0x04)[0]
        self._decrypt()

    # ---- crypto ----------------------------------------------------------
    def _decrypt(self):
        key = (self.pid ^ self.otid) & 0xFFFFFFFF
        enc = bytearray(self.raw[0x20:0x20 + 48])
        for i in range(0, 48, 4):
            v = struct.unpack_from("<I", enc, i)[0] ^ key
            struct.pack_into("<I", enc, i, v & 0xFFFFFFFF)
        order = SUBSTRUCT_ORDER[self.pid % 24]
        subs = {order[i]: bytes(enc[i * 12: i * 12 + 12]) for i in range(4)}
        self.G = bytearray(subs["G"])
        self.A = bytearray(subs["A"])
        self.E = bytearray(subs["E"])
        self.M = bytearray(subs["M"])

    def _encrypt_into_raw(self):
        """Re-shuffle G/A/E/M by PID order, XOR-encrypt, place at raw[0x20:0x50]."""
        order = SUBSTRUCT_ORDER[self.pid % 24]
        parts = {"G": self.G, "A": self.A, "E": self.E, "M": self.M}
        shuffled = bytearray()
        for ch in order:
            shuffled += parts[ch]
        key = (self.pid ^ self.otid) & 0xFFFFFFFF
        for i in range(0, 48, 4):
            v = struct.unpack_from("<I", shuffled, i)[0] ^ key
            struct.pack_into("<I", shuffled, i, v & 0xFFFFFFFF)
        self.raw[0x20:0x20 + 48] = shuffled[:48]

    # ---- setters ---------------------------------------------------------
    def set_nickname(self, s: str):
        self.raw[0x08:0x12] = encode_str(s, 10)

    def set_level(self, lv: int):
        self.raw[0x54] = lv & 0xFF

    def set_experience(self, exp: int):
        # preserve the high 12 bits of the u32 (the separate packed field)
        w = struct.unpack_from("<I", self.G, 0x04)[0]
        w = (w & ~0xFFFFF) | (exp & 0xFFFFF)
        struct.pack_into("<I", self.G, 0x04, w & 0xFFFFFFFF)

    def set_friendship(self, f: int):
        self.G[0x09] = f & 0xFF

    def set_held_item(self, item: int):
        struct.pack_into("<H", self.G, 0x02, item & 0xFFFF)

    def set_moves(self, moves):
        for i in range(4):
            struct.pack_into("<H", self.A, i * 2, (moves[i] if i < len(moves) else 0) & 0xFFFF)

    def set_ivs(self, ivs: dict):
        w = struct.unpack_from("<I", self.M, 0x04)[0]
        # clear only the 30 IV bits, keep bits 30/31 flags
        w &= ~((1 << 30) - 1)
        for i, k in enumerate(STAT_KEYS):
            w |= (ivs[k] & 0x1F) << (5 * i)
        struct.pack_into("<I", self.M, 0x04, w & 0xFFFFFFFF)

    def set_evs(self, evs: dict):
        for i, k in enumerate(STAT_KEYS):
            self.E[i] = evs[k] & 0xFF

    def set_ability_slot(self, idx: int):
        # Misc byte 0x0B bits 5-6 (0x20=1, 0x40=2)
        b = self.M[0x0B] & ~0x60
        b |= (idx & 0x3) << 5
        self.M[0x0B] = b & 0xFF

    def force_shiny(self, shiny: bool) -> bool:
        """Make the mon shiny/non-shiny reliably.

        enable  -> set the flag bit (verified to work in-game; least invasive).
        disable -> clear the flag AND, if the mon is shiny by its PID/OTID xor
                   (< 16), nudge the secret ID (SID) until it is no longer
                   PID-shiny. The visible trainer ID (TID, low 16 bits) is NOT
                   changed; only the hidden SID is adjusted.

        Returns True if a SID change was needed (only possible on disable of a
        PID-shiny)."""
        self.set_shiny(shiny)
        if shiny:
            return False
        # disabling: check the PID/OTID xor rule
        tid = self.otid & 0xFFFF
        sid = (self.otid >> 16) & 0xFFFF
        pidlo = self.pid & 0xFFFF
        pidhi = (self.pid >> 16) & 0xFFFF
        if (tid ^ sid ^ pidlo ^ pidhi) >= 16:
            return False  # flag clear is enough
        # find the smallest SID tweak (flip low bits) that pushes xor >= 16
        for bit in range(16):
            cand_sid = sid ^ (1 << bit)
            if (tid ^ cand_sid ^ pidlo ^ pidhi) >= 16:
                self.otid = (self.otid & 0x0000FFFF) | (cand_sid << 16)
                struct.pack_into("<I", self.raw, 0x04, self.otid & 0xFFFFFFFF)
                return True
        # fallback: bump SID directly (shouldn't happen)
        cand_sid = (sid + 1) & 0xFFFF
        self.otid = (self.otid & 0x0000FFFF) | (cand_sid << 16)
        struct.pack_into("<I", self.raw, 0x04, self.otid & 0xFFFFFFFF)
        return True

    def set_shiny(self, shiny: bool):
        if shiny:
            self.raw[0x1F] |= 0x40
        else:
            self.raw[0x1F] &= ~0x40

    # ---- commit ----------------------------------------------------------
    def to_raw(self) -> bytes:
        self._encrypt_into_raw()
        return bytes(self.raw)


# --------------------------------------------------------------------------
# Save writer: place an edited mon into SaveBlock1 and fix checksums.
# --------------------------------------------------------------------------
def write_party_mon(save: Save, index: int, mon_raw: bytes) -> list:
    """Write a 100-byte mon into party slot `index` (0-based) within SaveBlock1.

    Recomputes checksums only for the sectors that changed. Returns the list
    of section IDs touched. Caller must then persist `save` to disk.
    """
    sb1_off = PARTY_OFF + index * PARTY_MON_SIZE
    touched = set()

    for j, byte in enumerate(mon_raw):
        sb1_rel = sb1_off + j
        seg = sb1_rel // DATA_SIZE          # which SaveBlock1 section (0..3)
        within = sb1_rel % DATA_SIZE
        sid = SB1_SECTION_IDS[seg]
        abs_off = save.sections[sid] + within
        if save.data[abs_off] != byte:
            save.data[abs_off] = byte
            touched.add(sid)

    for sid in touched:
        _fix_section_checksum(save, sid)
    return sorted(touched)


def _fix_section_checksum(save: Save, sid: int):
    off = save.sections[sid]
    chk = save._checksum(save.data[off:off + DATA_SIZE])
    struct.pack_into("<H", save.data, off + FOOTER + 2, chk)


def save_to_file(save: Save, path: str):
    """Persist 128KB core + preserved tail to `path`."""
    out = bytes(save.data) + bytes(save.tail)
    with open(path, "wb") as f:
        f.write(out)


# --------------------------------------------------------------------------
# PK3 export (100-byte party-format Pokemon file for PKHeX)
# --------------------------------------------------------------------------

def _make_pid_shiny(pid: int, otid: int) -> int:
    """Return an OTID whose PID/OTID xor is shiny (< 8) without changing the
    visible Trainer ID (low 16 bits) or the PID. Only the hidden Secret ID
    (high 16 bits) is adjusted. This makes the mon shiny by the *standard*
    Gen3 rule, which both PKHeX and the game recognise."""
    tid = otid & 0xFFFF
    pidlo = pid & 0xFFFF
    pidhi = (pid >> 16) & 0xFFFF
    # We need (tid ^ sid ^ pidlo ^ pidhi) < 8. Choose a target value, then
    # solve for sid. Try a few targets for a clean result.
    for target in range(0, 8):
        sid = target ^ tid ^ pidlo ^ pidhi
        new = (sid << 16) | tid
        if ((pid & 0xFFFF) ^ ((pid >> 16) & 0xFFFF) ^ (new & 0xFFFF) ^ ((new >> 16) & 0xFFFF)) < 8:
            return new
    return otid  # fallback (shouldn't happen)


def to_pk3(mon_raw: bytes, level: int = 0, want_shiny: bool = False) -> bytes:
    """Convert a mon (party 100-byte or box 80-byte) into a 100-byte PK3.

    PKHeX's Gen3 .pk3 is the 100-byte PARTY structure:
      0x00 PID, 0x04 OTID, 0x08 nickname(10), 0x12 lang, 0x13 flags,
      0x14 OT name, 0x18 markings, 0x1C checksum(u16), 0x1E pad,
      0x20 encrypted/shuffled 48-byte substructs, 0x50 party stats/tail.
    The checksum at 0x1C is the sum of the 24 DECRYPTED u16 substruct words.

    If ``want_shiny`` is True the mon is made shiny by the standard Gen3
    PID/OTID rule (by adjusting only the hidden Secret ID), so it shows as
    shiny in BOTH the game and PKHeX. If False, the Seaglass shiny flag bit
    (raw header 0x1F & 0x40) is cleared in the export and the standard rule is
    not forced.
    """
    raw = bytearray(mon_raw[:100])
    if len(raw) < 100:
        raw += bytes(100 - len(raw))   # synthesize empty party tail for box mons
        if 0 < level <= 100:
            raw[0x54] = level & 0xFF

    # Language byte: keep valid Gen3 values (1-7), otherwise default to English.
    if raw[0x12] not in (1, 2, 3, 4, 5, 6, 7):
        raw[0x12] = 2

    pid = struct.unpack_from("<I", raw, 0x00)[0]
    otid = struct.unpack_from("<I", raw, 0x04)[0]

    # Reconcile shiny so the export is understood by PKHeX (standard rule).
    pid_shiny = ((pid & 0xFFFF) ^ ((pid >> 16) & 0xFFFF)
                 ^ (otid & 0xFFFF) ^ ((otid >> 16) & 0xFFFF)) < 8
    if want_shiny and not pid_shiny:
        otid = _make_pid_shiny(pid, otid)
        struct.pack_into("<I", raw, 0x04, otid)
    if want_shiny:
        raw[0x1F] |= 0x40      # keep the Seaglass flag too (game side)
    else:
        raw[0x1F] &= ~0x40     # not shiny: ensure Seaglass flag is clear

    key = (pid ^ otid) & 0xFFFFFFFF
    enc = bytearray(raw[0x20:0x20 + 48])
    for i in range(0, 48, 4):
        v = struct.unpack_from("<I", enc, i)[0] ^ key
        struct.pack_into("<I", enc, i, v & 0xFFFFFFFF)
    chk = sum(struct.unpack_from("<24H", bytes(enc), 0)) & 0xFFFF
    struct.pack_into("<H", raw, 0x1C, chk)
    return bytes(raw)


def export_pk3(mon_raw: bytes, path: str, level: int = 0, want_shiny: bool = False) -> str:
    data = to_pk3(mon_raw, level, want_shiny)
    with open(path, "wb") as f:
        f.write(data)
    return path
