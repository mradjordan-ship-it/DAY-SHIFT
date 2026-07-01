// FeedScreen.tsx - 3-Section Architecture (Feed / Events / For Sale)
import { useState, useEffect, useRef } from "react";
import type { Video, FeedTab, FeedSection } from "../types";
import { useAuth, useNav } from "../App";
import { Heart, MapPin, DollarSign, Clock, ChefHat, Star, Share2, Volume2, VolumeX, Flag, Trash2, Tag, Search, X, Bookmark, Maximize2, Store, Calendar, Sparkles } from "lucide-react";
import TickerTape from "./TickerTape";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { trackEvent } from "../lib/analytics";
import { cn } from "@/lib/utils";
import { RoleIcon, CategoryIcon } from "./Icons";

// ── Avatar error fallback: replace broken img with initials ──
function handleAvatarError(e: React.SyntheticEvent<HTMLImageElement>) {
  const img = e.currentTarget;
  const name = img.alt || "";
  const initial = name[0]?.toUpperCase() || "?";
  img.style.display = "none";
  const fallback = document.createElement("div");
  fallback.className = img.parentElement?.className || "";
  fallback.style.cssText = "width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:rgba(234,88,12,0.15);color:#ea580c;font-weight:700;font-size:1.2rem;";
  fallback.textContent = initial;
  img.parentElement?.replaceChild(fallback, img);
}

// ── Relative time helper ──
function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return `${Math.floor(days / 7)}w ago`;
}

interface FeedScreenProps {
  section?: FeedSection;
}

export default function FeedScreen({ section: propSection }: FeedScreenProps) {
  const { user, token } = useAuth();
  const { navigate, params: navParams, setNavHidden } = useNav();

  // Section: from prop (parent) or navParams (deep link), defaults to "feed"
  const section: FeedSection = propSection || (navParams.section as FeedSection) || "feed";

  const [videos, setVideos] = useState<Video[]>([]);
  const [injectedCarousels, setInjectedCarousels] = useState<Video[][]>([]);
  const [tab, setTab] = useState<FeedTab>(section === "feed" ? "all" : "all");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const [tickerFrequency] = useState(4);

  // Search & filter state
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [bookmarkedOnly, setBookmarkedOnly] = useState(false);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<number>>(new Set());
  const [togglingBookmarkId, setTogglingBookmarkId] = useState<number | null>(null);
  const [matchingVideoId, setMatchingVideoId] = useState<number | null>(null);
  const [deletingVideoId, setDeletingVideoId] = useState<number | null>(null);
  const [reportingVideoId, setReportingVideoId] = useState<number | null>(null);
  const [expandedChips, setExpandedChips] = useState<Set<number>>(new Set());

  // Apply ticker nav params once on mount
  useEffect(() => {
    if (navParams?.tickerFilter) {
      const f = navParams.tickerFilter as string;
      if (f === "workers" || f === "crew") setTab("crew");
      else if (f === "employers" || f === "kitchens") setTab("kitchens");
    }
    if (navParams?.tickerQuery) {
      setSearchQuery(navParams.tickerQuery as string);
      setSearchOpen(true);
    }
  }, []);

  // Scroll direction detection — hide nav on scroll down, show on scroll up (mobile only)
  const lastScrollY = useRef(0);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      // Only auto-hide nav on mobile (below md breakpoint)
      if (window.innerWidth >= 768) return;
      const currentY = el.scrollTop;
      const delta = currentY - lastScrollY.current;
      if (delta > 30) setNavHidden(true);
      else if (delta < -15) setNavHidden(false);
      lastScrollY.current = currentY;
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [setNavHidden]);

  useEffect(() => {
    const fetchVideos = async () => {
      setLoading(true);
      try {
        const qs = new URLSearchParams();

        // Section-aware API mapping:
        // - "feed" section: tab controls type filter (all/crew/kitchens)
        // - "events" section: always category=event
        // - "forsale" section: always category=sale
        if (section === "events") {
          qs.set("category", "event");
        } else if (section === "forsale") {
          qs.set("category", "sale");
        } else {
          // Main feed — tab filters by type
          if (tab === "crew") {
            qs.set("type", "worker");
          } else if (tab === "kitchens") {
            qs.set("type", "employer");
          }
          // tab === "all": no filter, fetches both workers + employers
        }
        if (searchQuery.trim()) qs.set("q", searchQuery.trim());
        const queryStr = qs.toString();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        // Fetch videos + bookmarks in parallel
        const [videosRes, bookmarksRes] = await Promise.all([
          fetch(`/api/videos${queryStr ? `?${queryStr}` : ""}`, { headers }),
          token ? fetch("/api/bookmarks", { headers: { Authorization: `Bearer ${token}` } }).catch(() => null) : Promise.resolve(null),
        ]);

        // Process bookmarks
        if (bookmarksRes?.ok) {
          const list: { video_id: number }[] = await bookmarksRes.json();
          setBookmarkedIds(new Set(list.map((b) => b.video_id)));
        }

        if (videosRes.ok) {
          const data = await videosRes.json();
          const rawList: Video[] = data.videos || data;  // Support both paginated and legacy format
          // Deduplicate by video id
          const seen = new Set<number>();
          const videoList = rawList.filter((v: Video) => {
            if (seen.has(v.id)) return false;
            seen.add(v.id);
            return true;
          });
          setVideos(videoList);
          setNextCursor(data.next_cursor || null);
          setHasMore(data.has_more || false);
          
          if (videoList.length > 0) {
            const sponsoredPosts = videoList.filter((v: Video) => v.is_sponsored || v.category === "sponsored");
            const boostedPosts = videoList.filter((v: Video) => v.boost_tier === "spotlight" || v.boost_tier === "premium");
            const regularPosts = videoList.filter((v: Video) => !v.is_sponsored && v.category !== "sponsored" && !v.boost_tier);

            const carouselsList: Video[][] = [];
            const numCarousels = Math.max(3, Math.ceil(videoList.length / 6));
            for (let i = 0; i < numCarousels; i++) {
              // Priority: spotlight/premium boosted posts first, then fill with random regular posts
              const shuffled = [...regularPosts].sort(() => 0.5 - Math.random());
              const seenAuthors = new Set<number>();
              const uniqueByAuthor: Video[] = [];
              // Add spotlight/premium boosted posts first (deduped by author)
              for (const v of boostedPosts) {
                if (!seenAuthors.has(v.user_id)) {
                  seenAuthors.add(v.user_id);
                  uniqueByAuthor.push(v);
                }
              }
              // Fill remaining slots with random regular posts
              for (const v of shuffled) {
                if (!seenAuthors.has(v.user_id)) {
                  seenAuthors.add(v.user_id);
                  uniqueByAuthor.push(v);
                }
              }
              const remainingSponsored = sponsoredPosts.filter(s => !seenAuthors.has(s.user_id)).slice(0, 1);
              carouselsList.push([...remainingSponsored, ...uniqueByAuthor].slice(0, 5));
            }
            setInjectedCarousels(carouselsList);
          } else {
            setInjectedCarousels([]);
          }
        }
      } finally {
        setLoading(false);
      }
    };
    fetchVideos();
  }, [tab, token, searchQuery, filterCategory, section]);

  const handleLike = async (video: Video) => {
    if (!user) { navigate("login"); return; }
    setTogglingId(video.id);
    try {
      const res = await fetch(`/api/videos/${video.id}/like`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setVideos((prev) =>
          prev.map((v) =>
            v.id === video.id ? { ...v, liked_by_me: data.liked, likes: data.likes } : v
          )
        );
        setInjectedCarousels((prev) =>
          prev.map((carousel) =>
            carousel.map((v) =>
              v.id === video.id ? { ...v, liked_by_me: data.liked, likes: data.likes } : v
            )
          )
        );
        trackEvent("video_liked", { video_id: video.id, video_type: video.type, liked: data.liked });
      }
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async (video: Video) => {
    if (!user || deletingVideoId) return;
    if (!window.confirm("Delete this post? This cannot be undone.")) return;
    setDeletingVideoId(video.id);
    try {
      const res = await fetch(`/api/videos/${video.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setVideos((prev) => prev.filter((v) => v.id !== video.id));
        setInjectedCarousels((prev) =>
          prev.map((carousel) => carousel.filter((v) => v.id !== video.id))
        );
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Failed to delete post");
        setTimeout(() => setError(""), 5000);
      }
    } catch {
      setError("Network error — please try again");
      setTimeout(() => setError(""), 5000);
    } finally {
      setDeletingVideoId(null);
    }
  };

  // ── Infinite scroll: load more when sentinel enters viewport ──
  const sentinelRef = useRef<HTMLDivElement>(null);
  const loadMore = async () => {
    if (!hasMore || !nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const qs = new URLSearchParams();
      // Section-aware API mapping (same as fetchVideos)
      if (section === "events") {
        qs.set("category", "event");
      } else if (section === "forsale") {
        qs.set("category", "sale");
      } else {
        if (tab === "crew") {
          qs.set("type", "worker");
        } else if (tab === "kitchens") {
          qs.set("type", "employer");
        }
      }
      if (searchQuery.trim()) qs.set("q", searchQuery.trim());
      qs.set("cursor", nextCursor);
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`/api/videos?${qs.toString()}`, { headers });
      if (res.ok) {
        const data = await res.json();
        const newVideos: Video[] = data.videos || [];
        setVideos((prev) => {
          const existing = new Set(prev.map((v) => v.id));
          const deduped = newVideos.filter((v) => !existing.has(v.id));
          return [...prev, ...deduped];
        });
        setNextCursor(data.next_cursor || null);
        setHasMore(data.has_more || false);
      }
    } finally {
      setLoadingMore(false);
    }
  };
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore(); },
      { rootMargin: "400px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, nextCursor, loadingMore, tab, token, searchQuery, filterCategory, section]);

  const handleMatch = async (video: Video) => {
    if (!user) { navigate("login"); return; }
    if (user.id === video.user_id) return;
    if (matchingVideoId) return;  // Prevent double-click

    setMatchingVideoId(video.id);
    // Send only the video the user is viewing — the backend figures out the other party
    const payload = video.type === "employer"
      ? { employer_video_id: video.id }      // worker matched on employer's post
      : { worker_video_id: video.id };         // employer matched on worker's post

    try {
      const res = await fetch("/api/matches", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        trackEvent("match_created", { video_id: video.id, video_type: video.type });
        navigate("matches");
      } else {
        const data = await res.json().catch(() => ({}));
        if (data.detail?.includes("already exists") || data.detail) {
          setError(data.detail);
          setTimeout(() => setError(""), 5000);
        }
      }
    } catch {
      setError("Network error — please try again");
      setTimeout(() => setError(""), 5000);
    } finally {
      setMatchingVideoId(null);
    }
  };

  const handleBookmark = async (video: Video) => {
    if (!user || !token) { navigate("login"); return; }
    setTogglingBookmarkId(video.id);
    try {
      const res = await fetch("/api/bookmarks", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: video.id }),
      });
      if (res.ok) {
        const data = await res.json();
        setBookmarkedIds((prev) => {
          const next = new Set(prev);
          if (data.bookmarked) next.add(video.id);
          else next.delete(video.id);
          return next;
        });
      }
    } finally {
      setTogglingBookmarkId(null);
    }
  };

  const clearFilters = () => {
    setSearchQuery("");
    setBookmarkedOnly(false);
  };

  const hasActiveFilters = searchQuery || bookmarkedOnly;

  return (
    <div className="flex flex-col h-full bg-black">
      {/* Unverified email banner */}
      {user && !user.email_verified && (
        <div className="flex-shrink-0 bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 flex items-center justify-between gap-2">
          <p className="text-amber-500 text-xs font-medium">Verify your email to post and match</p>
          <button
            onClick={async () => {
              try {
                const res = await fetch("/api/auth/resend-verification", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ email: user.email }),
                });
                const data = await res.json();
                alert(data.message || "Check your email");
              } catch { alert("Failed to resend verification"); }
            }}
            className="text-amber-500 text-xs font-bold hover:underline whitespace-nowrap"
          >
            Resend
          </button>
        </div>
      )}
      {/* Error / alert banner */}
      {error && (
        <div className="flex-shrink-0 bg-destructive/10 border-b border-destructive/20 px-4 py-2 flex items-center justify-between gap-2">
          <p className="text-destructive text-xs font-medium">{error}</p>
          <button
            onClick={() => setError("")}
            className="text-destructive/60 hover:text-destructive text-xs font-bold"
          >
            Dismiss
          </button>
        </div>
      )}
      {/* Tabs — section-aware */}
      {section === "feed" ? (
        /* Main feed: shows All / Crew / Kitchens tabs (icons only) */
        <>
        <div className="flex-shrink-0 flex gap-0.5 px-3 py-2 bg-background border-b border-border z-20 shadow-sm relative">
          {(["all", "crew", "kitchens"] as FeedTab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2 rounded-lg font-semibold transition-all flex items-center justify-center
                ${tab === t ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              {t === "crew" ? <ChefHat size={18} /> : t === "kitchens" ? <Store size={18} /> : <Sparkles size={18} />}
            </button>
          ))}
        </div>
        </>
      ) : (
        /* Events / For Sale: section label bar instead of tabs */
        <div className="flex-shrink-0 px-3 py-2.5 bg-background border-b border-border z-20 shadow-sm relative flex items-center justify-center">
          {section === "events" ? (
            <>
              <Calendar size={16} className="text-violet-400 mr-1.5" />
              <span className="text-sm font-bold text-foreground tracking-wide">Events</span>
            </>
          ) : (
            <>
              <Tag size={16} className="text-emerald-400 mr-1.5" />
              <span className="text-sm font-bold text-foreground tracking-wide">For Sale</span>
            </>
          )}
        </div>
      )}

      {/* Filter bar — icons only */}
      <div className="flex-shrink-0 bg-background border-b border-border z-10 px-3 py-1.5">
        <div className="flex items-center gap-2">
          {/* Search toggle */}
          <button
            onClick={() => setSearchOpen(!searchOpen)}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${searchOpen ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"}`}
          >
            <Search size={15} />
          </button>

          {/* Spacer to push bookmark/clear to the right */}
          <div className="flex-1" />

          {/* Bookmark toggle */}
          <button
            onClick={() => setBookmarkedOnly(!bookmarkedOnly)}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${bookmarkedOnly ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"}`}
            title="Saved posts"
          >
            <Bookmark size={15} />
          </button>

          {/* Clear all */}
          {hasActiveFilters && (
            <button onClick={clearFilters} className="w-8 h-8 rounded-full flex items-center justify-center bg-secondary text-muted-foreground hover:text-foreground transition-colors" title="Clear filters">
              <X size={15} />
            </button>
          )}
        </div>

        {/* Search input (expandable) */}
        {searchOpen && (
          <div className="mt-1.5">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search posts, locations, cuisines..."
              autoFocus
              className="w-full bg-secondary border border-border rounded-lg px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        )}
      </div>

      {/* Feed — snap scroll on mobile, 2-col grid on desktop */}
      <div
        ref={containerRef}
        className="flex-1 min-h-0 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-3 px-2 pb-6 pt-3 md:pt-2 items-start auto-rows-min"
      >
        {loading ? (
          <div className="flex items-center justify-center h-full col-span-full">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : videos.length === 0 ? (
          <EmptyFeed tab={tab} section={section} navigate={navigate} user={user} />
        ) : (
          <>
            {(() => {
              // Build a flat list of feed items: posts, tickers, and carousels interleaved
              const items: { type: "post"; video: Video; idx: number } | { type: "ticker"; idx: number } | { type: "carousel"; carouselIdx: number; idx: number }[] = [];
              let carouselCounter = 0;
              
              videos.forEach((video, idx) => {
                items.push({ type: "post", video, idx });
                
                // Inject carousel after 3rd post, then every 8 posts
                if (idx === 2 || (idx > 2 && (idx - 2) % 8 === 0)) {
                  if (injectedCarousels[0]?.length > 0) {
                    items.push({ type: "carousel", carouselIdx: 0, idx });
                    carouselCounter++;
                  }
                }
                
                // Ticker every 6 posts
                const shouldShowTicker = (idx + 1) % 6 === 0;
                if (shouldShowTicker) {
                  items.push({ type: "ticker", idx });
                }
              });
              
              return items.map((item, i) => {
                if (item.type === "post") {
                  return (
                    <div key={`post-${item.video.id}`} className="pb-0">
                      <VideoCard
                        video={item.video}
                        currentUser={user}
                        onLike={handleLike}
                        onMatch={handleMatch}
                        onProfile={() => navigate("user-profile", { userId: item.video.user_id })}
                        onDelete={handleDelete}
                        onBookmark={handleBookmark}
                        bookmarkedIds={bookmarkedIds}
                        togglingId={togglingId}
                        togglingBookmarkId={togglingBookmarkId}
                        matchingVideoId={matchingVideoId}
                        deletingVideoId={deletingVideoId}
                        expandedChips={expandedChips}
                        setExpandedChips={setExpandedChips}
                      />
                    </div>
                  );
                }
                if (item.type === "ticker") {
                  return (
                    <div key={`ticker-${item.idx}`} className="col-span-full md:hidden flex items-center py-2">
                      <TickerTape />
                    </div>
                  );
                }
                if (item.type === "carousel") {
                  return (
                    <div key={`carousel-${item.carouselIdx}-${item.idx}`} className="col-span-full md:hidden pb-2">
                      <HorizontalDeckCard
                        videos={injectedCarousels[item.carouselIdx]}
                        currentUser={user}
                        onLike={handleLike}
                        onMatch={handleMatch}
                        onProfile={(userId) => navigate("user-profile", { userId })}
                        onDelete={handleDelete}
                        onBookmark={handleBookmark}
                        bookmarkedIds={bookmarkedIds}
                        togglingId={togglingId}
                        togglingBookmarkId={togglingBookmarkId}
                        matchingVideoId={matchingVideoId}
                        deletingVideoId={deletingVideoId}
                        expandedChips={expandedChips}
                        setExpandedChips={setExpandedChips}
                      />
                    </div>
                  );
                }
                return null;
              });
            })()}
            {/* Login CTA for non-logged-in users */}
            {!user && !loading && videos.length > 0 && (
              <div className="col-span-full flex flex-col items-center justify-center py-10 px-6 text-center snap-start snap-always">
                <div className="w-14 h-14 rounded-full bg-primary/15 flex items-center justify-center mb-3">
                  <ChefHat className="w-7 h-7 text-primary" />
                </div>
                <h3 className="text-lg text-foreground font-bold mb-1" style={{ fontFamily: "'Bebas Neue'" }}>Join Day Shift</h3>
                <p className="text-muted-foreground text-xs mb-4 max-w-xs">Match with your next shift. Workers and kitchens, one feed today!</p>
                <button
                  onClick={() => navigate("login")}
                  className="bg-primary text-primary-foreground px-6 py-2 rounded-xl text-sm font-semibold ember-glow"
                >
                  Sign In
                </button>
              </div>
            )}
            {/* Infinite scroll sentinel */}
            <div ref={sentinelRef} className="col-span-full h-1" />
            {loadingMore && (
              <div className="col-span-full flex justify-center py-4">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function HorizontalDeckCard({
  videos,
  currentUser,
  onLike,
  onMatch,
  onProfile,
  onDelete,
  onBookmark,
  bookmarkedIds,
  togglingId,
  togglingBookmarkId,
  matchingVideoId,
  deletingVideoId,
  expandedChips,
  setExpandedChips,
}: {
  videos: Video[];
  currentUser: import("../types").User | null;
  onLike: (v: Video) => void;
  onMatch: (v: Video) => void;
  onProfile: (userId: number) => void;
  onDelete: (v: Video) => void;
  onBookmark: (v: Video) => void;
  bookmarkedIds: Set<number>;
  togglingId: number | null;
  togglingBookmarkId: number | null;
  matchingVideoId: number | null;
  deletingVideoId: number | null;
  expandedChips: Set<number>;
  setExpandedChips: React.Dispatch<React.SetStateAction<Set<number>>>;
}) {
  const [activeIdx, setActiveIdx] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget;
    const scrollLeft = container.scrollLeft;
    const width = container.clientWidth;
    if (width > 0) {
      // Each card is w-[47%] of the viewport width, scroll snap threshold calculation
      const idx = Math.round(scrollLeft / (width * 0.47));
      if (idx !== activeIdx) {
        setActiveIdx(idx);
      }
    }
  };

  return (
    <div className="relative bg-black overflow-hidden rounded-xl border border-white/5 w-full min-h-[160px] md:min-h-0 aspect-[3/2] md:aspect-[16/9] py-1">
      {/* Horizontal Scroll Content */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex gap-2.5 px-3 overflow-x-auto snap-x snap-mandatory scrollbar-none h-full w-full items-center"
      >
        {videos.map((video, idx) => (
          <div key={`carousel-card-${video.id}`} className="w-[55%] sm:w-[40%] h-full shrink-0 snap-center relative rounded-xl border border-white/10 overflow-hidden bg-black shadow-lg">
            <VideoCard
              video={video}
              currentUser={currentUser}
              onLike={onLike}
              onMatch={onMatch}
              onProfile={() => onProfile(video.user_id)}
              onDelete={onDelete}
              onBookmark={onBookmark}
              bookmarkedIds={bookmarkedIds}
              togglingId={togglingId}
              togglingBookmarkId={togglingBookmarkId}
              matchingVideoId={matchingVideoId}
              deletingVideoId={deletingVideoId}
              expandedChips={expandedChips}
              setExpandedChips={setExpandedChips}
              isHorizontal={true}
              isActiveHorizontal={idx === activeIdx}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function VideoCard({
  video,
  currentUser,
  onLike,
  onMatch,
  onProfile,
  onDelete,
  onBookmark,
  bookmarkedIds,
  togglingId,
  togglingBookmarkId,
  matchingVideoId,
  deletingVideoId,
  isHorizontal,
  isActiveHorizontal,
  expandedChips,
  setExpandedChips,
}: {
  video: Video;
  currentUser: import("../types").User | null;
  onLike: (v: Video) => void;
  onMatch: (v: Video) => void;
  onProfile: () => void;
  onDelete: (v: Video) => void;
  onBookmark: (v: Video) => void;
  bookmarkedIds: Set<number>;
  togglingId: number | null;
  togglingBookmarkId: number | null;
  matchingVideoId: number | null;
  deletingVideoId: number | null;
  isHorizontal?: boolean;
  isActiveHorizontal?: boolean;
  expandedChips: Set<number>;
  setExpandedChips: React.Dispatch<React.SetStateAction<Set<number>>>;
}) {
  const { navigate, setFullscreenActive } = useNav();
  const videoRef = useRef<HTMLVideoElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(true);
  const [videoError, setVideoError] = useState(false);
  const [showMatch, setShowMatch] = useState(false);
  const [shared, setShared] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [reportReason, setReportReason] = useState<string>("other");
  const [reportComment, setReportComment] = useState("");
  const [reportSent, setReportSent] = useState(false);
  const [titleExpanded, setTitleExpanded] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const fsVideoRef = useRef<HTMLVideoElement>(null);
  const [fsPlaying, setFsPlaying] = useState(false);

  // Sync fullscreen state with nav context to hide bottom nav
  useEffect(() => {
    setFullscreenActive(fullscreen);
    return () => setFullscreenActive(false);
  }, [fullscreen]);

  // Autoplay when card scrolls into view, pause when it leaves
  useEffect(() => {
    const card = cardRef.current;
    const vid = videoRef.current;
    if (!card || !vid) return;

    // Reset error state when URL changes
    setVideoError(false);

    // Handle video load errors
    const handleError = () => setVideoError(true);
    vid.addEventListener("error", handleError);

    if (isHorizontal && !isActiveHorizontal) {
      vid.pause();
      setPlaying(false);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.3) {
          if (!isHorizontal || isActiveHorizontal) {
            vid.play().catch(() => {
              // Autoplay may be blocked — show play button
              setPlaying(false);
            });
            setPlaying(true);
          }
        } else {
          vid.pause();
          setPlaying(false);
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(card);
    return () => {
      observer.disconnect();
      vid.removeEventListener("error", handleError);
    };
  }, [video.video_url, isHorizontal, isActiveHorizontal]);

  // Fullscreen video autoplay
  useEffect(() => {
    const vid = fsVideoRef.current;
    if (!vid || !fullscreen) return;
    vid.play().catch(() => {});
    setFsPlaying(true);
    return () => { vid.pause(); };
  }, [fullscreen]);

  const toggleMute = () => {
    if (videoRef.current) videoRef.current.muted = !muted;
    setMuted((m) => !m);
  };

  const isOwnVideo = currentUser && video.user_id === currentUser.id;
  const canMatch = currentUser &&
    !isOwnVideo &&
    ((currentUser.role === "worker" && video.type === "employer") ||
     (currentUser.role === "employer" && video.type === "worker"));

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (playing) { videoRef.current.pause(); setPlaying(false); }
    else { videoRef.current.play().catch(() => {}); setPlaying(true); }
  };

  const handleMatch = () => {
    setShowMatch(true);
    onMatch(video);
    setTimeout(() => setShowMatch(false), 1500);
  };

  const handleShare = async () => {
    const shareText = video.type === "worker"
      ? `${video.author_name} is looking for work on Day Shift — ${video.title}`
      : `Shift available on Day Shift — ${video.title}`;
    const shareUrl = `${window.location.origin}?video=${video.id}`;

    if (navigator.share) {
      try {
        await navigator.share({ title: "Day Shift", text: shareText, url: shareUrl });
      } catch {
        // user cancelled — no-op
      }
    } else {
      await navigator.clipboard.writeText(`${shareText}\n${shareUrl}`).catch(() => {});
      setShared(true);
      setTimeout(() => setShared(false), 2000);
    }
  };

  const handleReport = async () => {
    if (!currentUser) { navigate("login"); return; }
    try {
      const res = await fetch("/api/reports", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          target_type: "video",
          target_id: video.id,
          reason: reportReason,
          comment: reportComment || null,
        }),
      });
      if (res.ok) {
        setReportSent(true);
        trackEvent("video_reported", { video_id: video.id, reason: reportReason });
        setTimeout(() => { setShowReport(false); setReportSent(false); setReportComment(""); }, 1500);
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Failed to submit report");
      }
    } catch {}
  };

  // All feed cards use a uniform portrait ratio so the grid is consistent
  const cardAspect = "3/4";

  const sponsored = video.category === "sponsored";

  return (
    <div
      ref={cardRef}
      className={
        isHorizontal
          ? `relative bg-black w-full h-full overflow-hidden ${sponsored ? "sponsored-shimmer" : ""}`
          : `relative bg-black w-full overflow-hidden rounded-xl ${sponsored ? "sponsored-shimmer border-2 border-amber-400/50" : "border border-white/10"}`
      }
      style={!isHorizontal ? { aspectRatio: cardAspect, minHeight: '12rem' } : undefined}
    >
      {/* Media Content — image, video, or text */}
      {isHorizontal ? (
        /* Horizontal carousel cards: show profile headshot as main visual */
        <div
          className="absolute inset-0 flex flex-col items-center justify-center gap-2 cursor-pointer"
          style={{
            background: video.type === "worker"
              ? "linear-gradient(135deg, #1a0a02 0%, #3d1a06 50%, #1a0a02 100%)"
              : "linear-gradient(135deg, #020d1a 0%, #063055 50%, #020d1a 100%)",
          }}
          onClick={onProfile}
        >
          <div className="w-20 h-20 md:w-24 md:h-24 rounded-full overflow-hidden border-2 border-primary/60 shadow-lg">
            {video.author_avatar ? (
              <img src={video.author_avatar} alt={video.author_name || ""} className="w-full h-full object-cover" onError={handleAvatarError} />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-primary/20 text-primary text-2xl font-bold">
                {video.author_name?.[0]?.toUpperCase() || "?"}
              </div>
            )}
          </div>
          <span className="text-white font-bold text-xs md:text-sm">{video.author_name}</span>
          <span className="flex items-center gap-0.5 text-[10px]">
            <Star size={8} className="text-primary fill-primary" />
            <span className="text-white/60">{video.author_rating ? Number(video.author_rating).toFixed(1) : "New"}</span>
          </span>
        </div>
      ) : video.embed_url ? (
        /* Embedded video (YouTube, Vimeo, TikTok, etc.) */
        <iframe
          src={video.embed_url}
          title={video.title || "Embedded video"}
          className="absolute inset-0 w-full h-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
          loading="lazy"
          style={{ border: 'none' }}
          onClick={(e) => e.stopPropagation()}
        />
      ) : video.image_url && video.video_url ? (
        /* Both image and video */
        <>
          <img src={video.image_url} alt={video.title || ""} className="absolute inset-0 w-full h-full object-cover" />
          {!videoError && <video ref={videoRef} src={video.video_url} preload="metadata" className="absolute inset-0 w-full h-full object-cover" loop playsInline webkit-playsinline="true" muted onClick={togglePlay} style={{ opacity: playing ? 1 : 0, transition: 'opacity 0.3s' }} onError={() => setVideoError(true)} />}
        </>
      ) : video.image_url ? (
        /* Image only */
        <img src={video.image_url} alt={video.title || ""} className="absolute inset-0 w-full h-full object-cover" />
      ) : video.video_url && !videoError ? (
        /* Video only */
        <video ref={videoRef} src={video.video_url} preload="metadata" className="absolute inset-0 w-full h-full object-cover" loop playsInline webkit-playsinline="true" muted onClick={togglePlay} onError={() => setVideoError(true)} />
      ) : (video.video_url && videoError) || video.description ? (
        /* Text only — no media */
        <div
          className="absolute inset-0 flex items-start justify-center px-5 pt-16 pb-20"
          style={{
            background: video.type === "worker"
              ? "linear-gradient(135deg, #1a0a02 0%, #3d1a06 50%, #1a0a02 100%)"
              : "linear-gradient(135deg, #020d1a 0%, #063055 50%, #020d1a 100%)",
          }}
        >
          <div className="text-center max-w-xs">
            <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">{video.description}</p>
          </div>
        </div>
      ) : (
        /* Fallback */
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{
            background: video.type === "worker"
              ? "linear-gradient(135deg, #1a0a02 0%, #3d1a06 50%, #1a0a02 100%)"
              : "linear-gradient(135deg, #020d1a 0%, #063055 50%, #020d1a 100%)",
          }}
        >
          <div className="text-center">
            <div className="mb-2 flex justify-center">
              {video.type === "worker" ? <ChefHat size={48} className="text-orange-400" /> : <Store size={48} className="text-blue-400" />}
            </div>
            <p className="text-white/60 text-sm">No preview</p>
          </div>
        </div>
      )}

      {/* Play/pause tap overlay — only when video exists and not horizontal */}
      {!isHorizontal && !playing && video.video_url && (
        <div
          className="absolute inset-0 flex items-center justify-center pointer-events-auto"
          onClick={togglePlay}
        >
          <div className="w-14 h-14 bg-black/40 backdrop-blur rounded-full flex items-center justify-center">
            {videoError ? (
              <span className="text-white/70 text-[8px] font-bold">ERR</span>
            ) : (
              <div className="w-0 h-0 border-t-[10px] border-b-[10px] border-l-[18px] border-transparent border-l-white ml-1" />
            )}
          </div>
        </div>
      )}

      {/* Top gradient */}
      <div className="absolute top-0 left-0 right-0 h-20 bg-gradient-to-b from-black/70 via-black/40 to-transparent pointer-events-none" />
      {/* Bottom gradient — covers info area only */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black/80 via-black/40 to-transparent pointer-events-none" />

      {/* Top-left: title + expand */}
      {!isHorizontal && (
        <div className="absolute z-10 top-2.5 md:top-3 left-2.5 md:left-3 right-14 md:right-16 flex items-center gap-2 pointer-events-auto">
          {/* Title + expand — single tappable row with gradient fade */}
          {(video.title || video.description || video.video_url || video.image_url || video.embed_url) && (
            <button
              onClick={() => setFullscreen(true)}
              className="flex items-center gap-1.5 min-w-0 flex-1 group"
            >
              <p
                className="text-white font-bold leading-tight text-[13px] md:text-base drop-shadow-md truncate text-left min-w-0"
                title={video.title || (video.description ? "Tap to view post" : "View post")}
              >
                {video.title || (video.description ? video.description.slice(0, 60) : "View post")}
              </p>
              <Maximize2 size={13} className="text-white/50 group-hover:text-white transition-colors flex-shrink-0" />
            </button>
          )}
        </div>
      )}

      {/* Volume toggle only — fullscreen moved into title row above */}
      {!isHorizontal && (video.video_url || video.image_url) && (
      <div className="absolute left-2.5 md:left-3 z-10 flex flex-col gap-1.5 top-[52px] md:top-14">
        {video.video_url && (
          <button
            onClick={toggleMute}
            className="bg-black/40 backdrop-blur rounded-full flex items-center justify-center w-8 h-8"
          >
            {muted
              ? <VolumeX size={14} className="text-white/80" />
              : <Volume2 size={14} className="text-white" />}
          </button>
        )}
      </div>
      )}


      {/* Edit Post action if currentUser is the author */}
      {currentUser && currentUser.id === video.user_id && !isHorizontal && (
        <div className="absolute z-10 top-2.5 right-2.5 pointer-events-auto">
          <Button
            onClick={(e) => {
              e.stopPropagation();
              // To hook into existing ProfileScreen edit modal, we can route to profile
              // The user can open their edit modal from there.
              navigate("profile");
            }}
            size="sm"
            variant="secondary"
            className="bg-black/60 hover:bg-primary text-white border-white/20 h-7 text-xs px-3 rounded-full flex items-center gap-1.5 backdrop-blur-sm transition-colors shadow-md"
          >
            Edit
          </Button>
        </div>
      )}

      {/* Type badges — icon-only circles, bottom-right above action column */}
      {!isHorizontal && (
        <div className="absolute z-10 bottom-16 md:bottom-20 right-12 md:right-14 flex items-center gap-1 pointer-events-auto">
          {(video.is_sponsored || video.category === "sponsored") && (
            <button
              onClick={(e) => { e.stopPropagation(); navigate("boost"); }}
              className="w-6 h-6 rounded-full bg-amber-500/25 backdrop-blur-sm border border-amber-400/40 flex items-center justify-center text-[10px] hover:bg-amber-500/40 active:scale-95 transition-colors"
              title="Sponsored"
            >✦</button>
          )}
          {video.boost_tier === "premium" && (
            <button
              onClick={(e) => { e.stopPropagation(); navigate("boost"); }}
              className="w-6 h-6 rounded-full bg-violet-500/25 backdrop-blur-sm border border-violet-400/40 flex items-center justify-center text-[10px] hover:bg-violet-500/40 active:scale-95 transition-colors"
              title="Featured"
            >👑</button>
          )}
          {video.boost_tier === "spotlight" && (
            <button
              onClick={(e) => { e.stopPropagation(); navigate("boost"); }}
              className="w-6 h-6 rounded-full bg-sky-500/25 backdrop-blur-sm border border-sky-400/40 flex items-center justify-center text-[10px] hover:bg-sky-500/40 active:scale-95 transition-colors"
              title="Spotlight"
            >⭐</button>
          )}
          {video.boost_tier === "boost" && (
            <button
              onClick={(e) => { e.stopPropagation(); navigate("boost"); }}
              className="w-6 h-6 rounded-full bg-emerald-500/25 backdrop-blur-sm border border-emerald-400/40 flex items-center justify-center text-[10px] hover:bg-emerald-500/40 active:scale-95 transition-colors"
              title="Boosted"
            >🔥</button>
          )}
          {video.category !== "sponsored" && video.type !== "admin" && (
            <span
              className={cn("w-6 h-6 rounded-full backdrop-blur-sm border flex items-center justify-center",
                video.type === "worker"
                  ? "bg-orange-500/25 border-orange-400/40"
                  : "bg-blue-500/25 border-blue-400/40"
              )}
              title={video.type === "worker" ? "Crew" : "Kitchen"}
            >
              {video.type === "worker" ? <ChefHat size={11} className="text-orange-300" /> : <Store size={11} className="text-blue-300" />}
            </span>
          )}
          {video.type === "admin" && video.category && (
            <span className="w-6 h-6 rounded-full bg-amber-500/25 backdrop-blur-sm border border-amber-400/40 flex items-center justify-center" title={
              video.category === "event" ? "Event" :
              video.category === "sale" ? "For Sale" :
              video.category === "crew" ? "Crew" :
              video.category === "kitchen" ? "Kitchen" :
              video.category === "general" ? "General" :
              video.category.charAt(0).toUpperCase() + video.category.slice(1)
            }>
              <Sparkles size={11} className="text-amber-300" />
            </span>
          )}
          {video.category === "sale" && (
            <button
              onClick={(e) => { e.stopPropagation(); setShowDetail(true); }}
              className="w-6 h-6 rounded-full bg-emerald-500/25 backdrop-blur-sm border border-emerald-400/40 flex items-center justify-center hover:bg-emerald-500/40 transition-colors active:scale-95"
              title={`For Sale${video.price ? ` · ${video.price}` : ""}`}
            >
              <Tag size={11} className="text-emerald-300" />
            </button>
          )}
          {video.category === "event" && (
            <button
              onClick={(e) => { e.stopPropagation(); setShowDetail(true); }}
              className="w-6 h-6 rounded-full bg-violet-500/25 backdrop-blur-sm border border-violet-400/40 flex items-center justify-center hover:bg-violet-500/40 transition-colors active:scale-95"
              title={`Event${video.event_date ? ` · ${video.event_date}` : ""}${video.event_time ? ` ${video.event_time}` : ""}`}
            >
              <Calendar size={11} className="text-violet-300" />
            </button>
          )}
        </div>
      )}
      {isHorizontal && (
        <div className="absolute z-10 top-1.5 left-1.5 flex flex-col gap-1 pointer-events-auto">
          {(video.is_sponsored || video.category === "sponsored") && (
            <Badge className="font-bold border backdrop-blur text-[8px] px-1.5 py-0 border-amber-400/25 bg-amber-500/10 text-amber-300">
              ✦ Sponsored
            </Badge>
          )}
          {video.boost_tier === "premium" && (
            <Badge className="font-bold border backdrop-blur text-[8px] px-1.5 py-0 border-violet-400/25 bg-violet-500/10 text-violet-300">
              👑 Featured
            </Badge>
          )}
          {video.boost_tier === "spotlight" && (
            <Badge className="font-bold border backdrop-blur text-[8px] px-1.5 py-0 border-sky-400/25 bg-sky-500/10 text-sky-300">
              ⭐ Spotlight
            </Badge>
          )}
          {video.boost_tier === "boost" && (
            <Badge className="font-bold border backdrop-blur text-[8px] px-1.5 py-0 border-emerald-400/25 bg-emerald-500/10 text-emerald-300">
              🔥 Boosted
            </Badge>
          )}
          {video.category !== "sponsored" && video.type !== "admin" && (
            <Badge
              className={cn("font-semibold border-0 backdrop-blur text-[8px] px-1.5 py-0 flex items-center gap-0.5",
                video.type === "worker"
                  ? "bg-orange-500/20 text-orange-300"
                  : "bg-blue-500/20 text-blue-300"
              )}
            >
              {video.type === "worker" ? <><ChefHat size={10} /> Crew</> : <><Store size={10} /> Kitchen</>}
            </Badge>
          )}
          {video.type === "admin" && video.category && (
            <Badge className="font-semibold border-0 backdrop-blur text-[8px] px-1.5 py-0 bg-amber-500/20 text-amber-300 flex items-center gap-0.5">
              <Sparkles size={10} /> {video.category}
            </Badge>
          )}
          {video.category === "sale" && (
            <Badge 
              onClick={(e) => { e.stopPropagation(); setShowDetail(true); }}
              className="font-bold border backdrop-blur text-[8px] px-1.5 py-0 border-emerald-400/25 bg-emerald-500/10 text-emerald-300 cursor-pointer hover:bg-emerald-500/20 transition-colors active:scale-95 flex items-center gap-0.5">
              <Tag size={10} /> For Sale{video.price ? ` · ${video.price}` : ""}
            </Badge>
          )}
          {video.category === "event" && (
            <Badge 
              onClick={(e) => { e.stopPropagation(); setShowDetail(true); }}
              className="font-bold border backdrop-blur text-[8px] px-1.5 py-0 border-violet-400/25 bg-violet-500/10 text-violet-300 cursor-pointer hover:bg-violet-500/20 transition-colors active:scale-95 flex items-center gap-0.5">
              <Calendar size={10} /> Event{video.event_date ? ` · ${video.event_date}` : ""}{video.event_time ? ` ${video.event_time}` : ""}
            </Badge>
          )}
        </div>
      )}

      {/* Right action column — vertically constrained (hidden in horizontal decks) */}
      {!isHorizontal && (
      <div className="absolute right-2 md:right-3 bottom-16 md:bottom-20 flex flex-col items-center justify-end z-10 gap-2 md:gap-1.5">
        <ActionBtn
          onClick={() => onLike(video)}
          loading={togglingId === video.id}
          label={String(video.likes)}
          isHorizontal={isHorizontal}
          isWorker={video.type === "worker"}
        >
          <Heart
            size={18}
            className={`transition-all md:w-4 md:h-4 ${video.liked_by_me ? "fill-primary text-primary scale-110" : "text-white"}`}
          />
        </ActionBtn>

        <ActionBtn
          onClick={() => onBookmark(video)}
          loading={togglingBookmarkId === video.id}
          label="Save"
          isHorizontal={isHorizontal}
          isWorker={video.type === "worker"}
        >
          <Bookmark
            size={16}
            className={`transition-all md:w-4 md:h-4 ${bookmarkedIds.has(video.id) ? "fill-primary text-primary scale-110" : "text-white"}`}
          />
        </ActionBtn>

        {canMatch && !sponsored && (
          <ActionBtn onClick={handleMatch} loading={matchingVideoId === video.id} label="Match" isHorizontal={isHorizontal} isWorker={video.type === "worker"}>
            <span className="text-xl md:text-lg">🤝</span>
          </ActionBtn>
        )}

        <ActionBtn onClick={handleShare} label={shared ? "Copied!" : "Share"} isHorizontal={isHorizontal} isWorker={video.type === "worker"}>
          <Share2
            size={16}
            className={`transition-all md:w-4 md:h-4 ${shared ? "text-primary scale-110" : "text-white"}`}
          />
        </ActionBtn>

        {isOwnVideo ? (
          <ActionBtn onClick={() => onDelete(video)} loading={deletingVideoId === video.id} label="Delete" isHorizontal={isHorizontal} isWorker={video.type === "worker"}>
            <Trash2 size={18} className="text-white/60 md:w-4 md:h-4" />
          </ActionBtn>
        ) : currentUser ? (
          <ActionBtn onClick={() => setShowReport(true)} label="Report" isHorizontal={isHorizontal} isWorker={video.type === "worker"}>
            <Flag size={18} className="text-white/60 md:w-4 md:h-4" />
          </ActionBtn>
        ) : null}
      </div>
      )}

      {/* Bottom info — description + full-width meta chips */}
      <div className={cn("absolute bottom-0 left-0 right-0 pointer-events-none", isHorizontal ? "px-2 pb-2" : "px-3 md:px-4 pb-3 md:pb-4")}>
        {isHorizontal && video.title && (
          <p className="text-white font-bold leading-tight text-[10px] drop-shadow-md line-clamp-1">
            {video.title}
          </p>
        )}
        {isHorizontal && !video.title && video.description && (
          <p className="text-white/90 leading-tight text-[10px] drop-shadow-md line-clamp-2">
            {video.description}
          </p>
        )}
        {/* Description — shown on card for workers only; kitchen posts show it in fullscreen/detail view */}
        {!isHorizontal && video.type === "worker" && !video.title && video.description && (video.video_url || video.image_url) && (
          <p
            onClick={() => setTitleExpanded((v) => !v)}
            className={cn(
              "text-white/90 leading-snug mb-1.5 pointer-events-auto cursor-pointer text-[12px] md:text-sm drop-shadow-md max-w-full",
              !titleExpanded && "line-clamp-1"
            )}
          >
            {titleExpanded ? video.description : (video.description.length > 80 ? video.description.slice(0, 80) + "…" : video.description)}
          </p>
        )}

        {/* Profile pill — above meta chips */}
        {!isHorizontal && (
          <button
            onClick={onProfile}
            className="flex items-center gap-1 bg-black/50 backdrop-blur-sm rounded-full pr-1.5 pl-0.5 py-0.5 border border-white/10 hover:border-white/20 transition-colors mb-2 pointer-events-auto self-start"
          >
            <div className={cn("rounded-full bg-secondary border border-primary overflow-hidden flex-shrink-0", "w-6 h-6 md:w-7 md:h-7")}>
              {video.author_avatar ? (
                <img src={video.author_avatar} alt="" className="w-full h-full object-cover" onError={handleAvatarError} />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-[8px] font-bold text-primary">
                  {video.author_name?.[0]?.toUpperCase()}
                </div>
              )}
            </div>
            <span className="text-white font-semibold text-[11px] leading-none md:text-xs whitespace-nowrap">{video.author_name}</span>
            <Star size={8} className="text-primary fill-primary md:w-3 md:h-3 flex-shrink-0" />
            <span className="text-white/60 text-[9px] md:text-[10px] whitespace-nowrap">{video.author_rating ? Number(video.author_rating).toFixed(1) : "New"}</span>
          </button>
        )}

        {/* Full-width meta chips row — Location + Pay always visible, rest behind +N */}
        {!isHorizontal && (() => {
          const isExpanded = expandedChips.has(video.id);
          const primary = [
            video.location && { icon: <MapPin size={11} />, text: video.location, key: "loc", onClick: () => {
              const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(video.location || '')}`;
              window.open(url, '_blank', 'noopener,noreferrer');
            }},
            video.pay_rate && { icon: <DollarSign size={11} />, text: video.pay_rate, key: "pay" },
          ].filter(Boolean) as { icon: JSX.Element; text: string; key: string; onClick?: () => void }[];
          const secondary = [
            video.hours && { icon: <Clock size={11} />, text: video.hours, key: "hours" },
            video.cuisine_type && { icon: <ChefHat size={11} />, text: video.cuisine_type, key: "cuisine" },
          ].filter(Boolean) as { icon: JSX.Element; text: string; key: string }[];
          const hiddenCount = secondary.length;

          return (
        <div className="flex items-center gap-1.5 flex-wrap pointer-events-auto">
          {primary.map((chip) => (
            <Badge
              key={chip.key}
              variant="chip"
              className={cn("bg-black/40", chip.onClick && "cursor-pointer hover:bg-primary/60")}
              onClick={chip.onClick}
            >
              {chip.icon} {chip.text}
            </Badge>
          ))}
          {hiddenCount > 0 && !isExpanded && (
            <Badge
              variant="chip"
              className="bg-black/40 cursor-pointer hover:bg-white/20"
              onClick={() => setExpandedChips((prev) => new Set(prev).add(video.id))}
            >
              +{hiddenCount}
            </Badge>
          )}
          {isExpanded && secondary.map((chip) => (
            <Badge key={chip.key} variant="chip" className="bg-black/40">
              {chip.icon} {chip.text}
            </Badge>
          ))}
        </div>
          );
        })()}
      </div>

      {/* Detail modal for Events/For Sale */}
      {showDetail && (video.category === "event" || video.category === "sale") && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-30 flex items-center justify-center p-4" onClick={() => setShowDetail(false)}>
          <div className="bg-card border border-border rounded-2xl p-5 w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                {video.category === "sale" ? (
                  <Tag className="w-6 h-6 text-emerald-400" />
                ) : (
                  <Calendar className="w-6 h-6 text-violet-400" />
                )}
                <h3 className="text-foreground font-bold text-lg">
                  {video.category === "sale" ? "For Sale" : "Event"}
                </h3>
              </div>
              <button
                onClick={() => setShowDetail(false)}
                className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>

            {/* Title */}
            {video.title && (
              <p className="text-foreground font-semibold text-base">{video.title}</p>
            )}

            {/* Description */}
            {video.description && (
              <p className="text-muted-foreground text-sm leading-relaxed">{video.description}</p>
            )}

            {/* Sale-specific info */}
            {video.category === "sale" && video.price && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3">
                <p className="text-emerald-300 text-xs uppercase tracking-wider font-medium mb-1">Price</p>
                <p className="text-emerald-400 text-xl font-bold">{video.price}</p>
              </div>
            )}

            {/* Event-specific info */}
            {video.category === "event" && (
              <div className="space-y-2">
                {video.event_date && (
                  <div className="bg-violet-500/10 border border-violet-500/20 rounded-xl p-3">
                    <p className="text-violet-300 text-xs uppercase tracking-wider font-medium mb-1">Date</p>
                    <p className="text-violet-400 text-lg font-bold">{video.event_date}</p>
                  </div>
                )}
                {video.event_time && (
                  <div className="bg-violet-500/10 border border-violet-500/20 rounded-xl p-3">
                    <p className="text-violet-300 text-xs uppercase tracking-wider font-medium mb-1">Time</p>
                    <p className="text-violet-400 text-lg font-bold">{video.event_time}</p>
                  </div>
                )}
                {video.price && (
                  <div className="bg-violet-500/10 border border-violet-500/20 rounded-xl p-3">
                    <p className="text-violet-300 text-xs uppercase tracking-wider font-medium mb-1">Price / Entry</p>
                    <p className="text-violet-400 text-lg font-bold">{video.price}</p>
                  </div>
                )}
              </div>
            )}

            {/* Location */}
            {video.location && (
              <button
                onClick={() => {
                  const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(video.location || '')}`;
                  window.open(url, '_blank', 'noopener,noreferrer');
                }}
                className="w-full flex items-center gap-2 bg-secondary rounded-xl p-3 hover:bg-muted transition-colors"
              >
                <MapPin size={16} className="text-primary" />
                <span className="text-foreground text-sm">{video.location}</span>
                <span className="ml-auto text-xs text-muted-foreground">Open in Maps →</span>
              </button>
            )}

            {/* Author */}
            <div className="flex items-center gap-2 pt-2 border-t border-border">
              <img
                src={video.author_avatar || "/default-avatar.png"}
                alt={video.author_name}
                className="w-8 h-8 rounded-full object-cover"
                onError={handleAvatarError}
              />
              <div className="flex-1 min-w-0">
                <p className="text-foreground text-sm font-medium truncate">{video.author_name}</p>
                <p className="text-muted-foreground text-xs">{video.type === "worker" ? "Crew" : "Kitchen"}</p>
              </div>
              <button
                onClick={() => {
                  setShowDetail(false);
                  onProfile();
                }}
                className="px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-xs font-medium"
              >
                View Profile
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Report modal */}
      {showReport && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-30 flex items-center justify-center p-6" onClick={() => setShowReport(false)}>
          <div className="bg-card border border-border rounded-2xl p-5 w-full max-w-sm space-y-3" onClick={(e) => e.stopPropagation()}>
            {reportSent ? (
              <div className="text-center py-4">
                <p className="text-primary text-lg font-semibold">Report Submitted</p>
                <p className="text-muted-foreground text-sm mt-1">We'll review this content</p>
              </div>
            ) : (
              <>
                <h3 className="text-foreground font-semibold text-sm">Report this {video.post_type === "text" ? "post" : video.post_type === "image" ? "image" : "video"}</h3>
                <p className="text-xs text-muted-foreground">Select a reason for your report:</p>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { value: "harassment", label: "Harassment or Hate Speech" },
                    { value: "spam", label: "Spam or Misleading" },
                    { value: "inappropriate", label: "Inappropriate Content" },
                    { value: "fake", label: "Fake or Fraudulent" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setReportReason(opt.value)}
                      className={`px-3 py-2 rounded-lg text-xs font-medium text-left transition-colors ${reportReason === opt.value ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground hover:bg-muted"}`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                <textarea
                  value={reportComment}
                  onChange={(e) => setReportComment(e.target.value)}
                  placeholder="Additional details (optional)"
                  className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-xs text-foreground resize-none h-16"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowReport(false)}
                    className="flex-1 px-4 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleReport}
                    className="flex-1 px-4 py-2 rounded-lg text-xs font-medium bg-destructive text-destructive-foreground"
                  >
                    Submit Report
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Match flash */}
      {showMatch && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-20">
          <div className="bg-primary/90 text-primary-foreground px-6 py-3 rounded-2xl text-lg font-bold ember-glow animate-bounce">
            🤝 Match Sent!
          </div>
        </div>
      )}

      {/* Fullscreen lightbox */}
      {fullscreen && (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col">
          {/* Top bar */}
          <div className="flex items-center justify-between px-4 py-3 z-10">
            <div className="text-white text-sm font-medium truncate max-w-[60%]">{video.title || video.author_name}</div>
            <button
              onClick={() => setFullscreen(false)}
              className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center"
            >
              <X size={18} className="text-white" />
            </button>
          </div>
          {/* Content area */}
          <div className="flex-1 flex items-center justify-center overflow-y-auto relative">
            {video.embed_url ? (
              /* Embedded video in fullscreen */
              <iframe
                src={video.embed_url}
                title={video.title || "Embedded video"}
                className="w-full h-full max-w-4xl max-h-[80vh] rounded-lg"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                style={{ border: 'none' }}
              />
            ) : video.video_url ? (
              <video
                ref={fsVideoRef}
                src={video.video_url}
                className="max-w-full max-h-full object-contain"
                loop
                playsInline
                autoPlay
                onClick={() => {
                  const vid = fsVideoRef.current;
                  if (!vid) return;
                  if (fsPlaying) { vid.pause(); setFsPlaying(false); }
                  else { vid.play().catch(() => {}); setFsPlaying(true); }
                }}
              />
            ) : video.image_url ? (
              <img src={video.image_url} alt={video.title || ""} className="max-w-full max-h-full object-contain" />
            ) : (
              /* Text-only post — full expanded view */
              <div className="w-full max-w-lg px-6 py-4">
                <div
                  className="rounded-2xl p-6"
                  style={{
                    background: video.type === "worker"
                      ? "linear-gradient(135deg, #1a0a02 0%, #3d1a06 50%, #1a0a02 100%)"
                      : "linear-gradient(135deg, #020d1a 0%, #063055 50%, #020d1a 100%)",
                  }}
                >
                  {/* Author header */}
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-full bg-secondary border-2 border-primary overflow-hidden flex-shrink-0">
                      {video.author_avatar ? (
                        <img src={video.author_avatar} alt="" className="w-full h-full object-cover" onError={handleAvatarError} />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-lg font-bold text-primary">{video.author_name?.[0]?.toUpperCase()}</div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-white font-bold text-base">{video.author_name}</div>
                      <div className="flex items-center gap-2 text-white/50 text-xs">
                        <Star size={10} className="text-primary fill-primary" />
                        <span>{video.author_rating ? Number(video.author_rating).toFixed(1) : "New"}</span>
                        <span>·</span>
                        <span>{timeAgo(video.created_at)}</span>
                      </div>
                    </div>
                    {video.type === "worker"
                      ? <ChefHat size={20} className="text-orange-400" />
                      : <Store size={20} className="text-blue-400" />}
                  </div>

                  {/* Title */}
                  {video.title && (
                    <h2 className="text-white text-xl font-bold mb-3">{video.title}</h2>
                  )}

                  {/* Description */}
                  {video.description && (
                    <p className="text-white/80 text-sm leading-relaxed mb-4 whitespace-pre-wrap">{video.description}</p>
                  )}

                  {/* Meta chips */}
                  <div className="flex flex-wrap gap-2">
                    {video.location && (
                      <Badge variant="chip" className="text-xs px-3 py-1">
                        <MapPin size={12} /> {video.location}
                      </Badge>
                    )}
                    {video.pay_rate && (
                      <Badge variant="chip" className="text-xs px-3 py-1">
                        <DollarSign size={12} /> {video.pay_rate}
                      </Badge>
                    )}
                    {video.hours && (
                      <Badge variant="chip" className="text-xs px-3 py-1">
                        <Clock size={12} /> {video.hours}
                      </Badge>
                    )}
                    {video.cuisine_type && (
                      <Badge variant="chip" className="text-xs px-3 py-1">
                        <ChefHat size={12} /> {video.cuisine_type}
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Bottom overlay for media posts — hide for text-only since it's inline */}
            {(video.video_url || video.image_url) && (
              <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 via-black/40 to-transparent">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-secondary border border-primary overflow-hidden flex-shrink-0">
                    {video.author_avatar ? (
                      <img src={video.author_avatar} alt="" className="w-full h-full object-cover" onError={handleAvatarError} />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-xs font-bold text-primary">{video.author_name?.[0]?.toUpperCase()}</div>
                    )}
                  </div>
                  <div className="text-white text-sm font-semibold">{video.author_name}</div>
                  {video.location && (
                    <Badge variant="chip" className="ml-auto bg-black/40 text-[10px]">
                      <MapPin size={10} /> {video.location}
                    </Badge>
                  )}
                </div>
                {video.description && (
                  <p className="text-white/70 text-xs leading-relaxed mt-1 whitespace-pre-wrap">{video.description}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Chip({ icon, text, isHorizontal, onClick }: { icon: React.ReactNode; text: string; isHorizontal?: boolean; onClick?: () => void }) {
  const baseClasses = cn(
    "inline-flex items-center gap-0.5 bg-black/50 backdrop-blur text-white/90 rounded-full whitespace-nowrap",
    isHorizontal ? "text-[8px] px-1 py-0.5" : "text-[9px] px-1.5 py-0.5 md:text-[11px] md:px-2 md:py-0.5",
    onClick && "pointer-events-auto cursor-pointer hover:bg-primary/50 transition-colors"
  );
  
  if (onClick) {
    return (
      <button onClick={onClick} className={baseClasses}>
        {icon} {text}
      </button>
    );
  }
  
  return (
    <span className={baseClasses}>
      {icon} {text}
    </span>
  );
}

function ActionBtn({
  onClick,
  label,
  loading,
  disabled,
  children,
  isHorizontal,
  isWorker,
}: {
  onClick: () => void;
  label?: string;
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  isHorizontal?: boolean;
  isWorker?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={cn(
        "flex flex-col items-center gap-0.5",
        (disabled || loading) && "opacity-50 pointer-events-none",
      )}
    >
      <div className={cn(
        "bg-black/30 backdrop-blur rounded-full flex items-center justify-center transition-transform",
        isHorizontal ? "w-6 h-6" : "w-9 h-9 md:w-8 md:h-8",
        loading ? "scale-90" : "active:scale-90"
      )}>
        {loading ? (
          <div className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
        ) : children}
      </div>
      {label && <span className="text-white text-[9px] md:text-[10px] font-semibold drop-shadow shadow-black">{loading ? "..." : label}</span>}
    </button>
  );
}

function EmptyFeed({ tab, section, navigate, user }: { tab: FeedTab; section: FeedSection; navigate: (s: import("../types").Screen, p?: Record<string, unknown>) => void; user: import("../types").User | null }) {
  const isEvents = section === "events";
  const isSale = section === "forsale";

  return (
    <div className="flex flex-col items-center justify-center h-64 p-6 text-center">
      <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
        {isEvents ? (
          <Calendar className="w-8 h-8 text-primary" />
        ) : isSale ? (
          <Tag className="w-8 h-8 text-primary" />
        ) : tab === "crew" ? (
          <ChefHat className="w-8 h-8 text-primary" />
        ) : tab === "kitchens" ? (
          <Store className="w-8 h-8 text-primary" />
        ) : (
          <Sparkles className="w-8 h-8 text-primary" />
        )}
      </div>
      <h3 className="text-xl text-foreground mb-2" style={{ fontFamily: "'Bebas Neue'" }}>No posts yet</h3>
      <p className="text-muted-foreground text-sm mb-4">
        {isEvents
          ? "No events posted yet"
          : isSale
            ? "Nothing for sale yet"
            : tab === "crew"
              ? "No crew profiles yet"
              : tab === "kitchens"
                ? "No kitchen openings yet"
                : "No posts in the feed yet"}
      </p>
      {user && (
        <button
          onClick={() => {
            if (isEvents) {
              navigate("post", { presetCategory: "event", returnSection: section });
            } else if (isSale) {
              navigate("post", { presetCategory: "sale", returnSection: section });
            } else {
              navigate("post", { returnSection: section });
            }
          }}
          className="bg-primary text-primary-foreground px-5 py-2 rounded-xl text-sm font-semibold ember-glow"
        >
          Post Now
        </button>
      )}
    </div>
  );
}
