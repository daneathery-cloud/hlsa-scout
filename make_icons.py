"""Draws the phone app icons into assets/icons (run once; the icons are committed).
Navy square, white "HLSA", red "SCOUT" bar - the HLSA colors."""
import os

from PIL import Image, ImageDraw, ImageFont

import config

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")
FONT = r"C:\Windows\Fonts\segoeuib.ttf"


def _fit(draw, text, max_w, start):
    size = start
    while size > 10:
        f = ImageFont.truetype(FONT, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(FONT, size)


def draw(size: int, safe: float) -> Image.Image:
    big = 1024
    img = Image.new("RGB", (big, big), config.NAVY)
    d = ImageDraw.Draw(img)
    w = big * safe
    lo = (big - w) / 2
    f1 = _fit(d, "HLSA", w, 420)
    d.text((big / 2, lo + w * 0.40), "HLSA", font=f1, fill="#FFFFFF", anchor="mm")
    bar_top, bar_h = lo + w * 0.68, w * 0.24
    d.rounded_rectangle((lo, bar_top, lo + w, bar_top + bar_h), radius=bar_h * 0.25, fill=config.RED)
    f2 = _fit(d, "SCOUT", w * 0.8, 200)
    d.text((big / 2, bar_top + bar_h / 2), "SCOUT", font=f2, fill="#FFFFFF", anchor="mm")
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    draw(512, 0.78).save(os.path.join(OUT, "icon-512.png"))
    draw(192, 0.78).save(os.path.join(OUT, "icon-192.png"))
    draw(512, 0.58).save(os.path.join(OUT, "maskable-512.png"))
    draw(180, 0.74).save(os.path.join(OUT, "apple-touch-icon.png"))
    draw(32, 0.92).save(os.path.join(OUT, "favicon-32.png"))
    print("icons written to", OUT)
