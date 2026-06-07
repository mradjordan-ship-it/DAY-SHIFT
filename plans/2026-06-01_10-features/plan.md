# Day Shift — 10 Feature Implementation Plan

## Codebase Summary

- **Stack**: React + TypeScript + FastAPI + Neon PostgreSQL + Tailwind + shadcn/ui
- **Container**: `h-screen max-w-[430px] mx-auto` mobile-first
- **Navigation**: Screen-based via `useNav()` / `useAuth()` context hooks
- **DB**: `db.py` has `init_db()` with CREATE TABLE, `routes.py` has 56+ API endpoints
- **Existing tables**: users, videos, likes, matches, messages, reviews, support_threads, support_messages, sponsor_contacts, sponsor_replies, tips, reports (created directly in DB, not in db.py)
- **Existing screens**: Feed, Post, Matches, Chat, Profile, Auth, UserProfile, Review, Admin, Support, Sponsor, Legal
- **Critical constraint**: `verbatimModuleSyntax: true` — type imports must use `import type`

## What Already Exists (don't duplicate)
1. **Direct messaging** — ChatScreen, messages table, `/api/matches/{id}/messages` endpoint. DONE.
2. **Report videos** — FeedScreen has Flag button + report modal, `/api/reports` POST endpoint. DONE.
3. **Admin dashboard** — AdminScreen with stats, users, videos, reports, support, sponsors, tips tabs. DONE.
4. **Reviews** — ReviewScreen, reviews table, `/api/reviews` endpoints. DONE.
5. **Share posts** — FeedScreen has Share2 button with `navigator.share` + clipboard fallback. DONE.

## What's Missing (6 features to build)

### Feature 1: Search & Filters (FeedScreen)
**DB changes**: None (filter on existing columns)
**Backend**: Add query params to `GET /api/videos` — `?q=`, `?location=`, `?cuisine_type=`, `?pay_min=`, `?experience_level=`, `?category=`
**Frontend**: Filter bar above feed tabs. Search input + filter chips.
**Files**: routes.py, FeedScreen.tsx

### Feature 2: Bookmarks / Saved Posts
**DB**: New `bookmarks` table (user_id, video_id, created_at)
**Backend**: `POST /api/bookmarks` (toggle), `GET /api/bookmarks` (list saved)
**Frontend**: Bookmark icon on feed cards. "Saved" tab in FeedScreen or dedicated screen.
**Files**: db.py, routes.py, types.ts, FeedScreen.tsx

### Feature 3: Report/Block Users
**DB**: New `user_blocks` table (blocker_id, blocked_id)
**Backend**: `POST /api/blocks` (block), `GET /api/blocks` (list blocked), `DELETE /api/blocks/{id}`
**Frontend**: "Block user" option on UserProfileScreen and from feed card author tap.
**Files**: db.py, routes.py, UserProfileScreen.tsx, FeedScreen.tsx (minor)

### Feature 4: Push Notifications (PWA)
**Backend**: None needed — purely frontend via service worker.
**Frontend**: Notification permission prompt. Notification badge on bell icon in header. When match received or message received, show browser notification.
**Files**: sw.js (update), App.tsx (notification bell, permission prompt)

### Feature 5: Onboarding Flow
**DB**: Add `onboarded` boolean to users table
**Backend**: `POST /api/auth/onboard` — save role, location, cuisine_type, experience
**Frontend**: New OnboardingScreen — 3 steps: pick role (worker/kitchen), set location, set specialties. Shown after registration, before feed.
**Files**: db.py, routes.py, types.ts, App.tsx, new OnboardingScreen.tsx

### Feature 6: Upload Progress Indicators
**DB/Backend**: None
**Frontend**: Use `XMLHttpRequest` instead of `fetch` for uploads to get progress events. Show progress bar in PostScreen.
**Files**: PostScreen.tsx

## Implementation Order (dependency-safe)

1. **DB Schema** — Add bookmarks, user_blocks tables + onboarded column. Run init_db.
2. **Search & Filters** — Backend query params + frontend filter bar. Zero risk to existing features.
3. **Bookmarks** — New table, endpoints, UI. Isolated feature.
4. **Report/Block Users** — New table, endpoints, UserProfileScreen UI. Isolated.
5. **Upload Progress** — Frontend-only change in PostScreen. Isolated.
6. **Onboarding** — New screen, minor App.tsx routing change. Isolated.
7. **Push Notifications** — Service worker update + App.tsx header change. Low risk.

## Files Modified Per Feature

| Feature | db.py | routes.py | types.ts | App.tsx | Components |
|---------|-------|----------|----------|---------|-------------|
| DB Schema | ✏️ | | | | |
| Search | | ✏️ | | | FeedScreen |
| Bookmarks | ✏️ | ✏️ | ✏️ | | FeedScreen |
| Block Users | ✏️ | ✏️ | | | UserProfile, Feed(minor) |
| Upload Progress | | | | | PostScreen |
| Onboarding | ✏️ | ✏️ | ✏️ | ✏️ | OnboardingScreen(new) |
| Notifications | | | | ✏️ | sw.js |

## Constraint Checklist
- [ ] Never touch `src/components/ui/`
- [ ] Never touch `dist/`
- [ ] `import type` for type-only imports
- [ ] Never rewrite import blocks — append only
- [ ] Don't change existing features' behavior
- [ ] All new routes under `/api/` prefix
