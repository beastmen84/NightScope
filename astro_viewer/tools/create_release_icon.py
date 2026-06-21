from __future__ import annotations

import struct
from pathlib import Path


def create_icon(path: Path) -> None:
    size = 32
    pixels: list[tuple[int, int, int, int]] = []
    center = (15.5, 15.5)
    for y in range(size):
        for x in range(size):
            dx = x - center[0]
            dy = y - center[1]
            distance = (dx * dx + dy * dy) ** 0.5
            if distance > 15:
                pixels.append((0, 0, 0, 0))
            elif 10 < distance < 12 and x > 10:
                pixels.append((101, 214, 232, 255))
            elif abs(y - 20) <= 1 and 7 <= x <= 25:
                pixels.append((244, 247, 251, 255))
            elif abs(x - 16) <= 1 and 12 <= y <= 24:
                pixels.append((174, 183, 196, 255))
            else:
                shade = max(20, 42 - int(distance))
                pixels.append((shade, shade + 5, shade + 13, 255))

    xor = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            r, g, b, a = pixels[y * size + x]
            xor.extend([b, g, r, a])
    and_mask = bytes(size * size // 8)
    bitmap_header = struct.pack(
        "<IIIHHIIIIII",
        40,
        size,
        size * 2,
        1,
        32,
        0,
        len(xor) + len(and_mask),
        0,
        0,
        0,
        0,
    )
    image = bitmap_header + bytes(xor) + and_mask
    icon_header = struct.pack("<HHH", 0, 1, 1)
    directory = struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(image), 22)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(icon_header + directory + image)


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    create_icon(base_dir / "resources" / "icons" / "nightscope.ico")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
