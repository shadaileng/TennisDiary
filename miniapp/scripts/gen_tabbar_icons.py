#!/usr/bin/env python3
"""Generate simple monochrome tabbar icons for the mini-program.

Produces 8 PNGs (4 tabs x normal/active) at 81x81 with a transparent
background, matching the olive/lime theme of Tennis Diary.

Tabs:
  diary - open notebook + pen
  gear  - tennis racket
  stats - bar chart
  mine  - person
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 81
OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "static" / "tabbar"

# Theme colors (unselected olive-light, selected lime-dark)
COLOR_NORMAL = "#6B7562"
COLOR_ACTIVE = "#A8B822"


def _new_img(color: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _draw_diary(color: str) -> Image.Image:
    img, d = _new_img(color)
    # notebook cover
    d.rounded_rectangle([18, 16, 63, 66], radius=6, outline=color, width=4)
    # binding
    d.line([18, 41, 63, 41], fill=color, width=4)
    # pen
    d.line([48, 30, 66, 12], fill=color, width=4)
    return img


def _draw_gear(color: str) -> Image.Image:
    img, d = _new_img(color)
    # racket head (ellipse) + handle
    d.ellipse([20, 14, 61, 55], outline=color, width=4)
    d.line([43, 52, 40, 66], fill=color, width=5)
    d.ellipse([30, 22, 51, 43], outline=color, width=3)
    return img


def _draw_stats(color: str) -> Image.Image:
    img, d = _new_img(color)
    # three bars
    d.rectangle([18, 40, 30, 64], outline=color, width=4)
    d.rectangle([35, 28, 47, 64], outline=color, width=4)
    d.rectangle([52, 16, 64, 64], outline=color, width=4)
    return img


def _draw_mine(color: str) -> Image.Image:
    img, d = _new_img(color)
    # head + shoulders
    d.ellipse([30, 16, 51, 37], outline=color, width=4)
    d.arc([22, 42, 59, 70], start=180, end=360, fill=color, width=4)
    return img


DRAWERS = {
    "diary": _draw_diary,
    "gear": _draw_gear,
    "stats": _draw_stats,
    "mine": _draw_mine,
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, fn in DRAWERS.items():
        fn(COLOR_NORMAL).save(OUT_DIR / f"{name}.png")
        fn(COLOR_ACTIVE).save(OUT_DIR / f"{name}-active.png")
        print(f"generated {name}.png / {name}-active.png")


if __name__ == "__main__":
    main()
