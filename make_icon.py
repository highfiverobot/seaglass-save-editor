"""make_icon.py -- build a multi-resolution app.ico from esg.png.

Run automatically by build_exe.bat (and the release workflow) so you only ever
need to edit the PNGs. Writes app.ico in the project root.

Uses PySide6 to render/resize, then assembles a standard multi-image ICO by
hand (PNG-compressed entries, which Windows Vista+ supports at all sizes).
Sizes: 16, 24, 32, 48, 256 -- all scaled from the single esg.png source.
"""
import os
import struct
import sys

from PySide6.QtCore import Qt, QBuffer, QByteArray
from PySide6.QtGui import QImage, QGuiApplication

HERE = os.path.dirname(os.path.abspath(__file__))

# single source image
SRC = os.path.join(HERE, "esg.png")
OUT = os.path.join(HERE, "app.ico")

SIZES = [16, 24, 32, 48, 256]


def _png_bytes(img: QImage) -> bytes:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return bytes(ba)


def _scaled(src: QImage, size: int) -> QImage:
    return src.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def build():
    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841

    src = QImage(SRC) if os.path.exists(SRC) else None
    if src is None or src.isNull():
        print("make_icon: esg.png not found; skipping")
        return 1

    entries = []  # (size, png_bytes)
    for size in SIZES:
        entries.append((size, _png_bytes(_scaled(src, size))))

    # Assemble ICO: header + directory + PNG payloads.
    count = len(entries)
    out = bytearray()
    out += struct.pack("<HHH", 0, 1, count)  # reserved, type=1(icon), count
    offset = 6 + 16 * count
    directory = bytearray()
    payload = bytearray()
    for size, data in entries:
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        directory += struct.pack("<BBBBHHII",
                                 w, h, 0, 0, 1, 32, len(data), offset)
        payload += data
        offset += len(data)
    out += directory + payload
    with open(OUT, "wb") as f:
        f.write(out)
    print(f"make_icon: wrote {OUT} ({count} sizes, {len(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(build())