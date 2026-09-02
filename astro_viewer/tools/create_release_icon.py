"""Render the deterministic multi-resolution Windows release icon without GUI tooling."""

from __future__ import annotations

import math
import struct
from pathlib import Path


RGBA = tuple[int, int, int, int]
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
SUPERSAMPLE = 4


def create_icon(path: Path) -> None:
    images = [_ico_image(size, _render_icon(size)) for size in ICON_SIZES]
    icon_header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + len(images) * 16
    directories = []
    for size, image in zip(ICON_SIZES, images):
        size_byte = 0 if size == 256 else size
        directories.append(
            struct.pack(
                "<BBBBHHII",
                size_byte,
                size_byte,
                0,
                0,
                1,
                32,
                len(image),
                offset,
            )
        )
        offset += len(image)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(icon_header + b"".join(directories) + b"".join(images))


def _render_icon(size: int) -> list[RGBA]:
    scale = SUPERSAMPLE
    samples = scale * scale
    pixels: list[RGBA] = []
    for y in range(size):
        for x in range(size):
            total = [0, 0, 0, 0]
            for sy in range(scale):
                for sx in range(scale):
                    px = (x + (sx + 0.5) / scale) / size
                    py = (y + (sy + 0.5) / scale) / size
                    color = _sample_scene(px, py)
                    for index in range(4):
                        total[index] += color[index]
            pixels.append(tuple(round(channel / samples) for channel in total))
    return pixels


def _sample_scene(x: float, y: float) -> RGBA:
    color: RGBA = (0, 0, 0, 0)
    badge_distance = _distance(x, y, 0.5, 0.5)
    if badge_distance <= 0.47:
        t = min(1.0, badge_distance / 0.47)
        color = _lerp((35, 48, 70, 255), (12, 18, 29, 255), t)
    if 0.435 < badge_distance <= 0.47:
        color = _over(color, (102, 214, 232, 190))

    for star_x, star_y, radius, alpha in (
        (0.25, 0.24, 0.020, 230),
        (0.38, 0.17, 0.010, 190),
        (0.78, 0.29, 0.016, 210),
        (0.18, 0.46, 0.011, 180),
    ):
        if _distance(x, y, star_x, star_y) <= radius:
            color = _over(color, (246, 249, 255, alpha))

    if _distance(x, y, 0.68, 0.26) <= 0.105:
        color = _over(color, (245, 248, 252, 238))
    if _distance(x, y, 0.72, 0.235) <= 0.105:
        cutout = _lerp((29, 41, 61, 255), (14, 21, 33, 255), min(1.0, badge_distance / 0.47))
        color = _over(color, cutout)

    if _segment_distance(x, y, 0.50, 0.58, 0.50, 0.78) <= 0.018:
        color = _over(color, (150, 161, 177, 255))
    if _segment_distance(x, y, 0.50, 0.68, 0.34, 0.84) <= 0.016:
        color = _over(color, (128, 141, 158, 255))
    if _segment_distance(x, y, 0.50, 0.68, 0.66, 0.84) <= 0.016:
        color = _over(color, (128, 141, 158, 255))

    if _segment_distance(x, y, 0.29, 0.63, 0.72, 0.45) <= 0.074:
        color = _over(color, (45, 55, 72, 180))
    if _segment_distance(x, y, 0.30, 0.60, 0.71, 0.43) <= 0.057:
        color = _over(color, (226, 232, 240, 255))
    if _segment_distance(x, y, 0.37, 0.57, 0.64, 0.46) <= 0.033:
        color = _over(color, (175, 185, 199, 255))
    if _segment_distance(x, y, 0.22, 0.63, 0.32, 0.59) <= 0.038:
        color = _over(color, (189, 199, 213, 255))
    if _segment_distance(x, y, 0.68, 0.42, 0.79, 0.38) <= 0.066:
        color = _over(color, (105, 214, 232, 255))
    if _segment_distance(x, y, 0.70, 0.42, 0.78, 0.39) <= 0.035:
        color = _over(color, (34, 52, 72, 170))
    if _distance(x, y, 0.50, 0.61) <= 0.041:
        color = _over(color, (244, 247, 251, 255))

    return color


def _ico_image(size: int, pixels: list[RGBA]) -> bytes:
    xor = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            red, green, blue, alpha = pixels[y * size + x]
            xor.extend((blue, green, red, alpha))

    row_bytes = ((size + 31) // 32) * 4
    mask = bytearray(row_bytes * size)
    for y in range(size):
        for x in range(size):
            alpha = pixels[(size - 1 - y) * size + x][3]
            if alpha < 128:
                mask[y * row_bytes + x // 8] |= 0x80 >> (x % 8)

    bitmap_header = struct.pack(
        "<IIIHHIIIIII",
        40,
        size,
        size * 2,
        1,
        32,
        0,
        len(xor) + len(mask),
        0,
        0,
        0,
        0,
    )
    return bitmap_header + bytes(xor) + bytes(mask)


def _distance(x: float, y: float, cx: float, cy: float) -> float:
    return math.hypot(x - cx, y - cy)


def _segment_distance(x: float, y: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx = bx - ax
    aby = by - ay
    length_sq = abx * abx + aby * aby
    if length_sq == 0:
        return _distance(x, y, ax, ay)
    t = max(0.0, min(1.0, ((x - ax) * abx + (y - ay) * aby) / length_sq))
    return _distance(x, y, ax + abx * t, ay + aby * t)


def _lerp(a: RGBA, b: RGBA, t: float) -> RGBA:
    return tuple(round(a[index] + (b[index] - a[index]) * t) for index in range(4))


def _over(base: RGBA, top: RGBA) -> RGBA:
    top_alpha = top[3] / 255
    base_alpha = base[3] / 255
    out_alpha = top_alpha + base_alpha * (1 - top_alpha)
    if out_alpha <= 0:
        return (0, 0, 0, 0)
    channels = []
    for index in range(3):
        value = (top[index] * top_alpha + base[index] * base_alpha * (1 - top_alpha)) / out_alpha
        channels.append(round(value))
    channels.append(round(out_alpha * 255))
    return tuple(channels)


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    create_icon(base_dir / "resources" / "icons" / "nightscope.ico")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
