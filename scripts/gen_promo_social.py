#!/usr/bin/env python3
"""Generate Day Shift social media promo image (1080×1080) with market analysis data.
   Fixed version — generous spacing, no clashing elements."""

import os
import sys
import qrcode
from PIL import Image as PILImage, ImageDraw, ImageFont

# ── Config ──────────────────────────────────────────────────────────────
W, H = 1080, 1080
BG = "#0c0a09"
ORANGE = "#f97316"
WHITE = "#fafaf9"
GRAY = "#a8a29e"
DARK = "#1c1917"
DIM = "#78716c"

TARGET_URL = "https://day-shift.workshop.build"
LOGO_PATH = "./public/dayshift-logo.png"
OUTPUT = "promo-assets/DayShift_Social_Market.png"

# ── Fonts ───────────────────────────────────────────────────────────────
FONT_DIR = "/usr/share/fonts/truetype/liberation"

def load_font(name, size):
    path = os.path.join(FONT_DIR, name)
    return ImageFont.truetype(path, size)

# Font sizes tuned for 1080px canvas with breathing room
font_brand      = load_font("LiberationSans-Bold.ttf", 42)
font_header     = load_font("LiberationSans-Bold.ttf", 28)
font_stat_big   = load_font("LiberationSans-Bold.ttf", 52)
font_stat_label = load_font("LiberationSans-Regular.ttf", 20)
font_body       = load_font("LiberationSans-Regular.ttf", 20)
font_small      = load_font("LiberationSans-Regular.ttf", 20)
font_tiny       = load_font("LiberationSans-Regular.ttf", 18)
font_position   = load_font("LiberationSans-Italic.ttf", 19)
font_feature_title = load_font("LiberationSans-Bold.ttf", 22)
font_cta        = load_font("LiberationSans-Bold.ttf", 24)

# ── Helpers ─────────────────────────────────────────────────────────────
def center_text(draw, y, text, font, fill, **kw):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), text, fill=fill, font=font, **kw)

def draw_rounded_rect(draw, coords, radius, fill, outline=None, width=1):
    x1, y1, x2, y2 = coords
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=width)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=width)
    draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill)
    draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill)

def draw_rounded_rect_outline(draw, coords, radius, outline, width=1):
    """Draw only the border of a rounded rect (for the positioning statement card)."""
    x1, y1, x2, y2 = coords
    r = radius
    # Draw 4 corner arcs
    draw.arc([x1, y1, x1 + 2*r, y1 + 2*r], 180, 270, fill=outline, width=width)
    draw.arc([x2 - 2*r, y1, x2, y1 + 2*r], 270, 360, fill=outline, width=width)
    draw.arc([x1, y2 - 2*r, x1 + 2*r, y2], 90, 180, fill=outline, width=width)
    draw.arc([x2 - 2*r, y2 - 2*r, x2, y2], 0, 90, fill=outline, width=width)
    # Draw 4 straight edges
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

# Subtle top-to-bottom gradient warmth
for i in range(H):
    shade = int(12 + (i / H) * 8)
    draw.line([(0, i), (W, i)], fill=(shade, int(shade * 0.85), int(shade * 0.75)))

draw = ImageDraw.Draw(canvas)  # refresh after gradient

# ══════════════════════════════════════════════════════════════════════
# LAYOUT — generous margins, clear zones, no overlap
# ══════════════════════════════════════════════════════════════════════

MARGIN = 48          # outer margin
GAP = 28             # gap between major sections
INNER = 24           # padding inside cards

y = MARGIN

# ── 1) HEADER ZONE ────────────────────────────────────────────────────
center_text(draw, y, "THE KITCHEN FLOOR IS SHIFTING", font_header, WHITE)
y += 38

# Thin orange accent line under header
draw.line([(MARGIN + 80, y), (W - MARGIN - 80, y)], fill=ORANGE, width=2)
y += GAP

# ── 2) TOP ROW: Positioning Statement (left) + QR Code (right) ────────
row_height = 280
card_width = int((W - 2*MARGIN - GAP) * 0.58)  # positioning statement gets more width
qr_zone_width = W - 2*MARGIN - GAP - card_width

# Positioning statement card (left)
ps_x = MARGIN
ps_y = y
ps_w = card_width
ps_h = row_height

# Card background (subtle dark)
draw_rounded_rect(draw, [ps_x, ps_y, ps_x + ps_w, ps_y + ps_h], radius=16, fill=DARK)
# Orange border
draw_rounded_rect_outline(draw, [ps_x, ps_y, ps_x + ps_w, ps_y + ps_h], radius=16, outline=ORANGE, width=3)

# Positioning statement text — wrapped with generous padding inside card
pos_lines = [
    "The default infrastructure that connects",
    "Cincinnati's food service labor market",
    "— one verified video profile and one",
    "matched shift at a time.",
]
text_x = ps_x + INNER + 12
line_y = ps_y + 30
line_spacing = 27
for line in pos_lines:
    # Highlight "Cincinnati's" in orange
    if "Cincinnati" in line:
        parts = line.split("Cincinnati")
        # Draw part before Cincinnati
        draw.text((text_x, line_y), parts[0], fill=WHITE, font=font_position)
        before_w = draw.textbbox((0, 0), parts[0], font=font_position)[2]
        # Draw "Cincinnati" in orange
        draw.text((text_x + before_w, line_y), "Cincinnati", fill=ORANGE, font=font_position)
        cin_w = draw.textbbox((0, 0), "Cincinnati", font=font_position)[2]
        # Draw rest
        draw.text((text_x + before_w + cin_w, line_y), parts[1], fill=WHITE, font=font_position)
    else:
        draw.text((text_x, line_y), line, fill=WHITE, font=font_position)
    line_y += line_spacing

# QR Zone (right)
qr_x = ps_x + ps_w + GAP
qr_y = y
qr_display_size = min(qr_zone_width - 20, row_height - 20)  # fit within zone
qr_resized_display = qr_img.resize((qr_display_size, qr_display_size), PILImage.LANCZOS)

# Ember glow behind QR (concentric ellipses)
glow_center_x = qr_x + qr_zone_width // 2
glow_center_y = qr_y + row_height // 2
for alpha_val in [25, 18, 12, 6, 3]:
    glow_size = qr_display_size + (25 - alpha_val) * 6
    glow_overlay = PILImage.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow_overlay)
    gdraw.ellipse(
        [glow_center_x - glow_size // 2, glow_center_y - glow_size // 2,
         glow_center_x + glow_size // 2, glow_center_y + glow_size // 2],
        fill=(249, 115, 22, alpha_val)
    )
    canvas.paste(PILImage.alpha_composite(canvas.convert("RGBA"), glow_overlay).convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(canvas)

qr_paste_x = qr_x + (qr_zone_width - qr_display_size) // 2
qr_paste_y = qr_y + (row_height - qr_display_size) // 2
canvas.paste(qr_resized_display, (qr_paste_x, qr_paste_y), qr_resized_display.convert("RGBA"))

y += row_height + GAP

# ── 3) $14K STAT BAR ──────────────────────────────────────────────────
bar_h = 80
draw_rounded_rect(draw, [MARGIN, y, W - MARGIN, y + bar_h], radius=14, fill=DARK)
center_text(draw, y + 8, "$14K", font_stat_big, ORANGE)
center_text(draw, y + 50, "lost per vacant line cook per year", font_small, GRAY)
y += bar_h + GAP - 4

# ── 4) THREE STAT CARDS ───────────────────────────────────────────────
stat_card_w = (W - 2*MARGIN - 2*GAP) // 3
stat_card_h = 110
stats_data = [
    ("73%", "word-of-mouth", "hires"),
    ("60%", "annual", "turnover"),
    ("$3.2B", "lost to", "unfilled shifts"),
]

sx = MARGIN
for val, sub1, sub2 in stats_data:
    draw_rounded_rect(draw, [sx, y, sx + stat_card_w, y + stat_card_h], radius=12, fill=DARK)
    center_text(draw, y + 12, val, font_stat_big, ORANGE)
    center_text(draw, y + 56, sub1, font_stat_label, GRAY)
    center_text(draw, y + 76, sub2, font_stat_label, GRAY)
    sx += stat_card_w + GAP

y += stat_card_h + GAP

# ── 5) WHY DAY SHIFT WINS divider ─────────────────────────────────────
center_text(draw, y, "— WHY DAY SHIFT WINS —", font_small, DIM)
y += 28

# ── 6) FEATURE BULLETS ────────────────────────────────────────────────
features = [
    ("Video Profiles",     "See skills before the interview"),
    ("Instant Matching",   "Fill tonight's gap today"),
    ("Built-In Chat",      "Confirm & coordinate in-app"),
    ("Reviews That Travel","Reputation follows you"),
]

bullet_y = y
for title, desc in features:
    draw.rectangle([MARGIN, bullet_y + 4, MARGIN + 5, bullet_y + 4 + 32], fill=ORANGE)
    draw.text((MARGIN + 16, bullet_y), title, fill=ORANGE, font=font_feature_title)
    draw.text((MARGIN + 16, bullet_y + 22), desc, fill=GRAY, font=font_small)
    bullet_y += 50

y = bullet_y + 20  # extra breathing room before CTA

# ── 7) BOTTOM CTA BAR ─────────────────────────────────────────────────
cta_h = 85
draw.rectangle([0, H - cta_h, W, H], fill="#0a0908")
draw.line([(0, H - cta_h), (W, H - cta_h)], fill=ORANGE, width=3)
center_text(draw, H - cta_h + 8, "dayshiftnow.me", font_cta, ORANGE)
center_text(draw, H - cta_h + 36, "New users get a free 7-day Boost automatically", font_small, GRAY)
center_text(draw, H - cta_h + 60, "SCAN THE CODE   •   iOS & Android   •   Free", font_tiny, DIM)

# ── Save ───────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
canvas.save(OUTPUT, format="PNG", optimize=True)
print(f"Saved: {OUTPUT} ({W}×{H})")
print(f"Size: {os.path.getsize(OUTPUT) / 1024:.0f} KB")
