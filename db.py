"""Database connection and schema management for Day Shift marketplace."""
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt as _bcrypt

DATABASE_URL = os.environ.get("DAYSH1_URL", "")


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DAYSH1_URL environment variable not set")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


@contextmanager
def db_conn():
    """Context manager that guarantees connection cleanup on success or error."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield conn, cur
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'worker',  -- 'worker' | 'employer'
            bio TEXT DEFAULT '',
            avatar_url TEXT DEFAULT '',
            avg_rating NUMERIC(3,2) DEFAULT 0,
            total_shifts INTEGER DEFAULT 0,
            reset_token TEXT,
            reset_token_expires TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Safe column additions if table already exists
        ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token TEXT;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMPTZ;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS is_advertiser BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS advertiser_agreement_accepted BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarded BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS suspension_reason TEXT DEFAULT '';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS location TEXT DEFAULT '';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS cuisine_type TEXT DEFAULT '';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS experience_level TEXT DEFAULT '';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS hours TEXT DEFAULT '';
        ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verify_token TEXT;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS suspension_expires_at TIMESTAMPTZ;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS strike_count INTEGER DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS welcome_boost_available BOOLEAN DEFAULT TRUE;

        CREATE TABLE IF NOT EXISTS strikes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            reason TEXT NOT NULL,
            report_id INTEGER,
            issued_by INTEGER REFERENCES users(id),  -- admin who issued, or NULL for auto
            strike_level INTEGER DEFAULT 1,  -- 1st, 2nd, 3rd strike etc.
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_strikes_user ON strikes(user_id);

        CREATE TABLE IF NOT EXISTS appeals (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'pending',  -- 'pending' | 'approved' | 'denied'
            admin_response TEXT,
            reviewed_by INTEGER REFERENCES users(id),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            reviewed_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS idx_appeals_user ON appeals(user_id);

        CREATE TABLE IF NOT EXISTS content_flags (
            id SERIAL PRIMARY KEY,
            target_type TEXT NOT NULL,  -- 'video' | 'user'
            target_id INTEGER NOT NULL,
            flag_type TEXT NOT NULL,  -- 'keyword' | 'ai_moderation'
            matched_term TEXT,
            auto_resolved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_content_flags_target ON content_flags(target_type, target_id);

        CREATE TABLE IF NOT EXISTS moderation_keywords (
            id SERIAL PRIMARY KEY,
            keyword TEXT NOT NULL UNIQUE,
            severity TEXT DEFAULT 'warn',  -- 'warn' | 'block' | 'flag'
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS videos (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            video_url TEXT,
            image_url TEXT,
            thumbnail_url TEXT DEFAULT '',
            type TEXT NOT NULL,  -- 'worker' | 'employer'
            post_type TEXT DEFAULT 'video',  -- 'video' | 'image' | 'text'
            category TEXT DEFAULT 'general',  -- 'general' | 'sale' | 'event'
            price TEXT DEFAULT '',
            event_date TEXT DEFAULT '',
            event_time TEXT DEFAULT '',
            aspect_ratio TEXT DEFAULT '9:16',  -- '9:16' | '1:1' | '4:5' | '16:9'
            title TEXT,
            description TEXT DEFAULT '',
            cuisine_type TEXT DEFAULT '',
            pay_rate TEXT DEFAULT '',
            hours TEXT DEFAULT '',
            experience_level TEXT DEFAULT '',
            location TEXT DEFAULT '',
            likes INTEGER DEFAULT 0,
            scheduled_at TIMESTAMPTZ DEFAULT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Safe column additions for videos (after table exists)
        ALTER TABLE videos ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'general';
        ALTER TABLE videos ADD COLUMN IF NOT EXISTS price TEXT DEFAULT '';
        ALTER TABLE videos ADD COLUMN IF NOT EXISTS event_date TEXT DEFAULT '';
        ALTER TABLE videos ADD COLUMN IF NOT EXISTS event_time TEXT DEFAULT '';
        ALTER TABLE videos ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ DEFAULT NULL;

        CREATE TABLE IF NOT EXISTS likes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, video_id)
        );

        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            worker_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            employer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            worker_video_id INTEGER REFERENCES videos(id),
            employer_video_id INTEGER REFERENCES videos(id),
            status TEXT DEFAULT 'pending',  -- 'pending' | 'active' | 'completed' | 'cancelled'
            initiated_by INTEGER REFERENCES users(id),
            worker_confirmed BOOLEAN DEFAULT FALSE,
            employer_confirmed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,
            sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,
            reviewer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            reviewee_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            feedback TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(match_id, reviewer_id)
        );

        CREATE TABLE IF NOT EXISTS support_threads (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            subject TEXT DEFAULT '',
            status TEXT DEFAULT 'open',  -- 'open' | 'closed'
            source TEXT DEFAULT 'app',   -- 'app' | 'sponsor'
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS support_messages (
            id SERIAL PRIMARY KEY,
            thread_id INTEGER REFERENCES support_threads(id) ON DELETE CASCADE,
            sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            sender_role TEXT DEFAULT 'user',  -- 'user' | 'admin' | 'auto'
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS sponsor_contacts (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT DEFAULT '',
            organization TEXT DEFAULT '',
            type TEXT DEFAULT 'sponsor',
            message TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS sponsor_replies (
            id SERIAL PRIMARY KEY,
            contact_id INTEGER REFERENCES sponsor_contacts(id) ON DELETE CASCADE,
            admin_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Tips / donations
        CREATE TABLE IF NOT EXISTS tips (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            amount INTEGER NOT NULL,  -- in cents ($1 = 100)
            name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            message TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',  -- 'pending' | 'completed' | 'refunded'
            stripe_session_id TEXT DEFAULT '',
            paypal_order_id TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Bookmarks / saved posts
        CREATE TABLE IF NOT EXISTS bookmarks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, video_id)
        );

        -- User blocks
        CREATE TABLE IF NOT EXISTS user_blocks (
            id SERIAL PRIMARY KEY,
            blocker_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            blocked_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(blocker_id, blocked_id)
        );

        -- Reports
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            reporter_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            target_type TEXT NOT NULL,  -- 'video' | 'user'
            target_id INTEGER NOT NULL,
            reason TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            status TEXT DEFAULT 'open',  -- 'open' | 'resolved' | 'dismissed'
            reviewed_by INTEGER REFERENCES users(id),
            reviewed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        ALTER TABLE reports ADD COLUMN IF NOT EXISTS admin_action TEXT;
        CREATE TABLE IF NOT EXISTS advertiser_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            tier TEXT NOT NULL DEFAULT 'free',  -- 'free' | 'boost' | 'spotlight' | 'premium' | 'business' | 'enterprise'
            start_date TIMESTAMPTZ DEFAULT NOW(),
            end_date TIMESTAMPTZ,
            boosts_used INTEGER DEFAULT 0,
            boosts_remaining INTEGER DEFAULT 0,
            free_boost_used BOOLEAN DEFAULT FALSE,
            payment_method TEXT DEFAULT 'stripe',
            status TEXT DEFAULT 'active',  -- 'active' | 'expired' | 'cancelled' | 'pending' | 'failed'
            stripe_session_id TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        ALTER TABLE advertiser_subscriptions ADD COLUMN IF NOT EXISTS stripe_session_id TEXT DEFAULT '';
        ALTER TABLE advertiser_subscriptions ADD COLUMN IF NOT EXISTS paypal_order_id TEXT DEFAULT '';
        ALTER TABLE advertiser_subscriptions DROP CONSTRAINT IF EXISTS advertiser_subscriptions_user_id_key;

        -- Individual post boosts
        CREATE TABLE IF NOT EXISTS post_boosts (
            id SERIAL PRIMARY KEY,
            video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id),
            tier TEXT NOT NULL,  -- 'boost' | 'spotlight' | 'premium'
            status TEXT DEFAULT 'pending',  -- 'pending' | 'active' | 'expired' | 'rejected'
            start_date TIMESTAMPTZ,
            end_date TIMESTAMPTZ,
            stripe_session_id TEXT,
            stripe_payment_intent_id TEXT,
            paypal_order_id TEXT,
            payment_status TEXT DEFAULT 'unpaid',  -- 'unpaid' | 'paid' | 'failed' | 'refunded'
            admin_approved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Post analytics (daily aggregates)
        CREATE TABLE IF NOT EXISTS post_analytics (
            id SERIAL PRIMARY KEY,
            video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
            date DATE NOT NULL DEFAULT CURRENT_DATE,
            views INTEGER DEFAULT 0,
            profile_clicks INTEGER DEFAULT 0,
            match_requests INTEGER DEFAULT 0,
            UNIQUE(video_id, date)
        );

        -- Migrate post_boosts to Stripe columns if needed
        ALTER TABLE post_boosts ADD COLUMN IF NOT EXISTS stripe_session_id TEXT;
        ALTER TABLE post_boosts ADD COLUMN IF NOT EXISTS stripe_payment_intent_id TEXT;
        ALTER TABLE post_boosts ADD COLUMN IF NOT EXISTS payment_status TEXT DEFAULT 'unpaid';
        ALTER TABLE post_boosts ADD COLUMN IF NOT EXISTS paypal_order_id TEXT;

        -- Migrate tips to PayPal column if needed
        ALTER TABLE tips ADD COLUMN IF NOT EXISTS paypal_order_id TEXT;

        -- Push notification subscriptions
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            endpoint TEXT NOT NULL,
            p256dh TEXT NOT NULL DEFAULT '',
            auth_key TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, endpoint)
        );

        -- PERFORMANCE INDEXES
        CREATE INDEX IF NOT EXISTS idx_videos_type_cat_created ON videos(type, category, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_videos_user_created ON videos(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_videos_category_admin ON videos(category) WHERE category = 'sponsored';
        
        CREATE INDEX IF NOT EXISTS idx_matches_worker_created ON matches(worker_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_matches_employer_created ON matches(employer_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
        
        CREATE INDEX IF NOT EXISTS idx_messages_match_created ON messages(match_id, created_at);
        
        CREATE INDEX IF NOT EXISTS idx_post_boosts_active ON post_boosts(status, end_date) WHERE status = 'active';
        CREATE INDEX IF NOT EXISTS idx_post_analytics_video_date ON post_analytics(video_id, date);
        
        -- Additional performance indexes
        CREATE INDEX IF NOT EXISTS idx_likes_video ON likes(video_id);
        CREATE INDEX IF NOT EXISTS idx_likes_user ON likes(user_id);
        CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id);
        CREATE INDEX IF NOT EXISTS idx_bookmarks_video ON bookmarks(video_id);
        CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
        CREATE INDEX IF NOT EXISTS idx_user_blocks_blocker ON user_blocks(blocker_id);
        CREATE INDEX IF NOT EXISTS idx_user_blocks_blocked ON user_blocks(blocked_id);
        CREATE INDEX IF NOT EXISTS idx_tips_status ON tips(status);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
        CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC);

        -- ── PROMO CODES ──
        CREATE TABLE IF NOT EXISTS promo_codes (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            discount_percent INTEGER DEFAULT 100,   -- 100 = free, 50 = half off, etc.
            boost_tier TEXT DEFAULT '',              -- 'boost' | 'spotlight' | 'premium' — free boost on signup
            boost_days INTEGER DEFAULT 0,            -- how many days the free boost lasts
            max_redemptions INTEGER DEFAULT 0,       -- 0 = unlimited
            redeemed_count INTEGER DEFAULT 0,
            expires_at TIMESTAMPTZ,
            is_active BOOLEAN DEFAULT TRUE,
            source TEXT DEFAULT '',                  -- e.g. 'The Everything Food Podcast'
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS promo_redemptions (
            id SERIAL PRIMARY KEY,
            promo_code_id INTEGER REFERENCES promo_codes(id),
            user_id INTEGER REFERENCES users(id),
            boost_used BOOLEAN DEFAULT FALSE,
            redeemed_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, promo_code_id)           -- one redemption per user per code
        );

        CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);
        CREATE INDEX IF NOT EXISTS idx_promo_redemptions_user ON promo_redemptions(user_id);

        ALTER TABLE promo_redemptions ADD COLUMN IF NOT EXISTS boost_used BOOLEAN DEFAULT FALSE;

        -- ── PERSISTENT MEDIA STORAGE (bytea in Neon) ──
        -- Stores uploaded files in the database so they survive container restarts
        CREATE TABLE IF NOT EXISTS media_files (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL UNIQUE,
            data BYTEA NOT NULL,
            mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
            file_size INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_media_files_filename ON media_files(filename);
    """)

    conn.commit()

    # ── Seed moderation keywords if empty ──
    cur.execute("SELECT COUNT(*) FROM moderation_keywords")
    if cur.fetchone()["count"] == 0:
        keywords = [
            # Severity: block — auto-reject and flag
            (k, "block") for k in [
                "escort", "onlyfans", "nudes", "drug dealer", "buy drugs",
                "kill yourself", "doxx", "child abuse", "pedo",
            ]
        ] + [
            # Severity: flag — create content_flag for admin review
            (k, "flag") for k in [
                "cash only", "under the table", "no taxes", "off the books",
                "fake id", "counterfeit",
            ]
        ] + [
            # Severity: warn — soft warning, don't block
            (k, "warn") for k in [
                "dm me", "text me", "my number", "snapchat", "telegram",
                "cashapp", "cash app", "venmo request", "send money",
            ]
        ]
        for kw, severity in keywords:
            cur.execute(
                "INSERT INTO moderation_keywords (keyword, severity) VALUES (%s, %s) ON CONFLICT (keyword) DO NOTHING",
                (kw, severity),
            )
        conn.commit()

    # ── Seed default admin if missing ──
    # Check for ADMIN_EMAIL and ADMIN_PASSWORD in environment
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@dayshiftnow.me")
    admin_pw = os.environ.get("ADMIN_PASSWORD")
    
    if admin_pw:
        cur.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
        if not cur.fetchone():
            _admin_hash = _bcrypt.hashpw(admin_pw.encode("utf-8")[:72], _bcrypt.gensalt()).decode()
            cur.execute(
                """
                INSERT INTO users (name, email, password_hash, role, is_admin, onboarded)
                VALUES (%s, %s, %s, %s, TRUE, TRUE)
                ON CONFLICT (email) DO NOTHING
                """,
                ("Admin", admin_email, _admin_hash, "admin"),
            )
            conn.commit()
            print("Created default admin user")

    # ── Seed promo codes ──
    promo_codes = [
        {
            "code": "EVERYTHINGFOOD",
            "description": "The Everything Food Podcast — free Spotlight boost on signup",
            "discount_percent": 100,
            "boost_tier": "spotlight",
            "boost_days": 3,
            "source": "The Everything Food Podcast",
        },
    ]
    for pc in promo_codes:
        cur.execute("SELECT id FROM promo_codes WHERE code = %s", (pc["code"],))
        if not cur.fetchone():
            cur.execute(
                """INSERT INTO promo_codes (code, description, discount_percent, boost_tier, boost_days, source)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (pc["code"], pc["description"], pc["discount_percent"], pc["boost_tier"], pc["boost_days"], pc["source"]),
            )
            conn.commit()
            print(f"Seeded promo code: {pc['code']}")


    conn.commit()

    cur.close()
    conn.close()
