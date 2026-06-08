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

        -- Advertiser subscriptions / tiers
        CREATE TABLE IF NOT EXISTS advertiser_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) UNIQUE,
            tier TEXT NOT NULL DEFAULT 'free',  -- 'free' | 'boost' | 'spotlight' | 'premium'
            start_date TIMESTAMPTZ DEFAULT NOW(),
            end_date TIMESTAMPTZ,
            boosts_used INTEGER DEFAULT 0,
            boosts_remaining INTEGER DEFAULT 0,
            free_boost_used BOOLEAN DEFAULT FALSE,
            payment_method TEXT DEFAULT 'stripe',
            status TEXT DEFAULT 'active',  -- 'active' | 'expired' | 'cancelled'
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

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
    """)

    conn.commit()

    # ── Seed default admin if missing ──
    # Check for ADMIN_EMAIL and ADMIN_PASSWORD in environment
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@dayshift.app")
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

    cur.close()
    conn.close()
