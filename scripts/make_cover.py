#!/usr/bin/env python3
"""
Generates docs/cover.jpg — the artwork Apple Podcasts and Spotify show.

3000x3000. Deliberately plain and institutional: this show is competing on
credibility, and a listener scanning a podcast app should read it as a trade
publication rather than a hobby project.

    python scripts/make_cover.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "docs", "cover.jpg")

SIZE = 3000
MARGIN = 240
NAVY = (14, 30, 56)
NAVY_LIGHT = (26, 48, 82)
WHITE = (247, 249, 252)
AMBER = (232, 168, 56)
SLATE = (150, 166, 190)

DISPLAY_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
BODY_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def load_font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def ink(draw, text, font):
    return draw.textbbox((0, 0), text, font=font)


def draw_at(draw, left, top, text, font, fill):
    box = ink(draw, text, font)
    draw.text((left - box[0], top - box[1]), text, font=font, fill=fill)
    return box[2] - box[0], box[3] - box[1]


def tracked_width(draw, text, font, tracking):
    return sum(draw.textlength(c, font=font) for c in text) + tracking * max(len(text) - 1, 0)


def draw_tracked(draw, left, top, text, font, fill, tracking):
    box = ink(draw, text, font)
    x, y = left, top - box[1]
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        x += draw.textlength(char, font=font) + tracking
    return box[3] - box[1]


def fit_font(draw, text, candidates, max_width, tracking=0, start=200):
    size = start
    while size > 24:
        font = load_font(candidates, size)
        if tracked_width(draw, text, font, tracking) <= max_width:
            return font
        size -= 4
    return load_font(candidates, 24)


def build():
    img = Image.new("RGB", (SIZE, SIZE), NAVY)
    draw = ImageDraw.Draw(img)

    # A quiet bar-chart motif in the lower right — rising columns, barely there.
    heights = [260, 420, 340, 620, 780]
    bar_w, gap = 150, 46
    total = len(heights) * bar_w + (len(heights) - 1) * gap
    x = SIZE - MARGIN - total
    base = SIZE - 470
    for i, h in enumerate(heights):
        colour = AMBER if i == len(heights) - 1 else NAVY_LIGHT
        draw.rectangle([x, base - h, x + bar_w, base], fill=colour)
        x += bar_w + gap

    # Amber rule, then the wordmark.
    draw.rectangle([MARGIN, 560, MARGIN + 340, 560 + 26], fill=AMBER)

    title_font = fit_font(draw, "INSURANCE", DISPLAY_FONTS, SIZE - 2 * MARGIN, start=560)
    cap = max(ink(draw, t, title_font)[3] - ink(draw, t, title_font)[1] for t in ("INSURANCE", "DAILY"))
    y = 700
    draw_at(draw, MARGIN, y, "INSURANCE", title_font, WHITE)
    draw_at(draw, MARGIN, y + cap + 70, "DAILY", title_font, AMBER)

    sub_y = y + 2 * cap + 220
    sub = "THE US INSURANCE NEWS BRIEFING"
    sub_font = fit_font(draw, sub, BODY_FONTS, SIZE - 2 * MARGIN, tracking=16, start=112)
    draw_tracked(draw, MARGIN, sub_y, sub, sub_font, SLATE, 16)

    foot = "For agents and brokers  ·  Every weekday morning"
    foot_font = fit_font(draw, foot, BODY_FONTS, SIZE - 2 * MARGIN, start=94)
    draw_at(draw, MARGIN, SIZE - MARGIN - 60, foot, foot_font, SLATE)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    img.save(OUT_PATH, "JPEG", quality=92, optimize=True, progressive=True)
    print(f"Wrote {OUT_PATH} ({SIZE}x{SIZE}, {os.path.getsize(OUT_PATH) / 1024:.0f} KB)")


if __name__ == "__main__":
    build()
