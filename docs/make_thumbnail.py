"""Generate the 560x280 Kaggle submission thumbnail."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 560, 280
BG_TOP = (13, 27, 42)      # deep navy
BG_BOT = (27, 56, 88)      # lighter navy
ACCENT = (56, 199, 162)    # teal
WHITE = (240, 245, 250)
MUTED = (150, 170, 190)

img = Image.new("RGB", (W, H), BG_TOP)
draw = ImageDraw.Draw(img)

# vertical gradient
for y in range(H):
    t = y / H
    r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
    g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
    b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))


def font(size, bold=True):
    names = (
        ["arialbd.ttf", "Arialbd.ttf"] if bold else ["arial.ttf", "Arial.ttf"]
    ) + ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


# accent bar
draw.rectangle([0, 0, 8, H], fill=ACCENT)

# eyebrow
draw.text((34, 30), "HEALTHCARE DATA PIPELINE", font=font(15), fill=ACCENT)

# title (two lines)
draw.text((34, 58), "Provider Directory", font=font(40), fill=WHITE)
draw.text((34, 104), "Accuracy at Scale", font=font(40), fill=WHITE)

# subtitle
draw.text(
    (34, 158),
    "AI pipeline: detect → verify → score → route → audit",
    font=font(17, bold=False),
    fill=MUTED,
)

# stat chips
chips = [("~$0.04", "/ 1k records"), ("<15%", "human review"), ("4", "free sources")]
x = 34
y = 205
for big, small in chips:
    bw = 156
    draw.rounded_rectangle([x, y, x + bw, y + 50], radius=10, fill=(255, 255, 255, 0), outline=ACCENT, width=2)
    draw.text((x + 14, y + 8), big, font=font(22), fill=ACCENT)
    draw.text((x + 14, y + 32), small, font=font(12, bold=False), fill=MUTED)
    x += bw + 12

out = Path(__file__).parent / "thumbnail.png"
img.save(out)
print("wrote", out, img.size)
