# Sponsored Content Monetization — Cash App Flow

## Context
Day Shift has an existing `is_advertiser` flag on users, a basic SponsorScreen (contact/tip form), and sponsored post display (badge + shimmer). Admin can toggle advertiser status. The user wants a full monetization flow: advertisers select a tier, pay via Cash App, admin approves, and the app handles boosting + analytics.

## Scope & Non-Goals
### In scope
- DB tables for subscriptions and post analytics
- Backend routes: tier purchasing, boost management, analytics, admin approval
- Advertiser Boost screen (tier selection, Cash App payment, "I Paid" confirmation)
- Analytics dashboard for advertisers (views, matches, clicks, active boosts)
- Boost logic in feed (prioritize boosted posts)
- Admin panel additions (approve/reject boosts, view analytics)
- Post-level "Boost" button on advertiser's own posts

### Non-goals (defer)
- Automated payment via Stripe/Square
- Push notifications for boost expiration
- Refund flow
- Non-user sponsorship purchases

## Implementation Plan

### Phase 1: Database Schema (`db.py`)
Add three new tables:

```sql
-- Advertiser subscriptions/tiers
CREATE TABLE advertiser_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) UNIQUE,
    tier TEXT NOT NULL DEFAULT 'free',  -- 'free' | 'boost' | 'spotlight' | 'premium'
    start_date TIMESTAMPTZ DEFAULT NOW(),
    end_date TIMESTAMPTZ,  -- NULL = no active subscription
    boosts_used INTEGER DEFAULT 0,
    boosts_remaining INTEGER DEFAULT 0,
    free_boost_used BOOLEAN DEFAULT FALSE,
    payment_method TEXT DEFAULT 'cashapp',
    cash_tag TEXT DEFAULT '',
    status TEXT DEFAULT 'active',  -- 'active' | 'expired' | 'cancelled'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual post boosts
CREATE TABLE post_boosts (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id),
    user_id INTEGER REFERENCES users(id),
    tier TEXT NOT NULL,  -- 'boost' | 'spotlight' | 'premium'
    status TEXT DEFAULT 'pending',  -- 'pending' | 'active' | 'expired' | 'rejected'
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    cashapp_confirmed BOOLEAN DEFAULT FALSE,
    admin_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Post analytics (daily aggregates)
CREATE TABLE post_analytics (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    views INTEGER DEFAULT 0,
    profile_clicks INTEGER DEFAULT 0,
    match_requests INTEGER DEFAULT 0,
    UNIQUE(video_id, date)
);
```

### Phase 2: Backend Routes (`routes.py`)

**Tier/Pricing:**
- `GET /advertiser/tiers` — returns tier definitions (name, price, duration, features, limits)

**Subscription:**
- `GET /advertiser/subscription` — current user's subscription status, boosts remaining, etc.
- `POST /advertiser/subscription/purchase` — create a subscription purchase request (records Cash App intent)

**Boost Posts:**
- `GET /advertiser/boosts` — list user's active/pending boosts
- `POST /advertiser/boosts` — boost a specific post (creates pending boost with tier)
- `POST /advertiser/boosts/{id}/confirm-payment` — advertiser confirms they paid via Cash App
- `DELETE /advertiser/boosts/{id}` — cancel a pending boost

**Analytics:**
- `GET /advertiser/analytics` — aggregated stats (total views, matches, clicks, active boosts)
- `GET /advertiser/analytics/{video_id}` — per-post breakdown
- `POST /advertiser/analytics/view` — track post view (called from feed when card scrolls into view)
- `POST /advertiser/analytics/click` — track profile click from post

**Admin (additions to existing):**
- `GET /admin/boosts` — all pending + active boosts
- `PATCH /admin/boosts/{id}` — approve or reject a boost (sets admin_approved, activates if confirmed payment)

**Feed modification:**
- Update `GET /videos` to sort boosted posts first (post_boosts with status='active' and end_date > NOW())

### Phase 3: Frontend — Advertiser Boost Screen (`src/components/BoostScreen.tsx`)
New screen accessible from profile or post context menu.

**If not registered:** Show tiers publicly with "Sign Up to Boost" CTA
**If registered but not advertiser:** Show tiers with "Contact Day Shift to become an advertiser" CTA
**If advertiser:**
- Current subscription status + boosts remaining
- Tier cards (Boost $25, Spotlight $75, Premium $150)
- On tier select → shows Cash App $Cashtag + amount
- "I've Sent Payment" button → calls confirm-payment API
- Pending boost status (waiting for admin approval)
- List of posts with "Boost" button on each

### Phase 4: Frontend — Analytics Dashboard (`src/components/AnalyticsScreen.tsx`)
New screen for advertisers showing:
- Total views across all posts (last 7/30 days)
- Total profile clicks
- Total match requests from boosted posts
- Active boosts with countdown (days remaining)
- Per-post breakdown table
- Visual chart (recharts bar chart)

### Phase 5: Frontend — Boost Button on Posts
- In PostScreen: "Boost This Post" button (only for advertisers)
- In ProfileScreen: "Boost" badge on each post card
- In FeedScreen: track view analytics via IntersectionObserver (existing pattern)
- Profile click from feed: track analytics click

### Phase 6: Admin Panel Additions (`src/components/AdminScreen.tsx`)
- New "Boosts" tab in admin showing pending boosts
- Approve/Reject buttons per boost
- View analytics for any advertiser

### Phase 7: Feed Boost Logic
- Modify feed query to JOIN post_boosts and sort active boosts to top
- Carousels: inject advertiser's boosted posts into carousel slots
- Boosted posts get pinned position based on tier:
  - Boost: top 3 for 24h
  - Spotlight: carousel + top 5 for 7 days
  - Premium: every carousel section for 14 days

## Files to Modify
| File | Changes |
|---|---|
| `db.py` | 3 new tables |
| `routes.py` | ~12 new routes, modify feed query |
| `src/types.ts` | New types: Boost, Subscription, Analytics |
| `src/App.tsx` | Add boost + analytics screens, update nav |
| `src/components/BoostScreen.tsx` | **New** — tier selection + Cash App flow |
| `src/components/AnalyticsScreen.tsx` | **New** — advertiser analytics dashboard |
| `src/components/FeedScreen.tsx` | Add view tracking, profile click tracking |
| `src/components/PostScreen.tsx` | Add "Boost This Post" button |
| `src/components/ProfileScreen.tsx` | Add boost badges on posts |
| `src/components/AdminScreen.tsx` | Add "Boosts" tab with approve/reject |

## Cash App Flow
1. Advertiser selects tier → app shows $Cashtag + exact amount
2. User opens Cash App, sends payment
3. User taps "I've Sent Payment" in app
4. Boost status → `pending` (cashapp_confirmed=true, admin_approved=false)
5. Admin sees pending boost → taps Approve or Reject
6. On Approve → boost becomes `active`, feed shows boosted post

## Cash App $Cashtag
Currently set to `$InvitoChef` in SponsorScreen.tsx — reuse this same value for boost payments.

## Verification
- Advertiser selects tier → sees Cash App instructions → confirms payment → boost appears in admin pending queue
- Admin approves → post appears boosted in feed with correct tier priority
- Analytics count views as users scroll past boosted posts
- Analytics count profile clicks when user taps advertiser name from boosted post
- Boost expires after tier duration → post returns to normal position
- Free tier users get 1 boost/month tracked correctly
