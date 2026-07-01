#!/usr/bin/env python3
"""Generate Day Shift MOBILE promo image (1080×1920) — portrait/vertical for
   Stories, TikTok, and mobile-first social feeds. All content reflowed for
   vertical scroll with generous spacing."""

import os
import qrcode
from PIL import Image as PILImage, ImageDraw, ImageFont

# ── Config ──────────────────────────────────────────────────────────────
W, H = 1080, 1920          # 9:16 portrait — mobile-optimized
BG = "#0c0a09"
ORANGE = "#f97316"
WHITE = "#fafaf9"
GRAY = "#a8a29e"
DARK = "#1c1917"
DIM = "#78716c"

TARGET_URL = "https://day-shift.workshop.build"
LOGO_PATH = "./public/dayshift-logo.png"
OUTPUT = "promo-assets/DayShift_Mobile_Market.png"

# ── Fonts ───────────────────────────────────────────────────────────────
FONT_DIR = "/usr/share/fonts/truetype/liberation"

def load_font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

font_brand      = load_font("LiberationSans-Bold.ttf", 52)
font_header     = load_font("LiberationSans-Bold.ttf", 32)
font_stat_big   = load_font("LiberationSans-Bold.ttf", 72)
font_stat_label = load_font("LiberationSans-Regular.ttf", 22)
font_body       = load_font("LiberationSans-Regular.ttf", 24)
font_small      = load_font("LiberationSans-Regular.ttf", 20)
font_tiny       = load_font("LiberationSans-Regular.ttf", 18)
font_position   = load_font("LiberationSans-Italic.ttf", 23)
font_feature_title = load_font("LiberationSans-Bold.ttf", 23)
font_feature_desc = load_font("LiberationSans-Regular.ttf", 21)
font_cta        = load_font("LiberationSans-Bold.ttf", 30)
font_divider    = load_font("LiberationSans-Regular.ttf", 19)

# ── Helpers ─────────────────────────────────────────────────────────────
def center_text(draw, y, text, font, fill, **kw):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), text, fill=fill, font=font, **kw)

def left_text(draw, x, y, text, font, fill, **kw):
    draw.text((x, y), text, fill=fill, font=font, **kw)

def draw_rounded_rect(draw, coords, radius, fill):
    x1, y1, x2, y2 = coords
    r = radius
    draw.rectangle([x1 + r, y1, x2 - r, y2], fill=fill)
    draw.rectangle([x1, y1 + r, x2, y2 - r], fill=fill)
    draw.pieslice([x1, y1, x1 + 2*r, y1 + 2*r], 180, 270, fill=fill)
    draw.pieslice([x2 - 2*r, y1, x2, y1 + 2*r], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2*r, x1 + 2*r, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2*r, y2 - 2*r, x2, y2], 0, 90, fill=fill)

def draw_rounded_border(draw, coords, radius, outline, width=3):
    x1, y1, x2, y2 = coords
    r = radius
    draw.arc([x1, y1, x1 + 2*r, y1 + 2*r], 180, 270, fill=outline, width=width)
    draw.arc([x2 - 2*r, y1, x2, y1 + 2*r], 270, 360, fill=outline, width=width)
    draw.arc([x1, y2 - 2*r, x1 + 2*r, y2], 90, 180, fill=outline, width=width)
    draw.arc([x2 - 2*r, y2 - 2*r, x2, y2], 0, 90, fill=outline, width=width)
    draw.line([x1 + r, y1, x2 - r, y1], fill=outline, width=width)
    draw.line([x1 + r, y2, x2 - r, y2], fill=outline, width=width)
    draw.line([x1, y1 + r, x1, y2 - r], fill=outline, width=width)
    draw.line([x2, y1 + r, x2, y2 - r], fill=outline, width=width)

# ── Build QR code with embedded logo ───────────────────────────────────
qr = qrcode.QRCode(
    version=3,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=20,
    border=2,
)
qr.add_data(TARGET_URL)
qr.make(fit=True)
qr_img = qr.make_image(fill_color=ORANGE, back_color="transparent").convert("RGBA")

logo = PILImage.open(LOGO_PATH).convert("RGBA")
qr_w, qr_h = qr_img.size
logo_size = int(qr_w * 0.25)
logo_resized = logo.resize((logo_size, logo_size), PILImage.LANCZOS)

mask = PILImage.new("L", (logo_size, logo_size), 0)
md = ImageDraw.Draw(mask)
md.ellipse([0, 0, logo_size - 1, logo_size - 1], fill=255)

pad = int(logo_size * 0.15)
padded_size = logo_size + 2 * pad
white_bg = PILImage.new("RGBA", (padded_size, padded_size), (255, 255, 255, 255))
px = (padded_size - logo_size) // 2
white_bg.paste(logo_resized, (px, px), mask)

padded_mask = PILImage.new("L", (padded_size, padded_size), 0)
pmd = ImageDraw.Draw(padded_mask)
pmd.ellipse([0, 0, padded_size - 1, padded_size - 1], fill=255)

pos = ((qr_w - padded_size) // 2, (qr_h - padded_size) // 2)
qr_img.paste(white_bg, pos, padded_mask)

# ── Canvas ─────────────────────────────────────────────────────────────
canvas = PILImage.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(canvas)

# Subtle gradient warmth
for i in range(H):
    shade = int(12 + (i / H) * 10)
    draw.line([(0, i), (W, i)], fill=(shade, int(shade * 0.85), int(shade * 0.75)))

draw = ImageDraw.Draw(canvas)

# ══════════════════════════════════════════════════════════════════════
# VERTICAL LAYOUT — each section clearly separated
# ══════════════════════════════════════════════════════════════════════

M = 56              # horizontal margin
GAP_V = 40          # vertical gap between sections
INNER = 32          # padding inside cards

y = M

# ── 1) TOP ORANGE ACCENT BAR ─────────────────────────────────────────
draw.rectangle([0, 0, W, 6], fill=ORANGE)
y += 28

# ── 2) HEADER ─────────────────────────────────────────────────────────
center_text(draw, y, "THE KITCHEN FLOOR IS SHIFTING", font_header, WHITE)
y += 50

# Accent line
draw.line([(M + 100, y), (W - M - 100, y)], fill=ORANGE, width=2)
y += GAP_V + 10

# ── 3) QR CODE — centered, large for mobile scanning ──────────────────
qr_display = 420
qr_resized_d = qr_img.resize((qr_display, qr_display), PILImage.LANCZOS)

# Ember glow behind QR
gcx, gcy = W // 2, y + qr_display // 2
for alpha_val in [30, 20, 12, 6, 3]:
    gs = qr_display + (30 - alpha_val) * 8
    glow_ov = PILImage.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_ov)
    gd.ellipse([gcx - gs//2, gcy - gs//2, gcx + gs//2, gcy + gs//2],
               fill=(249, 115, 22, alpha_val))
    canvas = PILImage.alpha_composite(canvas.convert("RGBA"), glow_ov).convert("RGB")
    draw = ImageDraw.Draw(canvas)

canvas.paste(qr_resized_d, ((W - qr_display) // 2, y), qr_resized_d.convert("RGBA"))
y += qr_display + 20

center_text(draw, y, "SCAN TO JOIN THE CREW", font_body, ORANGE)
y += 28
center_text(draw, y, "New users get a free 7-day Boost automatically", font_small, GRAY)
y += GAP_V + 10

# ── 4) CINCINNATI POSITIONING STATEMENT CARD ─────────────────────────
card_h = 170
draw_rounded_rect(draw, [M, y, W - M, y + card_h], radius=18, fill=DARK)
draw_rounded_border(draw, [M, y, W - M, y + card_h], radius=18, outline=ORANGE, width=3)

pos_lines = [
    "The default infrastructure that connects",
    "Cincinnati's food service labor market",
    "— one verified video profile and one",
    "matched shift at a time.",
]
tx = M + INNER
ly = y + 30
ls = 29
for line in pos_lines:
    if "Cincinnati" in line:
        parts = line.split("Cincinnati")
        draw.text((tx, ly), parts[0], fill=WHITE, font=font_position)
        bw = draw.textbbox((0, 0), parts[0], font=font_position)[2]
        draw.text((tx + bw, ly), "Cincinnati", fill=ORANGE, font=font_position)
        cw = draw.textbbox((0, 0), "Cincinnati", font=font_position)[2]
        draw.text((tx + bw + cw, ly), parts[1], fill=WHITE, font=font_position)
    else:
        draw.text((tx, ly), line, fill=WHITE, font=font_position)
    ly += ls

y += card_h + GAP_V

# ── 5) THE PROBLEM — $14K BAR ────────────────────────────────────────
center_text(draw, y, "— THE PROBLEM —", font_divider, DIM)
y += 34

bar_h = 90
draw_rounded_rect(draw, [M, y, W - M, y + bar_h], radius=16, fill=DARK)
center_text(draw, y + 14, "$14K", font_stat_big, ORANGE)
center_text(draw, y + 68, "lost per vacant line cook, per year   •   avg 23-day wait to hire", font_tiny, DIM)
y += bar_h + GAP_V

# ── 6) THREE STAT CARDS — stacked vertically for mobile ──────────────
stat_card_h = 110
stat_gap = 20
stats_data = [
    ("73%", "of culinary hires come from word-of-mouth alone"),
    ("60%", "annual turnover rate across food service"),
    ("$3.2B", "lost annually to unfilled shifts nationwide"),
]

for val, desc in stats_data:
    draw_rounded_rect(draw, [M, y, W - M, y + stat_card_h], radius=14, fill=DARK)
    # Big number on left, text on right
    draw.text((M + INNER, y + 28), val, fill=ORANGE, font=font_stat_big)
    # Wrap description if needed — split into lines
    desc_bbox = draw.textbbox((0, 0), desc, font=font_stat_label)
    desc_w = desc_bbox[2] - desc_bbox[0]
    max_desc_w = W - 2*M - INNER - 140  # leave room for the big number
    if desc_w > max_desc_w:
        # Simple mid-split
        mid = len(desc) // 2
        space_idx = desc.rfind(" ", 0, mid + 20)
        if space_idx > 0:
            l1, l2 = desc[:space_idx], desc[space_idx+1:]
        else:
            l1, l2 = desc[:mid], desc[mid:]
        draw.text((M + 150, y + 36), l1, fill=GRAY, font=font_stat_label)
        draw.text((M + 150, y + 64), l2, fill=GRAY, font=font_stat_label)
    else:
        draw.text((M + 150, y + 44), desc, fill=GRAY, font=font_stat_label)
    y += stat_card_h + stat_gap

y += 8

# ── 7) WHY DAY SHIFT WINS ────────────────────────────────────────────
center_text(draw, y, "— WHY DAY SHIFT WINS —", font_divider, DIM)
y += 36

features = [
    ("Video Profiles",     "See skills & personality before the interview — not a paper resume."),
    ("Instant Matching",   "Swipe, match, connect. Fill tonight's gap today, not next week."),
    ("Built-In Chat",      "Confirm shifts, coordinate details, get paid — all in-app."),
    ("Reviews That Travel","Your reputation follows you. Top talent rises to the top."),
]

for title, desc in features:
    # Orange bullet bar
    bar_h = 44
    draw.rectangle([M, y + 5, M + 5, y + 5 + bar_h], fill=ORANGE)
    draw.text((M + 22, y), title, fill=ORANGE, font=font_feature_title)
    # Description on next line if long, or same line
    desc_bbox = draw.textbbox((0, 0), desc, font=font_feature_desc)
    desc_w = desc_bbox[2] - desc_bbox[0]
    max_w = W - M - 22 - 20
    if desc_w > max_w:
        # Split into two lines
        words = desc.split()
        line1, line2 = [], []
        current_len = 0
        for w in words:
            test_len = draw.textbbox((0, 0), " ".join(line1 + [w]), font=font_feature_desc)[2]
            if test_len > max_w and line1:
                line2.append(w)
            else:
                line1.append(w)
        draw.text((M + 22, y + 26), " ".join(line1), fill=GRAY, font=font_feature_desc)
        if line2:
            draw.text((M + 22, y + 50), " ".join(line2), fill=GRAY, font=font_feature_desc)
            y += 78
        else:
            y += 66
    else:
        draw.text((M + 22, y + 28), desc, fill=GRAY, font=font_feature_desc)
        y += 66

y += 16

# ── 8) BOTTOM CTA BAR ─────────────────────────────────────────────────
cta_h = 80
draw.rectangle([0, H - cta_h, W, H], fill="#0a0908")
draw.line([(0, H - cta_h), (W, H - cta_h)], fill=ORANGE, width=3)
center_text(draw, H - cta_h + 16, "dayshiftnow.me", font_cta, ORANGE)
center_text(draw, H - cta_h + 52, "iOS & Android   •   Free to download", font_tiny, DIM)

# ── Save ───────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
canvas.save(OUTPUT, format="PNG", optimize=True)
print(f"Saved: {OUTPUT} ({W}×{H})")
print(f"Size: {os.path.getsize(OUTPUT) / 1024:.0f} KB")
