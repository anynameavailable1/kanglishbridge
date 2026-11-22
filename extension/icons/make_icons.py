"""Generates simple PNG icons without any dependency. Replace with your own artwork any time."""
import struct, zlib
def png(size, path):
    cx = cy = (size - 1) / 2; r = size * 0.46
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d <= r:                                   # saffron disc
                bridge = abs(y - size * 0.62) < size * 0.07 and size * 0.2 < x < size * 0.8
                pillar = (abs(x - size * 0.3) < size * 0.05 or abs(x - size * 0.7) < size * 0.05) and size * 0.38 < y < size * 0.7
                row += bytes((29, 27, 22, 255)) if (bridge or pillar) else bytes((227, 154, 11, 255))
            else:
                row += bytes((0, 0, 0, 0))
        rows.append(bytes(row))
    raw = b"".join(rows)
    def chunk(t, d): c = struct.pack(">I", len(d)) + t + d; return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
for s in (16, 48, 128): png(s, f"icon{s}.png")
