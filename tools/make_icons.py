"""PWA 用アイコン（PNG）を生成するスクリプト。外部ライブラリ不要。

青地に白で「AI」、右下に合格を表すチェックマークを描く。
使い方:
    python tools/make_icons.py
出力: pwa/icons/icon-180.png, icon-192.png, icon-512.png
"""

import struct
import zlib
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "pwa" / "icons"
BACKGROUND = (37, 99, 235)
FOREGROUND = (255, 255, 255)
ACCENT = (250, 204, 21)
SUPERSAMPLE = 3

# 図形は 0〜1 の座標系で定義する（線分の始点・終点と太さ）
LETTER_STROKES = [
    ((0.20, 0.70), (0.34, 0.26), 0.075),  # A の左斜線
    ((0.34, 0.26), (0.48, 0.70), 0.075),  # A の右斜線
    ((0.255, 0.54), (0.425, 0.54), 0.06),  # A の横棒
    ((0.62, 0.26), (0.62, 0.70), 0.08),  # I
]
CHECK_STROKES = [
    ((0.66, 0.80), (0.72, 0.86), 0.05),
    ((0.72, 0.86), (0.84, 0.72), 0.05),
]


def distance_to_segment(point, start, end):
    """点と線分の距離を返す。"""
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    ratio = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    cx, cy = ax + ratio * dx, ay + ratio * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def color_at(x, y):
    """座標 (x, y) の色を返す。"""
    if any(distance_to_segment((x, y), a, b) <= width / 2 for a, b, width in CHECK_STROKES):
        return ACCENT
    if any(distance_to_segment((x, y), a, b) <= width / 2 for a, b, width in LETTER_STROKES):
        return FOREGROUND
    return BACKGROUND


def render(size):
    """size×size の画像を、間引きで滑らかにした RGB の行データとして返す。"""
    rows = []
    samples = SUPERSAMPLE * SUPERSAMPLE
    for pixel_y in range(size):
        row = bytearray([0])  # PNG のフィルタ種別（なし）
        for pixel_x in range(size):
            total = [0, 0, 0]
            for sub_y in range(SUPERSAMPLE):
                for sub_x in range(SUPERSAMPLE):
                    x = (pixel_x + (sub_x + 0.5) / SUPERSAMPLE) / size
                    y = (pixel_y + (sub_y + 0.5) / SUPERSAMPLE) / size
                    for channel, value in enumerate(color_at(x, y)):
                        total[channel] += value
            row.extend(round(value / samples) for value in total)
        rows.append(bytes(row))
    return b"".join(rows)


def write_png(path, size):
    """PNG ファイルを書き出す。"""

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
    png += chunk(b"IDAT", zlib.compress(render(size), 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for size in (180, 192, 512):
        write_png(OUTPUT_DIR / f"icon-{size}.png", size)
        print(f"icon-{size}.png")


if __name__ == "__main__":
    main()
