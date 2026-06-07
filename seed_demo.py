"""Seed demo data for Day Shift investor demo — with videos.

Run: python seed_demo.py
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DAYSHI_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DAYSHI_URL environment variable not set")

IMG = {
    "grill": "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=600&h=800&fit=crop",
    "prep": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&h=800&fit=crop",
    "pastry": "https://images.unsplash.com/photo-1556217477-d325251ece38?w=600&h=800&fit=crop",
    "team": "https://images.unsplash.com/photo-1577219491135-ce391730fb2c?w=600&h=800&fit=crop",
    "dining": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=800&fit=crop",
    "brunch": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&h=800&fit=crop",
    "steak": "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&h=800&fit=crop",
    "sushi": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=600&h=800&fit=crop",
    "cocktail": "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&h=800&fit=crop",
    "tacos": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=800&fit=crop",
}

VID = {
    "cooking": "https://videos.pexels.com/video-files/3195394/3195394-sd_640_360_25fps.mp4",
    "plating": "https://videos.pexels.com/video-files/5803517/5803517-sd_640_360_25fps.mp4",
    "kitchen": "https://videos.pexels.com/video-files/3015510/3015510-sd_640_360_24fps.mp4",
}

import bcrypt as _bcrypt
_DEMO_PW = _bcrypt.hashpw("demo123".encode(), _bcrypt.gensalt()).decode()


def seed():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    # ── Find admin ──
    cur.execute("SELECT id, name FROM users WHERE is_admin = TRUE LIMIT 1")
    admin = cur.fetchone()
    if not admin:
        print("No admin user found. Create your admin account first.")
        return
    admin_id = admin["id"]
    print(f"Admin: {admin['name']} (id={admin_id})")

    # ── Delete previous demo data ──
    demo_emails = [
        "maria@dayshift.demo", "james@dayshift.demo",
        "tasha@dayshift.demo", "diego@dayshift.demo",
        "flamefork@dayshift.demo", "sakura@dayshift.demo",
        "brunch@dayshift.demo", "tacomadre@dayshift.demo",
    ]
    for email in demo_emails:
        cur.execute("DELETE FROM videos WHERE user_id IN (SELECT id FROM users WHERE email = %s)", (email,))
        cur.execute("DELETE FROM users WHERE email = %s", (email,))
    conn.commit()
    print("Cleared previous demo data")

    # ── Create crew accounts ──
    crew = [
        ("Maria Santos", "maria@dayshift.demo",
         "Line cook with 8 years of experience. Grill & sauté specialist. Fast hands, clean station.",
         "https://images.unsplash.com/photo-1594744803329-e58b31de8bf5?w=200&h=200&fit=crop&crop=face"),
        ("James Carter", "james@dayshift.demo",
         "Prep cook & pastry enthusiast. Available mornings & weekends. ServSafe certified.",
         "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face"),
        ("Tasha Williams", "tasha@dayshift.demo",
         "Dish & prep double-threat. 5 years high-volume. Looking for steady day shifts.",
         "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=200&h=200&fit=crop&crop=face"),
        ("Diego Ramirez", "diego@dayshift.demo",
         "Sous chef & catering lead. Open to part-time & event gigs. Bilingual English/Spanish.",
         "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&h=200&fit=crop&crop=face"),
    ]
    crew_ids = []
    for name, email, bio, avatar in crew:
        cur.execute(
            """INSERT INTO users (name, email, password_hash, role, bio, avatar_url, avg_rating, total_shifts)
               VALUES (%s, %s, %s, 'worker', %s, %s, 4.5, 12) RETURNING id""",
            (name, email, _DEMO_PW, bio, avatar),
        )
        crew_ids.append(cur.fetchone()["id"])
    print(f"Created {len(crew_ids)} crew accounts")

    # ── Create spot accounts ──
    spots = [
        ("Flame & Fork Kitchen", "flamefork@dayshift.demo",
         "Upscale casual downtown. Farm-to-table menu, open kitchen, 80 covers.",
         "https://images.unsplash.com/photo-1552566626-52f8b828add9?w=200&h=200&fit=crop"),
        ("Sakura Ramen House", "sakura@dayshift.demo",
         "Authentic tonkotsu ramen shop. High volume, fast pace, loyal regulars.",
         "https://images.unsplash.com/photo-1579027989536-b7b1f875659b?w=200&h=200&fit=crop"),
        ("The Brunch Spot", "brunch@dayshift.demo",
         "Weekend brunch destination. Eggs benedict and bottomless mimosas.",
         "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=200&h=200&fit=crop"),
        ("Taco Madre", "tacomadre@dayshift.demo",
         "Food truck turned brick-and-mortar. Street tacos, daily specials, catering.",
         "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=200&h=200&fit=crop"),
    ]
    spot_ids = []
    for name, email, bio, avatar in spots:
        cur.execute(
            """INSERT INTO users (name, email, password_hash, role, bio, avatar_url, avg_rating, total_shifts)
               VALUES (%s, %s, %s, 'employer', %s, %s, 4.7, 50) RETURNING id""",
            (name, email, _DEMO_PW, bio, avatar),
        )
        spot_ids.append(cur.fetchone()["id"])
    print(f"Created {len(spot_ids)} spot accounts")

    # ── Sponsored posts (with video) ──
    sponsored = [
        (admin_id, VID["plating"], IMG["dining"], "employer", "video",
         "🔥 Day Shift Premium — Now Hiring!",
         "Top restaurants are hiring through Day Shift. Post your open shifts and let the crew come to you.",
         "Nationwide", "", "", "", 24),
        (admin_id, VID["cooking"], IMG["team"], "worker", "video",
         "⚡ New: Horizontal Browse",
         "Swipe through crew and spots side-by-side. Discover your next shift faster than ever.",
         "", "", "", "", 18),
        (admin_id, None, None, "employer", "text",
         None,
         "🛒 Culinary Utensils — Now available from Day Shift\n\nProfessional-grade tools shipped to your kitchen. Spatulas, tongs, knives & more.",
         "", "", "", "", 12),
    ]
    for s in sponsored:
        cur.execute(
            """INSERT INTO videos (user_id, video_url, image_url, type, post_type, title, description, location, pay_rate, cuisine_type, hours, likes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", s)
    print(f"Created {len(sponsored)} sponsored posts")

    # ── Crew posts (with videos) ──
    crew_posts = [
        (crew_ids[0], VID["cooking"], IMG["grill"], "worker", "video",
         "Grill & Sauté — Ready Today",
         "8 years on the line. Available for immediate day shifts. Fast, clean, reliable.",
         "Downtown", "$22/hr", "American", "Senior", 8),
        (crew_ids[1], None, IMG["pastry"], "worker", "image",
         "Prep & Pastry — Mornings",
         "ServSafe certified. Pastry is my passion, prep is my speed. Weekend availability too.",
         "Midtown", "$18/hr", "French", "Mid-Level", 5),
        (crew_ids[2], None, None, "worker", "text",
         None,
         "Dish & prep double-threat 💪\n5 years high-volume experience.\nLooking for steady day shifts — I show up early and stay until the line is clean.",
         "East Side", "$16/hr", "All", "Mid-Level", 3),
        (crew_ids[3], VID["kitchen"], IMG["prep"], "worker", "video",
         "Sous Chef — Event & Part-Time",
         "Catering lead with sous chef experience. Bilingual English/Spanish. Open to pop-ups & events.",
         "West Loop", "$28/hr", "Latin", "Senior", 11),
    ]
    for p in crew_posts:
        cur.execute(
            """INSERT INTO videos (user_id, video_url, image_url, type, post_type, title, description, location, pay_rate, cuisine_type, experience_level, likes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", p)
    print(f"Created {len(crew_posts)} crew posts")

    # ── Spot posts (with videos) ──
    spot_posts = [
        (spot_ids[0], VID["plating"], IMG["steak"], "employer", "video",
         "Line Cooks — Day Shift",
         "Farm-to-table kitchen hiring line cooks for day shifts. 80 covers, fast pace, great team.",
         "Downtown", "$20-24/hr", "American", "6am–2pm", 6),
        (spot_ids[1], None, IMG["sushi"], "employer", "image",
         "Prep Cook — Ramen House",
         "High-volume tonkotsu shop needs a prep cook. Must be fast and clean. Day shifts only.",
         "Chinatown", "$17-19/hr", "Japanese", "7am–3pm", 4),
        (spot_ids[2], VID["cooking"], IMG["brunch"], "employer", "video",
         "Weekend Brunch Line",
         "Eggs benedict factory needs you. Weekend brunch shifts, 200+ covers. Tips shared.",
         "River North", "$18/hr + tips", "Brunch", "Sat-Sun 8am–3pm", 9),
        (spot_ids[3], None, IMG["tacos"], "employer", "image",
         "Food Truck Crew",
         "Street taco truck hiring. Fast hands, good vibes. Lunch rushes Mon–Fri.",
         "South Loop", "$16-18/hr", "Mexican", "10am–3pm", 3),
        (spot_ids[0], None, IMG["cocktail"], "employer", "image",
         "Bartender / Barback — Days",
         "Upscale casual bar needs daytime coverage. Cocktail knowledge preferred but not required.",
         "Downtown", "$15/hr + tips", "American", "11am–5pm", 5),
    ]
    for p in spot_posts:
        cur.execute(
            """INSERT INTO videos (user_id, video_url, image_url, type, post_type, title, description, location, pay_rate, cuisine_type, hours, likes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", p)
    print(f"Created {len(spot_posts)} spot posts")

    conn.commit()
    cur.close()
    conn.close()
    print("\n✅ Demo data seeded with videos! Refresh your feed.")


if __name__ == "__main__":
    seed()
