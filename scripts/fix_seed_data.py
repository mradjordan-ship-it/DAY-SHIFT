"""
Fix seed data quality: unique images per user, realistic content for test posts, fix avatar dupe.
Uses unique Unsplash/Pexels stock photo URLs — no AI key needed.
"""
import os, sys
import psycopg2, psycopg2.extras

db_url = os.environ.get("DAYSH1_URL")
if not db_url:
    print("Missing DAYSH1_URL", file=sys.stderr)
    sys.exit(1)

conn = psycopg2.connect(db_url)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── Unique post images per user ─────────────────────────────────────
# Format: Pexels URLs with unique photo IDs per user persona
USER_IMAGES = {
    # Workers — chef portraits / food prep
    53: "https://images.pexels.com/photos/3338497/pexels-photo-3338497.jpeg?w=800&h=600&fit=crop",   # Marcus Johnson — chef plating
    54: "https://images.pexels.com/photos/3814446/pexels-photo-3814446.jpeg?w=800&h=600&fit=crop",   # Priya Patel — chef cooking (already unique, keep as-is? check)
    55: "https://images.pexels.com/photos/3873520/pexels-photo-3873520.jpeg?w=800&h=600&fit=crop",   # DeShawn Williams — chef in kitchen
    56: "https://images.pexels.com/photos/5943053/pexels-photo-5943053.jpeg?w=800&h=600&fit=crop",   # Sofia Rodriguez — Latin chef plating
    57: "https://images.pexels.com/photos/4252146/pexels-photo-4252146.jpeg?w=800&h=600&fit=crop",   # Aiden Chen — food prep/fusion
    58: "https://images.pexels.com/photos/6205750/pexels-photo-6205750.jpeg?w=800&h=600&fit=crop",   # Keisha Brown — pastry chef
    64: "https://images.pexels.com/photos/769969/pexels-photo-769969.jpeg?w=800&h=600&fit=crop",     # Tasha Williams — chef at work

    # Employers — restaurant / kitchen interiors
    59: "https://images.pexels.com/photos/262978/pexels-photo-262978.jpeg?w=800&h=600&fit=crop",    # The Golden Spoon — upscale restaurant
    60: "https://images.pexels.com/photos/1267320/pexels-photo-1267320.jpeg?w=800&h=600&fit=crop",  # Harlem Eats Kitchen — vibrant kitchen
    61: "https://images.pexels.com/photos/1435890/pexels-photo-1435890.jpeg?w=800&h=600&fit=crop",  # Sakura NYC — Japanese/modern (already unique? check)
    62: "https://images.pexels.com/photos/205961/pexels-photo-205961.jpeg?w=800&h=600&fit=crop",    # Brooklyn Bakehouse — bakery
    63: "https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?w=800&h=600&fit=crop",    # Catering Kings NYC — catering setup
    65: "https://images.pexels.com/photos/260922/pexels-photo-260922.jpeg?w=800&h=600&fit=crop",    # Marias Kitchen — cozy restaurant

    # Admin
    52: "https://images.pexels.com/photos/3184183/pexels-photo-3184183.jpeg?w=800&h=600&fit=crop",  # Day Shift Admin — networking/event
}

# Avatar fix — Catering Kings NYC gets a unique profile pic
AVATAR_FIX = (63, "https://images.pexels.com/photos/6267/menu-restaurant-vintage-table.jpg?w=200&h=200&fit=crop&crop=faces")

# ── Realistic content for test posts (IDs 221-234) ──────────────────
MARIA_POSTS = [
    {"title": "Line Cook Needed — Saturday Dinner Rush", "description": "Looking for an experienced line cook who can handle high-volume sauté and grill during our busiest shift of the week.", "pay_rate": "$25/hr", "hours": "5:00 PM - 11:00 PM", "location": "Williamsburg, Brooklyn", "cuisine_type": "Mexican", "event_date": "2026-07-11"},
    {"title": "Prep Cook — Morning Shift", "description": "Join our morning prep team! Chopping, marinating, and portioning for the day's service. Great for early risers.", "pay_rate": "$20/hr", "hours": "7:00 AM - 2:00 PM", "location": "Bushwick, Brooklyn", "cuisine_type": "Mexican", "event_date": "2026-07-12"},
    {"title": "Dishwasher / Kitchen Porter — Evening", "description": "Keep our kitchen running smooth. Reliable dishwasher needed for evening cleanup and dish pit management.", "pay_rate": "$18/hr", "hours": "6:00 PM - 12:00 AM", "location": "Williamsburg, Brooklyn", "cuisine_type": "Mexican", "event_date": "2026-07-14"},
    {"title": "Taco Station Cook — Weekend Pop-Up", "description": "We're running a weekend taco pop-up at Smorgasburg! Need someone fast and precise on the taco line.", "pay_rate": "$28/hr", "hours": "9:00 AM - 5:00 PM", "location": "Prospect Park, Brooklyn", "cuisine_type": "Mexican Street Food", "event_date": "2026-07-18"},
    {"title": "Pastry Assistant — Sunday Brunch Prep", "description": "Help our pastry team prep conchas, tres leches, and churros for our popular Sunday brunch service.", "pay_rate": "$22/hr", "hours": "5:00 AM - 12:00 PM", "location": "Bushwick, Brooklyn", "cuisine_type": "Mexican Bakery", "event_date": "2026-07-19"},
    {"title": "Grill Cook — Steak & Fajita Station", "description": "Experienced grill cook needed for our carne asada and fajita station. Must know temps and timing.", "pay_rate": "$26/hr", "hours": "4:00 PM - 10:00 PM", "location": "Williamsburg, Brooklyn", "cuisine_type": "Mexican Grill", "event_date": "2026-07-15"},
    {"title": "Salsa & Prep Station Lead", "description": "Own the salsa and cold prep station. Make our signature salsas, guacamole, and ceviches from scratch.", "pay_rate": "$23/hr", "hours": "8:00 AM - 3:00 PM", "location": "Greenpoint, Brooklyn", "cuisine_type": "Mexican", "event_date": "2026-07-16"},
    {"title": "Expeditor / Food Runner — Friday Night", "description": "Keep orders flowing between kitchen and floor. Must be fast, organized, and cool under pressure.", "pay_rate": "$19/hr", "hours": "5:00 PM - 11:00 PM", "location": "Williamsburg, Brooklyn", "cuisine_type": "Mexican", "event_date": "2026-07-17"},
    {"title": "Tamale Production Cook — Holiday Prep", "description": "We're making 500 tamales for a catering order. Need experienced hands for masa prep and assembly.", "pay_rate": "$24/hr", "hours": "6:00 AM - 2:00 PM", "location": "Bushwick, Brooklyn", "cuisine_type": "Mexican Catering", "event_date": "2026-07-22"},
    {"title": "Sous Chef — Dinner Service", "description": "Looking for a sous chef to help run dinner service and mentor junior cooks. Leadership experience required.", "pay_rate": "$30/hr", "hours": "3:00 PM - 11:00 PM", "location": "Williamsburg, Brooklyn", "cuisine_type": "Mexican Fine Dining", "event_date": "2026-07-20"},
    {"title": "Weekend Brunch Cook", "description": "Our brunch service needs an extra set of hands. Huevos rancheros, chilaquiles, breakfast burritos.", "pay_rate": "$22/hr", "hours": "8:00 AM - 3:00 PM", "location": "Bushwick, Brooklyn", "cuisine_type": "Mexican Brunch", "event_date": "2026-07-25"},
    {"title": "Catering Prep Cook — Corporate Lunch", "description": "Prepping for a 150-person corporate lunch order. Need efficient cooks who can work clean and fast.", "pay_rate": "$25/hr", "hours": "5:00 AM - 11:00 AM", "location": "DUMBO, Brooklyn", "cuisine_type": "Mexican Catering", "event_date": "2026-07-23"},
    {"title": "Tortilla Maker — Fresh Daily Production", "description": "We make our tortillas fresh every morning. Looking for someone who takes pride in the craft of handmade tortillas.", "pay_rate": "$21/hr", "hours": "5:00 AM - 10:00 AM", "location": "Bushwick, Brooklyn", "cuisine_type": "Mexican Artisanal", "event_date": "2026-07-21"},
    {"title": "Closing Cook / Clean-Up — Night Owl", "description": "Close down the kitchen after dinner service. Grill cleaning, station breakdown, prep list for tomorrow.", "pay_rate": "$20/hr", "hours": "10:00 PM - 2:00 AM", "location": "Williamsburg, Brooklyn", "cuisine_type": "Mexican", "event_date": "2026-07-24"},
]

# Only need 12 entries for Marias posts (IDs 221-224, 227-234)
MARIA_POSTS = MARIA_POSTS[:12]

ADMIN_POST = {"title": "Featured: Day Shift x NYC Restaurant Week — Bonus Pay Opportunities", "description": "NYC Restaurant Week is coming! We're highlighting kitchens offering premium pay for extra hands during the busiest dining week of summer. Swipe through for top-paying shifts.", "pay_rate": "Up to $35/hr", "hours": "Various shifts available", "location": "New York, NY", "cuisine_type": "Multiple Cuisines", "event_date": "2026-07-27"}

# ── Apply all changes ────────────────────────────────────────────────
print("=== Applying content to test posts ===")
cur2 = conn.cursor()

# Marias Kitchen test posts (221-234)
marias_posts = [221, 222, 223, 224, 227, 228, 229, 230, 231, 232, 233, 234]
for i, post_id in enumerate(marias_posts):
    if i < len(MARIA_POSTS):
        c = MARIA_POSTS[i]
        cur2.execute("""
            UPDATE videos SET title=%s, description=%s, pay_rate=%s, hours=%s,
            location=%s, cuisine_type=%s, event_date=%s, image_url=%s
            WHERE id=%s
        """, (c['title'], c['description'], c['pay_rate'], c['hours'],
              c['location'], c['cuisine_type'], c['event_date'],
              USER_IMAGES.get(65, ''), post_id))
        print(f"  Updated post {post_id}: {c['title']}")

# Admin test post (235)
cur2.execute("""
    UPDATE videos SET title=%s, description=%s, pay_rate=%s, hours=%s,
    location=%s, cuisine_type=%s, event_date=%s, image_url=%s
    WHERE id=235
""", (ADMIN_POST['title'], ADMIN_POST['description'], ADMIN_POST['pay_rate'],
      ADMIN_POST['hours'], ADMIN_POST['location'], ADMIN_POST['cuisine_type'],
      ADMIN_POST['event_date'], USER_IMAGES.get(52, ''),))
print(f"  Updated post 235: {ADMIN_POST['title']}")

# ── Fix avatar dupe ─────────────────────────────────────────────────
print("\n=== Fixing avatar dupe ===")
uid, new_av = AVATAR_FIX
cur2.execute("UPDATE users SET avatar_url=%s WHERE id=%s", (new_av, uid))
print(f"  Catering Kings NYC (id={uid}) avatar -> {new_av}")

# ── Assign unique images to users with dupes ─────────────────────────
print("\n=== Assigning unique post images ===")
for uid, img_url in USER_IMAGES.items():
    cur2.execute("UPDATE videos SET image_url=%s WHERE user_id=%s", (img_url, uid))
    affected = cur2.rowcount
    print(f"  user_id={uid}: {affected} posts -> {img_url[:60]}...")

conn.commit()
cur2.close()

# ── Verify ──────────────────────────────────────────────────────────
print("\n=== Verification ===")
cur.execute("""
    SELECT image_url, count(*) as cnt, array_agg(DISTINCT u.name) as users
    FROM videos v JOIN users u ON v.user_id = u.id
    WHERE image_url IS NOT NULL
    GROUP BY image_url HAVING count(DISTINCT u.id) > 1
""")
dupes = cur.fetchall()
if dupes:
    print(f"WARNING: {len(dupes)} image URLs still shared across users:")
    for d in dupes:
        print(f"  [{d['cnt']}x] users: {d['users']}")
else:
    print("✓ No duplicate images across different users")

# Check blank posts
cur.execute("""
    SELECT count(*) FROM videos 
    WHERE (title IS NULL OR title = '') 
    AND (description IS NULL OR description = 'User posted' OR description LIKE '%shift%test%' OR description LIKE '%Text:%' OR description LIKE '%AM shift%' OR description LIKE '%PM shift%')
""")
blank = cur.fetchone()['count']
print(f"  Test-looking posts remaining: {blank}")

cur.close()
conn.close()
print("\n✓ Done.")
