"""
Seed script for Day Shift — populates all tables with realistic test data
for 3 account types: Admin, Worker, Employer.

Usage:
    .venv/bin/python seed_data.py
"""
import os
import bcrypt as _bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
import random

DATABASE_URL = os.environ.get("DAYSH1_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DAYSH1_URL not set")

def hash_pw(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8")[:72], _bcrypt.gensalt()).decode()

def now_utc():
    return datetime.now(timezone.utc)

def days_ago(n):
    return now_utc() - timedelta(days=n)

def hours_ago(n):
    return now_utc() - timedelta(hours=n)

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def seed():
    conn = get_conn()
    cur = conn.cursor()

    # ─── Check if already seeded ───────────────────────────────────────────
    cur.execute("SELECT count(*) FROM users")
    if cur.fetchone()["count"] > 0:
        print("Database already has users. Skipping seed.")
        print("Run: DELETE FROM users CASCADE; then re-run this script.")
        cur.close()
        conn.close()
        return

    print("Seeding Day Shift database...")

    # ═══════════════════════════════════════════════════════════════════════
    # 1. USERS — 1 admin, 6 workers, 5 employers
    # ═══════════════════════════════════════════════════════════════════════
    users = {}

    # Admin
    cur.execute("""
        INSERT INTO users (name, email, password_hash, role, is_admin, onboarded,
                          bio, avatar_url, avg_rating, total_shifts, location)
        VALUES (%s,%s,%s,%s,TRUE,TRUE,%s,%s,%s,%s,%s) RETURNING id
    """, (
        "Day Shift Admin",
        "admin@dayshift.app",
        hash_pw("admin123"),
        "admin",
        "Official Day Shift account. Sharing culinary opportunities across the city.",
        "",
        5.0, 150, "New York, NY"
    ))
    users["admin@dayshift.app"] = cur.fetchone()["id"]
    print(f"  Admin (id={users['admin@dayshift.app']})")

    # Workers
    worker_data = [
        ("Marcus Johnson", "marcus@cook.com", "worker",
         "Line cook with 8 years in NYC restaurants. Specializing in Southern cuisine and BBQ.",
         "https://images.unsplash.com/photo-1518882570151-157128e78fa1?w=200&h=200&fit=crop&crop=face", 4.7, 45, "Brooklyn, NY", "Southern, BBQ, Comfort Food", "8+ years", "Full-time / Flex"),
        ("Priya Patel", "priya@cook.com", "worker",
         "Pastry chef trained in French technique. Available for pop-ups and catering gigs.",
         "https://images.unsplash.com/photo-1601455763557-db1bea8a9a5a?w=200&h=200&fit=crop&crop=face", 4.9, 32, "Queens, NY", "French, Pastry, Baking", "5 years", "Part-time"),
        ("DeShawn Williams", "deshawn@cook.com", "worker",
         "Sushi chef looking for evening shifts. Fast prep, clean station every time.",
         "https://images.unsplash.com/photo-1522529599102-193c0d76b5b6?w=200&h=200&fit=crop&crop=face", 4.3, 28, "Manhattan, NY", "Japanese, Sushi, Asian Fusion", "6 years", "Evenings / Nights"),
        ("Sofia Rodriguez", "sofia@cook.com", "worker",
         "Line cook / grill specialist. Bilingual English/Spanish. Strong team player.",
         "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop&crop=face", 4.8, 51, "Bronx, NY", "Latin, Grill, Mexican", "10+ years", "Full-time"),
        ("Aiden Chen", "aiden@cook.com", "worker",
         "Recent culinary grad hungry for experience. Quick learner, adaptable to any station.",
         "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=face", 4.1, 12, "Harlem, NY", "Italian, Pan-Asian, Modern American", "1 year", "Flexible"),
        ("Keisha Brown", "keisha@cook.com", "worker",
         "Sous chef transitioning to freelance. Banquet and catering specialist.",
         "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=crop&crop=face", 4.6, 67, "Jersey City, NJ", "Catering, Soul Food, Banquets", "12 years", "Freelance"),
    ]

    for name, email, role, bio, avatar, rating, shifts, loc, cuisine, exp, hrs in worker_data:
        cur.execute("""
            INSERT INTO users (name, email, password_hash, role, is_admin, onboarded,
                              bio, avatar_url, avg_rating, total_shifts, location,
                              cuisine_type, experience_level, hours)
            VALUES (%s,%s,%s,%s,FALSE,TRUE,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            name, email, hash_pw("worker123"), role, bio, avatar, rating, shifts,
            loc, cuisine, exp, hrs
        ))
        users[email] = cur.fetchone()["id"]
        print(f"  Worker: {name} (id={users[email]})")

    # Employers
    employer_data = [
        ("The Golden Spoon", "golden@spoon.com", "employer",
         "Upscale Southern fusion restaurant in Midtown. Looking for reliable line cooks.",
         "https://images.unsplash.com/photo-1531384441138-2736e62e0919?w=200&h=200&fit=crop&crop=face", 4.5, 200, "Midtown, Manhattan", "Southern Fusion, Fine Dining", "$22-28/hr", "Dinner service 4pm-12am"),
        ("Harlem Eats Kitchen", "harlem@eats.com", "employer",
         "Fast-casual Caribbean spot in Harlem. Growing team, flexible schedules.",
         "https://images.unsplash.com/photo-1508341595667-9c136f6837f1?w=200&h=200&fit=crop&crop=face", 4.2, 85, "Harlem, NY", "Caribbean, Jamaican, Fast Casual", "$18-22/hr", "Lunch + Dinner shifts"),
        ("Sakura NYC", "sakura@nyc.com", "employer",
         "Authentic Japanese restaurant near Penn Station. Seeking experienced sushi prep.",
         "https://images.unsplash.com/photo-1633332755192-727a05c4013d?w=200&h=200&fit=crop&crop=face", 4.7, 120, "Penn Station area, NY", "Japanese, Sushi, Ramen", "$25-32/hr", "Nights 5pm-2am"),
        ("Brooklyn Bakehouse", "bake@brooklyn.com", "employer",
         "Artisan bakery and café. Need pastry help for morning prep and weekend rushes.",
         "https://images.unsplash.com/photo-1527201987695-67c06571957e?w=200&h=200&fit=crop&crop=face", 4.8, 95, "Williamsburg, Brooklyn", "Bakery, Pastry, Café", "$20-25/hr", "Mornings 5am-1pm"),
        ("Catering Kings NYC", "catering@kings.com", "employer",
         "Full-service catering company. Event-driven staffing needs, great pay.",
         "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=200&h=200&fit=crop&crop=face", 4.4, 150, "Chelsea, Manhattan", "Catering, Events, All Cuisines", "$200-400/event", "Event-based"),
    ]

    for name, email, role, bio, avatar, rating, shifts, loc, cuisine, pay, hrs in employer_data:
        cur.execute("""
            INSERT INTO users (name, email, password_hash, role, is_admin, is_advertiser,
                              onboarded, bio, avatar_url, avg_rating, total_shifts, location,
                              cuisine_type, hours)
            VALUES (%s,%s,%s,%s,FALSE,FALSE,TRUE,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            name, email, hash_pw("employer123"), role, bio, avatar, rating, shifts,
            loc, cuisine, hrs
        ))
        users[email] = cur.fetchone()["id"]
        print(f"  Employer: {name} (id={users[email]})")

    # Make one employer an advertiser
    cur.execute("UPDATE users SET is_advertiser=TRUE WHERE id=%s", (users["golden@spoon.com"],))
    # Make one worker also an advertiser (for testing both roles)
    cur.execute("UPDATE users SET is_advertiser=TRUE WHERE id=%s", (users["sofia@cook.com"],))

    conn.commit()
    print(f"\n  Total users: {len(users)}")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. VIDEOS / POSTS
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding videos/posts...")

    admin_id = users["admin@dayshift.app"]
    worker_emails = ["marcus@cook.com", "priya@cook.com", "deshawn@cook.com", "sofia@cook.com", "aiden@cook.com", "keisha@cook.com"]
    employer_emails = ["golden@spoon.com", "harlem@eats.com", "sakura@nyc.com", "bake@brooklyn.com", "catering@kings.com"]

    videos = {}

    # Admin sponsored posts
    admin_posts = [
        ("Now Hiring: Line Cooks Across NYC", "sponsored",
         "Day Shift connects culinary workers with kitchens that need them. Post your skills, get matched with shifts that fit your life.",
         "New York, NY", "All Cuisines", "$18-35/hr", "Flexible", "16:9", days_ago(1)),
        ("Featured Kitchen: The Golden Spoon", "sponsored",
         "Southern fusion done right. Currently booking experienced line cooks for dinner service. Apply through the app.",
         "Midtown Manhattan", "Southern Fusion", "$22-28/hr", "Dinner 4pm-12am", "16:9", days_ago(3)),
        ("Weekend Gigs Available", "sponsored",
         "Catering events across Manhattan this weekend. Need prep cooks, servers, and dishwashers. Great hourly rates.",
         "Manhattan, NY", "Catering, Events", "$200-400/event", "Event-based", "16:9", days_ago(5)),
    ]

    for i, (title, cat, desc, loc, cuisine, pay, hrs, ar, created) in enumerate(admin_posts):
        cur.execute("""
            INSERT INTO videos (user_id, type, post_type, category, title, description,
                              location, cuisine_type, pay_rate, hours, aspect_ratio,
                              image_url, likes, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            admin_id, "employer", "text", cat, title, desc,
            loc, cuisine, pay, hrs, ar,
            f"/api/media/sponsored_{i}.jpg", random.randint(15, 80), created
        ))
        videos[f"admin_sponsored_{i}"] = cur.fetchone()["id"]

    # Worker posts
    worker_posts = [
        ("marcus@cook.com", "Looking for a Line Cook gig", "general",
         "8 years on the line. Southern and BBQ specialist. Available for full-time or flexible shifts in Brooklyn/Manhattan.",
         "Brooklyn, NY", "Southern, BBQ", "$22/hr negot", "Full-time", "9:16", days_ago(7)),
        ("marcus@cook.com", "My Smoked Brisket Setup", "general",
         "Weekend BBQ pop-up looking for a home. Full brisket, ribs, and sides operation.",
         "Brooklyn, NY", "BBQ", "Pop-up", "Weekends", "9:16", days_ago(14)),
        ("priya@cook.com", "Pastry Chef Available", "general",
         "French-trained pastry chef. Croissants, tarts, custom cakes. Looking for part-time or catering work.",
         "Queens, NY", "French, Pastry", "$25/hr", "Part-time", "9:16", days_ago(5)),
        ("priya@cook.com", "Wedding Cake I Made Last Weekend", "general",
         "3-tier buttercream with sugar flowers. Happy to discuss custom orders for your next event.",
         "Queens, NY", "Pastry, Cakes", "Starting $300", "Event-based", "9:16", days_ago(10)),
        ("deshawn@cook.com", "Sushi Chef Seeking Night Shifts", "general",
         "Experienced sushi prep. Fast, clean, consistent. Available evenings in Manhattan.",
         "Manhattan, NY", "Japanese, Sushi", "$28/hr", "Nights 5pm-2am", "9:16", days_ago(3)),
        ("deshawn@cook.com", "My Omakase Plate", "general",
         "12-course omakase I prepped for a private event. Quality speaks for itself.",
         "Manhattan, NY", "Japanese", "Private events", "Flexible", "9:16", days_ago(8)),
        ("sofia@cook.com", "Grill Cook Available", "general",
         "10 years on the grill. Latin and Mexican cuisine specialist. English/Spanish bilingual.",
         "Bronx, NY", "Latin, Grill, Mexican", "$24/hr", "Full-time", "9:16", days_ago(2)),
        ("sofia@cook.com", "Weekend Taco Pop-Up", "general",
         "Looking for spaces to host my taco pop-up. Birria, al pastor, carnitas — the real deal.",
         "Bronx / Manhattan", "Mexican Street Food", "Pop-up", "Weekends", "9:16", days_ago(12)),
        ("aiden@cook.com", "Culinary Grad Looking for First Gig", "general",
         "Fresh out of ICE. Trained in Italian, Pan-Asian, and modern American. Willing to start at any station.",
         "Harlem, NY", "Multi-cuisine", "$18/hr", "Flexible", "9:16", days_ago(1)),
        ("keisha@cook.com", "Sous Chef for Hire — Banquets", "general",
         "12 years catering experience. Can run a 500-person banquet solo. DM for availability.",
         "Jersey City, NJ", "Catering, Banquets", "$250/event min", "Freelance", "9:16", days_ago(4)),
        ("keisha@cook.com", "Soul Food Sunday I Catered", "general",
         "Fried chicken, mac and cheese, collard greens, cornbread. 150 guests, all homemade.",
         "Jersey City, NJ", "Soul Food", "Catering", "Event-based", "9:16", days_ago(9)),
    ]

    for email, title, cat, desc, loc, cuisine, pay, hrs, ar, created in worker_posts:
        uid = users[email]
        cur.execute("""
            INSERT INTO videos (user_id, type, post_type, category, title, description,
                              location, cuisine_type, pay_rate, hours, aspect_ratio,
                              image_url, likes, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            uid, "worker", "text", cat, title, desc,
            loc, cuisine, pay, hrs, ar,
            f"/api/media/worker_{random.randint(100,999)}.jpg",
            random.randint(5, 60), created
        ))
        key = f"worker_{email}_{title[:15]}"
        videos[key] = cur.fetchone()["id"]

    # Employer posts
    employer_posts = [
        ("golden@spoon.com", "Hiring Line Cook — Southern Fusion", "general",
         "Immediate opening for experienced line cook. Dinner service, Tuesday-Sunday. Competitive pay + tips.",
         "Midtown Manhattan", "Southern Fusion", "$22-28/hr", "Dinner 4pm-12am", "9:16", days_ago(6)),
        ("golden@spoon.com", "Our Kitchen in Action", "general",
         "Behind the scenes at The Golden Spoon. Come be part of the team.",
         "Midtown Manhattan", "Southern Fusion", "", "", "16:9", days_ago(11)),
        ("harlem@eats.com", "Line Cook Wanted — Caribbean Kitchen", "general",
         "Growing team! Need a solid line cook who can handle lunch and dinner rushes. Jamaican experience a plus.",
         "Harlem, NY", "Caribbean, Jamaican", "$18-22/hr", "Lunch + Dinner", "9:16", days_ago(4)),
        ("harlem@eats.com", "Weekend Help Needed", "general",
         "Extra hands needed this Saturday and Sunday. Busy brunch service. Same-day pay available.",
         "Harlem, NY", "Caribbean", "$20/hr cash", "Sat-Sun 10am-4pm", "9:16", days_ago(1)),
        ("sakura@nyc.com", "Sushi Prep Cook — Full Time", "general",
         "Seeking experienced sushi chef for evening service. Must be proficient with knife work and fish prep.",
         "Penn Station area", "Japanese, Sushi", "$25-32/hr", "Nights 5pm-2am", "9:16", days_ago(8)),
        ("sakura@nyc.com", "New Ramen Bar Opening Soon", "general",
         "Expanding our menu with a dedicated ramen station. Looking for noodle specialists.",
         "Penn Station area", "Japanese, Ramen", "$22-28/hr", "Nights", "16:9", days_ago(13)),
        ("bake@brooklyn.com", "Morning Pastry Prep", "general",
         "Need a reliable pastry cook for 5am start. Croissants, breads, and morning prep. Williamsburg.",
         "Williamsburg, Brooklyn", "Bakery, Pastry", "$20-25/hr", "Mornings 5am-1pm", "9:16", days_ago(3)),
        ("bake@brooklyn.com", "Weekend Café Rush", "general",
         "Saturday and Sunday morning rushes. Need prep help and someone who can handle high volume.",
         "Williamsburg, Brooklyn", "Bakery, Café", "$22/hr + tips", "Weekends 6am-2pm", "9:16", days_ago(2)),
        ("catering@kings.com", "Catering Staff Needed This Weekend", "event",
         "Corporate event for 300 guests in Chelsea. Need 4 prep cooks, 2 servers. $300 flat rate per person.",
         "Chelsea, Manhattan", "All Cuisines", "$300/event", "This Saturday", "16:9", days_ago(1)),
        ("catering@kings.com", "Wedding Season is Here", "general",
         "Booking catering teams for wedding season. Reliable crews only. Top pay for experienced staff.",
         "All NYC", "Catering, Events", "$200-400/event", "Event-based", "16:9", days_ago(6)),
    ]

    for email, title, cat, desc, loc, cuisine, pay, hrs, ar, created in employer_posts:
        uid = users[email]
        cur.execute("""
            INSERT INTO videos (user_id, type, post_type, category, title, description,
                              location, cuisine_type, pay_rate, hours, aspect_ratio,
                              event_date, event_time,
                              image_url, likes, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            uid, "employer", "text", cat, title, desc,
            loc, cuisine, pay, hrs, ar,
            "2025-06-14" if cat == "event" else "",
            "10:00 AM" if cat == "event" else "",
            f"/api/media/employer_{random.randint(100,999)}.jpg",
            random.randint(8, 45), created
        ))
        key = f"employer_{email}_{title[:15]}"
        videos[key] = cur.fetchone()["id"]

    conn.commit()
    print(f"  Total videos: {len(videos)}")

    # ═══════════════════════════════════════════════════════════════════════
    # 3. MATCHES — various statuses across workers ↔ employers
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding matches...")

    matches = {}

    # Active matches (both confirmed)
    match_defs = [
        ("marcus@cook.com", "golden@spoon.com", "active", "marcus_golden", days_ago(10)),
        ("priya@cook.com", "bake@brooklyn.com", "active", "priya_bakehouse", days_ago(8)),
        ("sofia@cook.com", "harlem@eats.com", "active", "sofia_harlem", days_ago(5)),
    ]

    for w_email, e_email, status, key, created in match_defs:
        w_id = users[w_email]
        e_id = users[e_email]
        cur.execute("""
            INSERT INTO matches (worker_id, employer_id, status, initiated_by,
                                worker_confirmed, employer_confirmed, created_at)
            VALUES (%s,%s,%s,%s,TRUE,TRUE,%s) RETURNING id
        """, (w_id, e_id, status, w_id, created))
        matches[key] = cur.fetchone()["id"]

    # Pending matches (worker initiated, employer hasn't confirmed yet)
    pending_defs = [
        ("deshawn@cook.com", "sakura@nyc.com", "deshawn_sakura"),
        ("aiden@cook.com", "harlem@eats.com", "aiden_harlem"),
    ]
    for w_email, e_email, key in pending_defs:
        cur.execute("""
            INSERT INTO matches (worker_id, employer_id, status, initiated_by,
                                worker_confirmed, employer_confirmed, created_at)
            VALUES (%s,%s,'pending',%s,TRUE,FALSE,%s) RETURNING id
        """, (users[w_email], users[e_email], users[w_email], days_ago(2)))
        matches[key] = cur.fetchone()["id"]

    # Pending matches (employer initiated, worker hasn't confirmed yet)
    pending_employer = [
        ("sakura@nyc.com", "keisha@cook.com", "sakura_keisha"),
        ("catering@kings.com", "marcus@cook.com", "catering_marcus"),
    ]
    for e_email, w_email, key in pending_employer:
        cur.execute("""
            INSERT INTO matches (worker_id, employer_id, status, initiated_by,
                                worker_confirmed, employer_confirmed, created_at)
            VALUES (%s,%s,'pending',%s,FALSE,TRUE,%s) RETURNING id
        """, (users[w_email], users[e_email], users[e_email], hours_ago(12)))
        matches[key] = cur.fetchone()["id"]

    # Completed matches
    completed_defs = [
        ("keisha@cook.com", "catering@kings.com", "keisha_catering_done", days_ago(20)),
        ("marcus@cook.com", "harlem@eats.com", "marcus_harlem_done", days_ago(30)),
        ("priya@cook.com", "golden@spoon.com", "priya_golden_done", days_ago(45)),
    ]
    for w_email, e_email, key, created in completed_defs:
        cur.execute("""
            INSERT INTO matches (worker_id, employer_id, status, initiated_by,
                                worker_confirmed, employer_confirmed, created_at)
            VALUES (%s,%s,'completed',%s,TRUE,TRUE,%s) RETURNING id
        """, (users[w_email], users[e_email], users[w_email], created))
        matches[key] = cur.fetchone()["id"]

    # Cancelled match
    cur.execute("""
        INSERT INTO matches (worker_id, employer_id, status, initiated_by,
                            worker_confirmed, employer_confirmed, created_at)
        VALUES (%s,%s,'cancelled',%s,TRUE,TRUE,%s) RETURNING id
    """, (users["aiden@cook.com"], users["sakura@nyc.com"], users["aiden@cook.com"], days_ago(15)))
    matches["aiden_sakura_cancel"] = cur.fetchone()["id"]

    conn.commit()
    print(f"  Total matches: {len(matches)}")

    # ═══════════════════════════════════════════════════════════════════════
    # 4. MESSAGES — realistic conversations in active matches
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding messages...")

    message_count = 0

    # Marcus ↔ Golden Spoon (active)
    convos = [
        (matches["marcus_golden"], users["marcus@cook.com"], [
            "Hey! I saw your posting for a line cook. I've got 8 years experience with Southern cuisine. Interested!",
            "Hi Marcus! Thanks for reaching out. Can you do dinner service Tuesday through Sunday?",
            "Absolutely. I'm available those nights. What's the pay range?",
            "We're offering $24-28/hr plus tips. You'd start on the grill station.",
            "That works for me. I can start next week if you need me.",
            "Perfect. Come in Tuesday at 3pm for a trial shift. Ask for Chef Thompson at the back entrance.",
            "See you Tuesday!",
        ]),
        (matches["marcus_golden"], users["golden@spoon.com"], [
            "Hi Marcus! Thanks for reaching out. Can you do dinner service Tuesday through Sunday?",
            "We're offering $24-28/hr plus tips. You'd start on the grill station.",
            "Perfect. Come in Tuesday at 3pm for a trial shift. Ask for Chef Thompson at the back entrance.",
        ]),

        (matches["priya_bakehouse"], users["priya@cook.com"], [
            "Hi! I'm a pastry chef and I saw you need morning prep help. I'd love to chat about it.",
            "Hey Priya! Yes, we need someone reliable for 5am starts. Is that something you can do?",
            "5am works for me. I'm used to early mornings — pastry life! What do you need prepped?",
            "Croissants, muffins, bread dough. We do everything from scratch.",
            "That's my specialty. I can start whenever you need.",
            "Great, how about this Saturday? Come at 4:45am so we can get you set up.",
        ]),
        (matches["priya_bakehouse"], users["bake@brooklyn.com"], [
            "Hey Priya! Yes, we need someone reliable for 5am starts. Is that something you can do?",
            "Croissants, muffins, bread dough. We do everything from scratch.",
            "Great, how about this Saturday? Come at 4:45am so we can get you set up.",
        ]),

        (matches["sofia_harlem"], users["sofia@cook.com"], [
            "Hola! Interested in the line cook position. I've worked Caribbean and Mexican kitchens for 10 years.",
            "Hey Sofia! That's exactly what we're looking for. When can you start?",
            "I can do a trial shift tomorrow if that works.",
            "Tomorrow works. Come at 4pm. It'll be a busy Friday night — good way to see the flow.",
            "Sounds good. See you then. Should I bring my own knife set?",
            "If you have them, bring them. We have house knives too.",
        ]),
        (matches["sofia_harlem"], users["harlem@eats.com"], [
            "Hey Sofia! That's exactly what we're looking for. When can you start?",
            "Tomorrow works. Come at 4pm. It'll be a busy Friday night — good way to see the flow.",
            "If you have them, bring them. We have house knives too.",
        ]),

        # Pending match messages
        (matches["deshawn_sakura"], users["deshawn@cook.com"], [
            "I'm interested in the sushi prep position. I have 6 years experience in sushi restaurants.",
        ]),
        (matches["sakura_keisha"], users["sakura@nyc.com"], [
            "Hi Keisha, we saw your profile and we're looking for experienced catering help. Are you available for events this month?",
        ]),
        (matches["catering_marcus"], users["catering@kings.com"], [
            "Hey Marcus, we have a corporate event next Saturday and need someone with BBQ experience. You available?",
        ]),
    ]

    for match_id, sender_id, msgs in convos:
        for i, msg_text in enumerate(msgs):
            cur.execute("""
                INSERT INTO messages (match_id, sender_id, content, created_at)
                VALUES (%s,%s,%s,%s)
            """, (match_id, sender_id, msg_text, days_ago(10 - i)))
            message_count += 1

    conn.commit()
    print(f"  Total messages: {message_count}")

    # ═══════════════════════════════════════════════════════════════════════
    # 5. REVIEWS — on completed matches
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding reviews...")

    review_data = [
        (matches["keisha_catering_done"], users["catering@kings.com"], users["keisha@cook.com"], 5,
         "Absolutely incredible. Keisha ran our 200-person gala flawlessly. Will book again."),
        (matches["keisha_catering_done"], users["keisha@cook.com"], users["catering@kings.com"], 4,
         "Good team to work with. Clear instructions, paid on time."),
        (matches["marcus_harlem_done"], users["harlem@eats.com"], users["marcus@cook.com"], 4,
         "Marcus knows his Southern food. Fit right in with the team."),
        (matches["marcus_harlem_done"], users["marcus@cook.com"], users["harlem@eats.com"], 5,
         "Great vibes at Harlem Eats. Loved the menu and the crew."),
        (matches["priya_golden_done"], users["golden@spoon.com"], users["priya@cook.com"], 5,
         "Priya's pastry work is next level. Her croissants sold out every shift."),
        (matches["priya_golden_done"], users["priya@cook.com"], users["golden@spoon.com"], 4,
         "Professional kitchen, high standards. Learned a lot."),
    ]

    for match_id, reviewer, reviewee, rating, feedback in review_data:
        cur.execute("""
            INSERT INTO reviews (match_id, reviewer_id, reviewee_id, rating, feedback, created_at)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (match_id, reviewer, reviewee, rating, feedback, days_ago(15)))
        print(f"  Review: {rating}★ — {feedback[:50]}...")

    conn.commit()

    # ═══════════════════════════════════════════════════════════════════════
    # 6. LIKES
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding likes...")

    like_count = 0
    # Each user likes a random selection of other users' posts
    all_video_ids = list(videos.values())
    all_user_ids = [users[k] for k in list(users.keys()) if k != "admin@dayshift.app"]

    for uid in all_user_ids:
        # Like 3-6 random posts (not their own)
        their_posts = set()
        for vid_key, vid_id in videos.items():
            pass  # We'll just randomly pick
        targets = random.sample(all_video_ids, min(random.randint(3, 6), len(all_video_ids)))
        for vid in targets:
            try:
                cur.execute("""
                    INSERT INTO likes (user_id, video_id, created_at) VALUES (%s,%s,%s)
                """, (uid, vid, hours_ago(random.randint(1, 168))))
                like_count += 1
            except Exception:
                pass  # duplicate, skip

    conn.commit()
    print(f"  Total likes: {like_count}")

    # ═══════════════════════════════════════════════════════════════════════
    # 7. BOOKMARKS
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding bookmarks...")

    bookmark_count = 0
    # Bookmark some employer posts from workers
    employer_video_keys = [k for k in videos if k.startswith("employer_")]
    worker_video_keys = [k for k in videos if k.startswith("worker_")]
    sponsored_keys = [k for k in videos if k.startswith("admin_")]

    bookmark_map = {
        "marcus@cook.com": employer_video_keys[:2] + sponsored_keys[:1],
        "priya@cook.com": employer_video_keys[2:4] + sponsored_keys[1:2],
        "deshawn@cook.com": [employer_video_keys[4]] if len(employer_video_keys) > 4 else employer_video_keys[:1],
        "sofia@cook.com": employer_video_keys[1:3],
        "aiden@cook.com": employer_video_keys[:1],
        "keisha@cook.com": employer_video_keys[4:] if len(employer_video_keys) > 4 else [],
    }

    for email, keys in bookmark_map.items():
        for vk in keys:
            if vk in videos:
                try:
                    cur.execute("""
                        INSERT INTO bookmarks (user_id, video_id, created_at) VALUES (%s,%s,%s)
                    """, (users[email], videos[vk], days_ago(random.randint(1, 5))))
                    bookmark_count += 1
                except Exception:
                    pass

    conn.commit()
    print(f"  Total bookmarks: {bookmark_count}")

    # ═══════════════════════════════════════════════════════════════════════
    # 8. POST BOOSTS (advertiser content)
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding post boosts...")

    # Golden Spoon (advertiser) has some boosts on their posts
    gs_videos = [k for k in videos if k.startswith("employer_golden")]
    bb_videos = [k for k in videos if k.startswith("employer_bake")]

    for vk in gs_videos[:2]:
        cur.execute("""
            INSERT INTO post_boosts (video_id, user_id, tier, status, start_date, end_date,
                                    payment_status, admin_approved, created_at)
            VALUES (%s,%s,'boost','active',%s,%s,'paid',TRUE,%s)
        """, (videos[vk], users["golden@spoon.com"], days_ago(3), days_ago(-4), days_ago(5)))
        print(f"  Active boost: {vk}")

    # Pending boost from Brooklyn Bakehouse
    if bb_videos:
        cur.execute("""
            INSERT INTO post_boosts (video_id, user_id, tier, status, start_date, end_date,
                                    payment_status, admin_approved, created_at)
            VALUES (%s,%s,'spotlight','pending',NULL,NULL,'unpaid',FALSE,%s)
        """, (videos[bb_videos[0]], users["bake@brooklyn.com"], days_ago(1)))
        print(f"  Pending boost: Brooklyn Bakehouse")

    conn.commit()

    # ═══════════════════════════════════════════════════════════════════════
    # 9. POST ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding analytics...")

    analytics_count = 0
    for vid_key, vid_id in list(videos.items())[:15]:
        for day_offset in range(7):
            date = (now_utc() - timedelta(days=day_offset)).date()
            cur.execute("""
                INSERT INTO post_analytics (video_id, date, views, profile_clicks, match_requests)
                VALUES (%s,%s,%s,%s,%s)
            """, (vid_id, date, random.randint(5, 120), random.randint(0, 15), random.randint(0, 5)))
            analytics_count += 1

    conn.commit()
    print(f"  Total analytics rows: {analytics_count}")

    # ═══════════════════════════════════════════════════════════════════════
    # 10. SUPPORT THREADS
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding support threads...")

    # Open thread from a user
    cur.execute("""
        INSERT INTO support_threads (user_id, subject, status, created_at, updated_at)
        VALUES (%s,%s,'open',%s,%s) RETURNING id
    """, (users["marcus@cook.com"], "Can't upload video from my phone", days_ago(3), days_ago(1)))
    thread1 = cur.fetchone()["id"]

    cur.execute("""
        INSERT INTO support_messages (thread_id, sender_id, sender_role, content, created_at) VALUES
        (%s,%s,'user','Every time I try to upload a video, it says error. Using iPhone 15.',%s),
        (%s,NULL,'auto','Thank you for contacting Day Shift support. A team member will respond within 24 hours.',%s),
        (%s,NULL,'admin','Hi Marcus! Could you try uploading from a different browser? Also check that your video is under 100MB and in MP4 format.',%s),
        (%s,%s,'user','Tried Safari and Chrome, same issue. My video is only 45MB MP4.',%s)
    """, (thread1, users["marcus@cook.com"], days_ago(3),
          thread1, days_ago(3),
          thread1, days_ago(2),
          thread1, users["marcus@cook.com"], days_ago(1)))

    # Closed thread
    cur.execute("""
        INSERT INTO support_threads (user_id, subject, status, created_at, updated_at)
        VALUES (%s,%s,'closed',%s,%s) RETURNING id
    """, (users["priya@cook.com"], "How to delete my account?", days_ago(14), days_ago(12)))
    thread2 = cur.fetchone()["id"]

    cur.execute("""
        INSERT INTO support_messages (thread_id, sender_id, sender_role, content, created_at) VALUES
        (%s,%s,'user','I want to delete my account. How do I do that?',%s),
        (%s,NULL,'admin','Hi Priya, you can delete your account from Settings > Account > Delete Account. Note: this action is permanent.',%s),
        (%s,%s,'user','Found it, thanks!',%s)
    """, (thread2, users["priya@cook.com"], days_ago(14),
          thread2, days_ago(13),
          thread2, users["priya@cook.com"], days_ago(12)))

    conn.commit()
    print(f"  Support threads: 2 (1 open, 1 closed)")

    # ═══════════════════════════════════════════════════════════════════════
    # 11. SPONSOR CONTACTS
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding sponsor contacts...")

    sponsor_data = [
        ("James Mitchell", "james@restaurantgroup.com", "212-555-0100", "NYC Restaurant Group", "sponsor",
         "Interested in sponsoring job postings across Manhattan. Budget: $500/month to start."),
        ("Lisa Chang", "lisa@foodfestival.nyc", "212-555-0200", "NYC Food Festival", "partner",
         "We'd like to partner with Day Shift for our annual food festival. Need 50+ kitchen workers."),
        ("Michael Torres", "mike@cateringco.com", "", "MT Catering Co", "sponsor",
         "Want to boost our job postings to reach more workers."),
    ]

    for name, email, phone, org, typ, msg in sponsor_data:
        cur.execute("""
            INSERT INTO sponsor_contacts (name, email, phone, organization, type, message, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (name, email, phone, org, typ, msg, days_ago(random.randint(1, 10))))
        sc_id = cur.fetchone()["id"]

        # Admin reply on the first one
        if name == "James Mitchell":
            cur.execute("""
                INSERT INTO sponsor_replies (contact_id, admin_id, content, created_at)
                VALUES (%s,%s,%s,%s)
            """, (sc_id, admin_id, "Hi James! Thanks for your interest. Let's set up a call to discuss sponsorship tiers. What days work for you?", days_ago(9)))

    conn.commit()
    print(f"  Sponsor contacts: {len(sponsor_data)}")

    # ═══════════════════════════════════════════════════════════════════════
    # 12. TIPS
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding tips...")

    tip_data = [
        (users["marcus@cook.com"], 500, "Sarah M.", "sarah@email.com", "Love the app! Here's a tip to keep it going."),
        (users["priya@cook.com"], 1000, "", "", "Anonymous tip. Great platform."),
        (users["admin@dayshift.app"], 2000, "Big Restaurant Corp", "contact@bigcorp.com", "Here's $20 to support culinary workers finding opportunities."),
    ]

    for uid, amount, name, email, msg in tip_data:
        cur.execute("""
            INSERT INTO tips (user_id, amount, name, email, message, status, created_at)
            VALUES (%s,%s,%s,%s,%s,'completed',%s)
        """, (uid, amount, name, email, msg, days_ago(random.randint(1, 7))))

    conn.commit()
    print(f"  Tips: {len(tip_data)}")

    # ═══════════════════════════════════════════════════════════════════════
    # 13. ADVERTISER SUBSCRIPTION
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding advertiser subscriptions...")

    cur.execute("""
        INSERT INTO advertiser_subscriptions (user_id, tier, start_date, end_date,
                                            boosts_used, boosts_remaining, status, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,'active',%s)
    """, (users["golden@spoon.com"], "boost", days_ago(10), days_ago(-20), 2, 3, days_ago(10)))

    conn.commit()
    print("  Advertiser subscription: Golden Spoon (boost tier)")

    # ═══════════════════════════════════════════════════════════════════════
    # 14. REPORTS
    # ═══════════════════════════════════════════════════════════════════════
    print("\nSeeding reports...")

    # Get video IDs for the reports
    sofia_vid = videos.get("worker_sofia@cook.comGrill Cook Av")
    aiden_vid = videos.get("worker_aiden@cook.comCulinary Grad Lo")
    # Fallback: get first video for sofia and aiden
    if not sofia_vid:
        cur.execute("SELECT id FROM videos WHERE user_id=%s LIMIT 1", (users["sofia@cook.com"],))
        r = cur.fetchone()
        sofia_vid = r["id"] if r else None
    if not aiden_vid:
        cur.execute("SELECT id FROM videos WHERE user_id=%s LIMIT 1", (users["aiden@cook.com"],))
        r = cur.fetchone()
        aiden_vid = r["id"] if r else None

    if sofia_vid:
        cur.execute("""
            INSERT INTO reports (reporter_id, target_type, target_id, reason, created_at)
            VALUES (%s,'video',%s,%s,%s)
        """, (users["aiden@cook.com"], sofia_vid, "Spam or misleading content", days_ago(1)))
    if aiden_vid:
        cur.execute("""
            INSERT INTO reports (reporter_id, target_type, target_id, reason, created_at)
            VALUES (%s,'video',%s,%s,%s)
        """, (users["deshawn@cook.com"], aiden_vid, "Inappropriate content", days_ago(2)))

    conn.commit()
    print("  Reports: 2")

    # ═══════════════════════════════════════════════════════════════════════
    # DONE
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("SEED COMPLETE!")
    print("="*60)
    print()
    print("ACCOUNTS FOR TESTING:")
    print()
    print("  ADMIN:")
    print("    Email:    admin@dayshift.app")
    print("    Password: admin123")
    print()
    print("  WORKERS:")
    print("    marcus@cook.com    / worker123  (Marcus Johnson — Southern/BBQ)")
    print("    priya@cook.com     / worker123  (Priya Patel — Pastry)")
    print("    deshawn@cook.com   / worker123  (DeShawn Williams — Sushi)")
    print("    sofia@cook.com     / worker123  (Sofia Rodriguez — Grill/Latin)")
    print("    aiden@cook.com     / worker123  (Aiden Chen — Recent grad)")
    print("    keisha@cook.com    / worker123  (Keisha Brown — Catering)")
    print()
    print("  EMPLOYERS:")
    print("    golden@spoon.com   / employer123  (The Golden Spoon — Southern Fusion)")
    print("    harlem@eats.com    / employer123  (Harlem Eats Kitchen — Caribbean)")
    print("    sakura@nyc.com     / employer123  (Sakura NYC — Japanese)")
    print("    bake@brooklyn.com  / employer123  (Brooklyn Bakehouse — Bakery)")
    print("    catering@kings.com / employer123  (Catering Kings — Events)")
    print()
    print("  ADVERTISERS (can boost posts):")
    print("    golden@spoon.com  (employer, is_advertiser=TRUE)")
    print("    sofia@cook.com   (worker, is_advertiser=TRUE)")
    print()
    cur.close()
    conn.close()


if __name__ == "__main__":
    seed()
