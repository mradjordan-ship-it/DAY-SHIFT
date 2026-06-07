"""Seed script — populate Day Shift with 3 months of realistic data."""
import os, sys, uuid, random, time, subprocess, asyncio
from pathlib import Path
from datetime import datetime, timedelta
import urllib.request
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.environ.get("DAYSH1_URL")
UPLOAD_DIR = Path(__file__).parent / "uploads"

# Free stock videos from Pexels (CC0 license, vertical/portrait cooking/kitchen/food)
STOCK_VIDEOS = [
    # cooking, kitchen, food prep — portrait orientation
    "https://videos.pexels.com/video-files/3252005/3252005-sd_360_640_25fps.mp4",  # cooking pan
    "https://videos.pexels.com/video-files/4761433/4761433-sd_360_640_25fps.mp4",  # chef cooking
    "https://videos.pexels.com/video-files/5800785/5800785-sd_360_640_25fps.mp4",  # food plating
    "https://videos.pexels.com/video-files/5960459/5960459-sd_360_640_25fps.mp4",  # kitchen prep
    "https://videos.pexels.com/video-files/4049992/4049992-sd_360_640_24fps.mp4",  # restaurant kitchen
]

# Free stock food images from Unsplash
STOCK_IMAGES = [
    "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&h=800&fit=crop",  # kitchen
    "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=600&h=800&fit=crop",  # chef
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=800&fit=crop",  # food plate
    "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=800&fit=crop",  # restaurant
    "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?w=600&h=800&fit=crop",  # baking
    "https://images.unsplash.com/photo-1551218808-94e220e084d2?w=600&h=800&fit=crop",  # cooking
    "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&h=800&fit=crop",  # food
    "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=600&h=800&fit=crop",  # veggies
]

# Posts data — spread across 3 months
POSTS = [
    # Employer posts (kitchens hiring)
    {"user_id": 59, "type": "employer", "post_type": "video", "title": "Line Cook Wanted — Dinner Service", "description": "Busy Italian kitchen in Midtown looking for an experienced line cook. Must handle high-volume dinner service. Competitive pay, great team.", "category": "general", "cuisine_type": "Italian", "pay_rate": "$22-28/hr", "hours": "Tue-Sun 4pm-12am", "location": "Midtown Manhattan", "aspect_ratio": "9:16"},
    {"user_id": 60, "type": "employer", "post_type": "video", "title": "Prep Cooks Needed ASAP", "description": "Harlem's favorite soul food spot is expanding! Need prep cooks who know their way around a kitchen. Morning shifts available.", "category": "general", "cuisine_type": "Soul Food", "pay_rate": "$18-22/hr", "hours": "Mon-Fri 6am-2pm", "location": "Harlem", "aspect_ratio": "9:16"},
    {"user_id": 61, "type": "employer", "post_type": "image", "title": "Sushi Chef — Full Time", "description": "Upscale Japanese restaurant seeking skilled sushi chef. Minimum 2 years experience required. We train on our specific techniques.", "category": "general", "cuisine_type": "Japanese", "pay_rate": "$25-35/hr", "hours": "Wed-Sun 3pm-11pm", "location": "East Village", "aspect_ratio": "9:16"},
    {"user_id": 62, "type": "employer", "post_type": "image", "title": "Pastry Chef Wanted", "description": "Brooklyn's award-winning bakery is looking for a creative pastry chef. Must have experience with artisan breads and French pastries.", "category": "general", "cuisine_type": "Bakery", "pay_rate": "$24-30/hr", "hours": "Mon-Fri 5am-1pm", "location": "Brooklyn", "aspect_ratio": "9:16"},
    {"user_id": 63, "type": "employer", "post_type": "video", "title": "Catering Event — This Weekend!", "description": "Large catering event in Manhattan this weekend. Need prep cooks, servers, and dishwashers. Great hourly rates, meals provided.", "category": "general", "cuisine_type": "Catering", "pay_rate": "$20-25/hr", "hours": "Sat-Sun 8am-8pm", "location": "Manhattan", "aspect_ratio": "9:16"},
    {"user_id": 65, "type": "employer", "post_type": "image", "title": "Dishwasher — Immediate Start", "description": "Family-owned Latin kitchen looking for reliable dishwasher. Full-time or part-time available. We treat our crew right.", "category": "general", "cuisine_type": "Latin", "pay_rate": "$16-18/hr", "hours": "Flexible", "location": "Washington Heights", "aspect_ratio": "9:16"},
    {"user_id": 59, "type": "employer", "post_type": "text", "title": "Now Hiring: Server/Bartender", "description": "Upscale Italian spot needs experienced server who can also bartend. Wine knowledge a plus. Weekend shifts, great tips.", "category": "general", "cuisine_type": "Italian", "pay_rate": "$15/hr + tips", "hours": "Fri-Sun 5pm-1am", "location": "Midtown Manhattan", "aspect_ratio": "9:16"},
    {"user_id": 60, "type": "employer", "post_type": "text", "title": "Weekend Brunch Cook", "description": "Looking for a cook who kills it at brunch. Eggs benedict, pancakes, the works. Every Saturday and Sunday morning.", "category": "general", "cuisine_type": "American", "pay_rate": "$20/hr", "hours": "Sat-Sun 7am-3pm", "location": "Harlem", "aspect_ratio": "9:16"},
    
    # Employer events
    {"user_id": 59, "type": "employer", "post_type": "text", "title": "Open Kitchen Night", "description": "Come see our kitchen in action! Tour the space, meet the team, and learn about open positions. Free appetizers.", "category": "event", "cuisine_type": "Italian", "pay_rate": "", "hours": "", "location": "Midtown Manhattan", "event_date": "2026-06-20", "event_time": "18:00", "aspect_ratio": "9:16"},
    {"user_id": 61, "type": "employer", "post_type": "text", "title": "Sushi Rolling Workshop", "description": "Free sushi rolling workshop for potential hires. Learn basic techniques and interview on the spot. All skill levels welcome.", "category": "event", "cuisine_type": "Japanese", "pay_rate": "Free", "hours": "", "location": "East Village", "event_date": "2026-06-28", "event_time": "14:00", "aspect_ratio": "9:16"},
    {"user_id": 63, "type": "employer", "post_type": "text", "title": "Catering Job Fair", "description": "We're booking summer events and need crew. Stop by our job fair — interviews on the spot. Bring your resume or just your hustle.", "category": "event", "cuisine_type": "Catering", "pay_rate": "", "hours": "", "location": "Chelsea", "event_date": "2026-07-05", "event_time": "10:00", "aspect_ratio": "9:16"},
    
    # Employer for sale
    {"user_id": 62, "type": "employer", "post_type": "image", "title": "Commercial Mixer — Like New", "description": "KitchenAid commercial 8-quart mixer. Used for 6 months, works perfectly. Upgrading to a larger model.", "category": "sale", "cuisine_type": "Bakery", "pay_rate": "", "hours": "", "location": "Brooklyn", "price": "$450", "aspect_ratio": "9:16"},
    {"user_id": 65, "type": "employer", "post_type": "text", "title": "Restaurant Equipment Sale", "description": "Closing our second location. Everything must go — flat top grill, prep tables, walk-in cooler, smallwares. DM for prices.", "category": "sale", "cuisine_type": "Latin", "pay_rate": "", "hours": "", "location": "Washington Heights", "price": "Various", "aspect_ratio": "9:16"},
    
    # Worker posts
    {"user_id": 53, "type": "worker", "post_type": "video", "title": "5 Years Line Cook Experience", "description": "Experienced line cook available for dinner service. Worked French, Italian, and American cuisine. Fast, clean, and reliable. Looking for full-time in Manhattan.", "category": "general", "cuisine_type": "", "pay_rate": "$22+/hr", "hours": "Evenings preferred", "location": "Manhattan", "aspect_ratio": "9:16"},
    {"user_id": 54, "type": "worker", "post_type": "image", "title": "Pastry & Bread Specialist", "description": "Classically trained pastry chef with 3 years at a Michelin-starred bakery. Specializing in viennoiserie and artisan breads. Available mornings.", "category": "general", "cuisine_type": "French Pastry", "pay_rate": "$25+/hr", "hours": "Mornings", "location": "Brooklyn", "aspect_ratio": "9:16"},
    {"user_id": 55, "type": "worker", "post_type": "video", "title": "Prep & Dish — Ready to Work", "description": "Hard worker, fast learner. 2 years prep and dish experience. Available immediately for any shift. Never late, never call out.", "category": "general", "cuisine_type": "", "pay_rate": "$16+/hr", "hours": "Any shift", "location": "Bronx", "aspect_ratio": "9:16"},
    {"user_id": 56, "type": "worker", "post_type": "image", "title": "Catering & Private Chef", "description": "Private chef and caterer with 7 years experience. Specialize in Caribbean-Latin fusion. Available for events, meal prep, and private dining.", "category": "general", "cuisine_type": "Caribbean-Latin Fusion", "pay_rate": "$35-50/hr", "hours": "Events & weekends", "location": "Queens", "aspect_ratio": "9:16"},
    {"user_id": 57, "type": "worker", "post_type": "text", "title": "Sous Chef Looking for Right Kitchen", "description": "Sous chef with 6 years in NYC restaurants. Managed teams of 8+. Looking for a kitchen that values quality and teamwork. Japanese or French preferred.", "category": "general", "cuisine_type": "Japanese/French", "pay_rate": "$28-35/hr", "hours": "Full-time", "location": "Manhattan", "aspect_ratio": "9:16"},
    {"user_id": 58, "type": "worker", "post_type": "text", "title": "Server / Bartender Available", "description": "Friendly, professional server with 4 years fine dining experience. Wine certification (WSET Level 2). Can also bartend. Weekend availability.", "category": "general", "cuisine_type": "", "pay_rate": "$15/hr + tips", "hours": "Weekends", "location": "Lower East Side", "aspect_ratio": "9:16"},
    {"user_id": 64, "type": "worker", "post_type": "video", "title": "Behind the Scenes — My Kitchen Flow", "description": "Day in the life of a prep cook. Organization, speed, and consistency. That's what I bring to every kitchen I work in.", "category": "general", "cuisine_type": "", "pay_rate": "$18+/hr", "hours": "Mornings", "location": "Harlem", "aspect_ratio": "9:16"},
    
    # More recent posts (last 2 weeks)
    {"user_id": 59, "type": "employer", "post_type": "video", "title": "Summer Menu — Hiring Now", "description": "New summer menu means we need more hands. Line cook and prep positions open. Come cook with the best Italian crew in Midtown.", "category": "general", "cuisine_type": "Italian", "pay_rate": "$22-28/hr", "hours": "Dinner service", "location": "Midtown Manhattan", "aspect_ratio": "9:16"},
    {"user_id": 60, "type": "employer", "post_type": "image", "title": "BBQ Season Is Here!", "description": "Outdoor BBQ catering season is popping. Need grill masters and prep cooks who aren't afraid of the heat. Per diem to start, full-time possible.", "category": "general", "cuisine_type": "BBQ", "pay_rate": "$20-25/hr", "hours": "Weekends", "location": "Harlem", "aspect_ratio": "9:16"},
    {"user_id": 53, "type": "worker", "post_type": "image", "title": "Just Got My Food Handler Cert!", "description": "Fresh food handler certification. Ready to get back in the kitchen. 5 years line cook experience, open to all cuisines.", "category": "general", "cuisine_type": "", "pay_rate": "$20+/hr", "hours": "Any", "location": "Manhattan", "aspect_ratio": "9:16"},
    {"user_id": 61, "type": "employer", "post_type": "text", "title": "Omakase Counter — Server Needed", "description": "Intimate 12-seat omakase counter looking for an attentive server with sake knowledge. One seating per night, high tips.", "category": "general", "cuisine_type": "Japanese", "pay_rate": "$18/hr + tips", "hours": "Wed-Sun 5pm-10pm", "location": "East Village", "aspect_ratio": "9:16"},
    {"user_id": 55, "type": "worker", "post_type": "text", "title": "Moving Up — Ready for Line Cook", "description": "Been doing prep for 2 years and I'm ready for the line. Fast hands, cool under pressure. Give me a shot and I won't let you down.", "category": "general", "cuisine_type": "", "pay_rate": "$18+/hr", "hours": "Any", "location": "Bronx", "aspect_ratio": "9:16"},
    
    # Sponsored post
    {"user_id": 52, "type": "employer", "post_type": "text", "title": "Featured Kitchen: The Golden Spoon", "description": "Southern fusion done right. Currently booking experienced line cooks for dinner service. Apply through the app.", "category": "sponsored", "cuisine_type": "Southern Fusion", "pay_rate": "$22-28/hr", "hours": "Dinner 4pm-12am", "location": "Midtown", "aspect_ratio": "9:16"},
]


def download_file(url, dest, timeout=60):
    """Download a file from URL to dest path."""
    try:
        urllib.request.urlretrieve(url, str(dest))
        return True
    except Exception as e:
        print(f"  Download failed: {e}")
        return False


def transcode(src, dest, ffmpeg_bin):
    """Transcode to H.264 720p MP4."""
    cmd = [
        ffmpeg_bin, "-y", "-i", str(src),
        "-c:v", "libx264", "-crf", "28", "-preset", "fast",
        "-vf", "scale=-2:'min(720,ih)'",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart", "-pix_fmt", "yuv420p",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return proc.returncode == 0


def main():
    import imageio_ffmpeg
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # Check existing post count
    cur.execute("SELECT COUNT(*) as cnt FROM videos")
    existing = cur.fetchone()["cnt"]
    print(f"Existing posts: {existing}")
    
    # Download stock videos
    print("\n--- Downloading stock videos ---")
    video_files = []
    for i, url in enumerate(STOCK_VIDEOS):
        raw = UPLOAD_DIR / f"stock_raw_{i}.mp4"
        final = UPLOAD_DIR / f"stock_{i}.mp4"
        if final.exists():
            print(f"  Video {i}: already exists ({final.stat().st_size/1024/1024:.1f}MB)")
            video_files.append(str(final))
            continue
        print(f"  Video {i}: downloading...")
        if download_file(url, raw):
            size = raw.stat().st_size / 1024 / 1024
            print(f"  Downloaded {size:.1f}MB, transcoding...")
            if transcode(raw, final, ffmpeg_bin):
                raw.unlink(missing_ok=True)
                final_size = final.stat().st_size / 1024 / 1024
                print(f"  Done: {final_size:.1f}MB")
                video_files.append(str(final))
            else:
                print(f"  Transcode failed, using raw file")
                os.rename(str(raw), str(final))
                video_files.append(str(final))
        else:
            print(f"  Skipping video {i}")
    
    # Download stock images
    print("\n--- Downloading stock images ---")
    image_files = []
    for i, url in enumerate(STOCK_IMAGES):
        final = UPLOAD_DIR / f"stock_img_{i}.jpg"
        if final.exists():
            print(f"  Image {i}: already exists")
            image_files.append(str(final))
            continue
        print(f"  Image {i}: downloading...")
        if download_file(url, final):
            print(f"  Done: {final.stat().st_size/1024/1024:.1f}MB")
            image_files.append(str(final))
        else:
            print(f"  Skipping image {i}")
    
    # Seed posts
    print(f"\n--- Seeding {len(POSTS)} posts ---")
    
    # Time range: 90 days ago to now
    now = datetime.now()
    start = now - timedelta(days=90)
    
    # Sort posts randomly across 3 months
    random.seed(42)
    timestamps = sorted([start + timedelta(seconds=random.randint(0, int((now - start).total_seconds()))) for _ in POSTS])
    
    # Assign media to posts
    video_idx = 0
    image_idx = 0
    
    seeded = 0
    for i, post in enumerate(POSTS):
        # Skip if similar post already exists (check by title)
        cur.execute("SELECT id FROM videos WHERE title = %s", (post["title"],))
        if cur.fetchone():
            print(f"  Skipping duplicate: {post['title'][:50]}")
            continue
        
        # Assign media
        video_url = None
        image_url = None
        if post["post_type"] == "video" and video_files:
            # Copy stock video to new UUID filename
            src_file = video_files[video_idx % len(video_files)]
            new_name = f"{uuid.uuid4()}.mp4"
            dest_file = UPLOAD_DIR / new_name
            import shutil
            shutil.copy2(src_file, dest_file)
            video_url = f"/api/media/{new_name}"
            video_idx += 1
        elif post["post_type"] == "image" and image_files:
            src_file = image_files[image_idx % len(image_files)]
            new_name = f"{uuid.uuid4()}.jpg"
            dest_file = UPLOAD_DIR / new_name
            import shutil
            shutil.copy2(src_file, dest_file)
            image_url = f"/api/media/{new_name}"
            image_idx += 1
        
        ts = timestamps[i]
        
        cur.execute("""
            INSERT INTO videos (user_id, video_url, image_url, type, post_type, category, 
                price, event_date, event_time, aspect_ratio, title, description, 
                cuisine_type, pay_rate, hours, location, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            post["user_id"], video_url, image_url, post["type"], post["post_type"],
            post["category"], post.get("price") or None, post.get("event_date") or None,
            post.get("event_time") or None, post["aspect_ratio"], post["title"],
            post["description"], post.get("cuisine_type") or None,
            post.get("pay_rate") or None, post.get("hours") or None,
            post.get("location") or None, ts
        ))
        new_id = cur.fetchone()["id"]
        seeded += 1
        media = "video" if video_url else "image" if image_url else "text"
        print(f"  Created id={new_id} [{media}] by user {post['user_id']}: {post['title'][:50]}")
    
    conn.commit()
    
    # Add some likes
    print("\n--- Adding likes ---")
    cur.execute("SELECT id FROM videos ORDER BY id")
    video_ids = [r["id"] for r in cur.fetchall()]
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r["id"] for r in cur.fetchall()]
    
    like_count = 0
    for vid_id in video_ids:
        # Random subset of users like each video
        likers = random.sample(user_ids, k=random.randint(1, min(8, len(user_ids))))
        for uid in likers:
            try:
                cur.execute("INSERT INTO likes (user_id, video_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (uid, vid_id))
                like_count += cur.rowcount
            except:
                pass
    conn.commit()
    print(f"  Added {like_count} likes")
    
    # Add some bookmarks
    print("\n--- Adding bookmarks ---")
    bm_count = 0
    for vid_id in video_ids:
        bookers = random.sample(user_ids, k=random.randint(0, min(4, len(user_ids))))
        for uid in bookers:
            try:
                cur.execute("INSERT INTO bookmarks (user_id, video_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (uid, vid_id))
                bm_count += cur.rowcount
            except:
                pass
    conn.commit()
    print(f"  Added {bm_count} bookmarks")
    
    # Update video like counts
    cur.execute("UPDATE videos SET likes = (SELECT COUNT(*) FROM likes WHERE video_id = videos.id)")
    conn.commit()
    
    # Add some reviews
    print("\n--- Adding reviews ---")
    review_texts = [
        "Great to work with, very professional.",
        "Showed up on time and crushed it. Would hire again.",
        "Solid cook, fast learner.",
        "Amazing kitchen, well organized and fair pay.",
        "Best prep cook I've ever worked with.",
        "Kitchen was clean and well stocked. Good management.",
        "Reliable and hardworking. Highly recommend.",
        "Great team environment, would love to work here again.",
    ]
    rev_count = 0
    for _ in range(20):
        reviewer = random.choice(user_ids)
        # Get a random user that isn't the reviewer
        others = [u for u in user_ids if u != reviewer]
        if not others:
            continue
        reviewee = random.choice(others)
        try:
            cur.execute("INSERT INTO reviews (reviewer_id, reviewee_id, rating, comment) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (reviewer, reviewee, random.choice([4, 4, 5, 5, 5]), random.choice(review_texts)))
            rev_count += cur.rowcount
        except:
            pass
    conn.commit()
    print(f"  Added {rev_count} reviews")
    
    cur.close()
    conn.close()
    
    print(f"\n✅ Done! Seeded {seeded} posts with media.")


if __name__ == "__main__":
    main()
