"""
Generate AI content and images for Day Shift seed data cleanup.
- Content for blank posts (text generation)
- Unique images per user (Nano Banana)
- Avatar fix for duplicate
"""
import os, sys, base64, time, json
import psycopg2, psycopg2.extras
from google import genai
from google.genai import types

api_key = os.environ.get("STRIPE_GOOGLE_API_KEY")
base_url = os.environ.get("STRIPE_GOOGLE_BASE_URL")
db_url = os.environ.get("DAYSH1_URL")

if not all([api_key, db_url]):
    print("Missing env vars", file=sys.stderr)
    sys.exit(1)

client = genai.Client(
    api_key=api_key,
    http_options={"api_version": "v1alpha", "base_url": base_url or None},
)

conn = psycopg2.connect(db_url)

# ── STEP 1: Generate content for blank posts ────────────────────────
print("=== STEP 1: Generating content for blank posts ===")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Get Marias Kitchen and Admin user info
cur.execute("SELECT id, name, role, cuisine_type, location, kitchen_type FROM users WHERE id IN (52, 65)")
user_info = {u['id']: u for u in cur.fetchall()}

# Get blank posts
cur.execute("""SELECT id, user_id FROM videos 
WHERE (title IS NULL OR title = '') AND (description IS NULL OR description = '')
AND (image_url IS NULL OR image_url = '') AND (video_url IS NULL OR video_url = '')
ORDER BY id""")
blank_posts = cur.fetchall()
print(f"Found {len(blank_posts)} blank posts")

if blank_posts:
    marias = user_info.get(65, {})
    admin_info = user_info.get(52, {})
    
    prompt = f"""You are generating realistic shift posts for a restaurant staffing marketplace app called Day Shift. Generate a JSON array of shift posting objects. Each object must have: title (string), description (string, 1-2 sentences), pay_rate (string like "$22/hr"), hours (string like "6:00 PM - 11:00 PM"), location (string), cuisine_type (string), event_date (string, YYYY-MM-DD format, dates in July 2026).

For {marias.get('name', 'Marias Kitchen')} (a {marias.get('cuisine_type', 'Mexican/home-style')} restaurant in {marias.get('location', 'Brooklyn')}): generate 13 unique shift posts. Mix of: line cook, prep cook, dishwasher, server shifts. Pay $18-28/hr. Locations around Brooklyn. Variety of hours.

For {admin_info.get('name', 'Day Shift Admin')}: generate 1 "featured opportunity" post highlighting the platform - something like a special event or promotion.

Return ONLY a JSON array, no markdown, no explanation. Array of objects with keys: title, description, pay_rate, hours, location, cuisine_type, event_date."""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    
    content_data = json.loads(text)
    print(f"Generated {len(content_data)} post content objects")

    # Assign content to blank posts
    cur2 = conn.cursor()
    marias_posts = [p for p in blank_posts if p['user_id'] == 65]
    admin_posts = [p for p in blank_posts if p['user_id'] == 52]

    marias_content = [c for c in content_data if 'marias' in str(c.get('cuisine_type','')).lower() or 'brooklyn' in str(c.get('location','')).lower()]
    admin_content = [c for c in content_data if c not in marias_content]

    # Assign Marias content
    for i, post in enumerate(marias_posts):
        if i < len(marias_content):
            c = marias_content[i]
            cur2.execute("""UPDATE videos SET title=%s, description=%s, pay_rate=%s, hours=%s, 
                          location=%s, cuisine_type=%s, event_date=%s WHERE id=%s""",
                       (c['title'], c['description'], c['pay_rate'], c['hours'],
                        c['location'], c['cuisine_type'], c['event_date'], post['id']))
    
    # Assign Admin content
    for i, post in enumerate(admin_posts):
        if i < len(admin_content):
            c = admin_content[i]
            cur2.execute("""UPDATE videos SET title=%s, description=%s, pay_rate=%s, hours=%s,
                          location=%s, cuisine_type=%s, event_date=%s WHERE id=%s""",
                       (c['title'], c['description'], c['pay_rate'], c['hours'],
                        c['location'], c['cuisine_type'], c['event_date'], post['id']))
    
    conn.commit()
    cur2.close()
    print(f"Updated {len(marias_posts) + len(admin_posts)} blank posts with content")
else:
    print("No blank posts to update")

cur.close()

# ── STEP 2: Generate unique post images per user ────────────────────
print("\n=== STEP 2: Generating unique images for users ===")

# Users needing unique images (one per user for their posts)
users_needing_images = [
    {"id": 59, "name": "The Golden Spoon", "role": "employer", "vibe": "upscale fine dining restaurant with gold accents, elegant plating, warm candlelit ambiance"},
    {"id": 60, "name": "Harlem Eats Kitchen", "role": "employer", "vibe": "vibrant soul food kitchen in Harlem, colorful, lively atmosphere, community feel"},
    {"id": 57, "name": "Aiden Chen", "role": "worker", "vibe": "young Asian-American chef with sharp knife skills, modern fusion kitchen, focused expression"},
    {"id": 55, "name": "DeShawn Williams", "role": "worker", "vibe": "confident Black male chef in a professional kitchen, strong presence, grilling or sauteing"},
    {"id": 62, "name": "Brooklyn Bakehouse", "role": "employer", "vibe": "cozy artisan bakery with fresh bread, pastries, warm morning light, rustic wood counters"},
    {"id": 56, "name": "Sofia Rodriguez", "role": "worker", "vibe": "passionate Latina chef plating a colorful dish, fresh ingredients, bright kitchen"},
    {"id": 64, "name": "Tasha Williams", "role": "worker", "vibe": "skilled Black female pastry chef decorating desserts, precise piping, elegant touch"},
    {"id": 53, "name": "Marcus Johnson", "role": "worker", "vibe": "tall Black male chef in a bustling kitchen, leading the line, commanding presence"},
    {"id": 65, "name": "Marias Kitchen", "role": "employer", "vibe": "warm family-run Mexican restaurant, colorful tiles, fresh guacamole being made, cozy"},
    {"id": 63, "name": "Catering Kings NYC", "role": "employer", "vibe": "elegant catering setup with chafing dishes, sophisticated event plating, NYC skyline view"},
    {"id": 52, "name": "Day Shift Admin", "role": "admin", "vibe": "professional restaurant industry networking event, diverse chefs collaborating, modern industrial event space"},
]

generated_images = {}
IMG_DIR = "static/images/generated"
os.makedirs(IMG_DIR, exist_ok=True)

for user in users_needing_images:
    name = user['name']
    vibe = user['vibe']
    role = user['role']
    safe_name = name.lower().replace(" ", "_").replace("'", "")
    filename = f"{safe_name}_post.png"
    filepath = f"{IMG_DIR}/{filename}"
    
    print(f"  Generating post image for {name}...")
    
    prompt = f"""Professional food industry photograph. {vibe}. 
Warm natural lighting, shallow depth of field, photorealistic editorial quality.
Horizontal 16:9 aspect ratio suitable for a mobile feed card.
No text, no watermarks, no logos."""
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()
                image.save(filepath)
                generated_images[user['id']] = f"/{filepath}"
                print(f"    ✓ Saved {filepath}")
                break
        else:
            print(f"    ✗ No image generated for {name}")
            generated_images[user['id']] = None
    except Exception as e:
        print(f"    ✗ Error for {name}: {e}")
        generated_images[user['id']] = None
    
    time.sleep(1)  # Rate limit breathing room

# ── STEP 3: Generate avatar for Catering Kings NYC ──────────────────
print("\n=== STEP 3: Generating avatar for Catering Kings NYC ===")
try:
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents="Professional square logo-style avatar for 'Catering Kings NYC' — elegant catering brand. Crown or elegant icon on dark background. Clean, minimal, professional. 200x200 style. No text.",
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    avatar_path = f"{IMG_DIR}/catering_kings_nyc_avatar.png"
    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            image.save(avatar_path)
            generated_images['avatar_63'] = f"/{avatar_path}"
            print(f"  ✓ Avatar saved: {avatar_path}")
            break
    else:
        print("  ✗ No avatar generated")
        generated_images['avatar_63'] = None
except Exception as e:
    print(f"  ✗ Avatar error: {e}")
    generated_images['avatar_63'] = None

# ── STEP 4: Update DB with new images ───────────────────────────────
print("\n=== STEP 4: Updating database ===")
cur = conn.cursor()

# Map: user_id -> which video IDs get the new image
# For each user, find all their videos that currently have an image URL and update them
for user_id, img_path in generated_images.items():
    if isinstance(user_id, str):
        continue  # Skip avatar entries
    if img_path is None:
        continue
    
    # Update all that user's videos to use the new image
    cur.execute("UPDATE videos SET image_url=%s WHERE user_id=%s AND (image_url IS NOT NULL OR id IN (SELECT id FROM videos WHERE user_id=%s AND image_url IS NULL LIMIT 1))",
               (img_path, user_id, user_id))
    affected = cur.rowcount
    if affected > 0:
        print(f"  Updated {affected} posts for user_id={user_id} -> {img_path}")

# Fix avatar dupe
if generated_images.get('avatar_63'):
    cur.execute("UPDATE users SET avatar_url=%s WHERE id=63", (generated_images['avatar_63'],))
    print(f"  Fixed avatar for Catering Kings NYC (id=63)")

conn.commit()
cur.close()
conn.close()

print("\n=== DONE ===")
print(f"Images saved to {IMG_DIR}/")
print(f"Generated: {len([v for v in generated_images.values() if v])} images")
