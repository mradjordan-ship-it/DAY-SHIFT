# Fix: Volume/Fullscreen Button Overlap & Profile Section Too Large on Laptop

## Context
Two visual issues on desktop (laptop) view in FeedScreen video cards:
1. Volume (mute) button and Maximize (fullscreen) button overlap — they're too close together
2. Profile pic, name, and rating section is too big on laptop (md: breakpoints)

## Issues

### 1. Button Overlap
Current positions (portrait/vertical mode, desktop):
- Mute button: `top-14 left-3 w-8 h-8` 
- Fullscreen button: `top-14 left-14 md:left-16 w-8 h-8`
- Both are on the same row at top-14. Left-3 + 32px (w-8) = left at 35px. Left-16 (64px) — that's only ~29px gap, fine visually.
- BUT on md: the mute is still `left-3` while fullscreen jumps to `left-16`. The mute icon is 14px in w-8 container, fullscreen is 13px in w-8 container. These shouldn't overlap.

Wait — let me re-check. Actually the overlap might be that both buttons use `top-14` and the fullscreen is `left-14 md:left-16` while mute is `left-3`. On desktop the mute button text might render wider... No, both are w-8 fixed-width buttons with fixed-positioned backgrounds. Let me reconsider — the user says they ARE overlapping. Maybe on certain screen widths the positioning causes them to collide. Need to space them further apart on md.

### 2. Profile Section Too Large
Current profile pill on desktop:
- Avatar: `w-7 h-7 md:w-9 md:h-9` → 36px on desktop
- Name: `text-[11px] md:text-sm` → 14px on desktop  
- Star: `size={8} md:w-4 md:h-4` → 16px on desktop
- Rating: `text-[9px] md:text-[11px]` → 11px on desktop

The md:w-9 avatar is large and the star at md:w-4 is also oversized for the compact pill. Needs to be scaled down.

## Scope
- Fix button spacing on desktop (md) so volume + fullscreen don't overlap
- Scale down profile section (avatar, star, text) on desktop to match mobile compactness
- Non-goals: don't change mobile layout

## Implementation Plan

### File: `src/components/FeedScreen.tsx`

**Step 1 — Space out volume and fullscreen buttons**
- Mute button: keep `left-3` on mobile, change to `md:left-3` (stays same)
- Fullscreen button: `left-14` on mobile → `md:left-[4.5rem]` or `md:left-18` on desktop (more spacing)
- Or simply: move fullscreen to `top-14 left-14 md:left-[72px]` (left-3 + 32px + 8px gap + 32px = 75px)
- Alternatively, group them into a single row with flex gap instead of absolute positioning

**Step 2 — Scale down profile section on desktop**
- Avatar: `md:w-9 md:h-9` → `md:w-7 md:h-7` (28px, same as mobile base)
- Name: `md:text-sm` → `md:text-xs` (12px)
- Star: `md:w-4 md:h-4` → `md:w-3 md:h-3` (12px)
- Rating: `md:text-[11px]` → keep or reduce to `md:text-[10px]`
- Pill padding: keep as-is (already using backdrop-blur-sm rounded-full)

## Verification
- Check on mobile viewport — no changes should be visible
- Check on laptop/desktop viewport — buttons have clear gap, profile section is compact
