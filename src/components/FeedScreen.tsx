// FeedScreen.tsx - Verified Clean State
import { useState, useEffect, useRef } from "react";
import type { Video, FeedTab } from "../types";
import { useAuth, useNav } from "../App";
import { Heart, MapPin, DollarSign, Clock, ChefHat, Star, Share2, Volume2, VolumeX, Flag, Trash2, Tag, Search, X, Bookmark, Maximize2, HardHat, Building2, Calendar, Sparkles } from "lucide-react";
import TickerTape from "./TickerTape";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { trackEvent } from "../lib/analytics";
import { cn } from "@/lib/utils";
import { RoleIcon, CategoryIcon } from "./Icons";

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

export default function FeedScreen() {
  const { user, token } = useAuth();
  const { navigate, params: navParams, setNavHidden } = useNav();
  const [videos, setVideos] = useState<Video[]>([]);
  const [injectedCarousels, setInjectedCarousels] = useState<Video[][]>([]);
  const [tab, setTab] = useState<FeedTab>("all");
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

  // Apply ticker nav params once on mount
  useEffect(() => {
    if (navParams?.tickerFilter) {
      const f = navParams.tickerFilter as string;
      if (f === "workers") setTab("workers");
      else if (f === "employers") setTab("employers");
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
        if (tab !== "all") qs.set("type", tab === "workers" ? "worker" : "employer");
        if (searchQuery.trim()) qs.set("q", searchQuery.trim());
        if (filterCategory !== "all") qs.set("category", filterCategory);
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
          const videoList: Video[] = data.videos || data;  // Support both paginated and legacy format
          setVideos(videoList);
          setNextCursor(data.next_cursor || null);
          setHasMore(data.has_more || false);
          
          if (videoList.length > 0) {
            const sponsoredPosts = videoList.filter((v: Video) => v.is_sponsored || v.category === "sponsored");
            const regularPosts = videoList.filter((v: Video) => !v.is_sponsored && v.category !== "sponsored");
            
            const carouselsList: Video[][] = [];
            // Create enough carousels to sprinkle through the feed
            const numCarousels = Math.max(3, Math.ceil(videoList.length / 6));
            for (let i = 0; i < numCarousels; i++) {
              const shuffled = [...regularPosts].sort(() => 0.5 - Math.random());
              const remainingSponsored = sponsoredPosts.slice(i % Math.max(sponsoredPosts.length, 1), (i % Math.max(sponsoredPosts.length, 1)) + 1);
              carouselsList.push([...remainingSponsored, ...shuffled].slice(0, 5));
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
  }, [tab, token, searchQuery, filterCategory]);

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
    if (!user) return;
    const res = await fetch(`/api/videos/${video.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      setVideos((prev) => prev.filter((v) => v.id !== video.id));
      setInjectedCarousels((prev) =>
        prev.map((carousel) => carousel.filter((v) => v.id !== video.id))
      );
    }
  };

  // ── Infinite scroll: load more when sentinel enters viewport ──
  const sentinelRef = useRef<HTMLDivElement>(null);
  const loadMore = async () => {
    if (!hasMore || !nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const qs = new URLSearchParams();
      if (tab !== "all") qs.set("type", tab === "workers" ? "worker" : "employer");
      if (searchQuery.trim()) qs.set("q", searchQuery.trim());
      if (filterCategory !== "all") qs.set("category", filterCategory);
      qs.set("cursor", nextCursor);
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`/api/videos?${qs.toString()}`, { headers });
      if (res.ok) {
        const data = await res.json();
        const newVideos: Video[] = data.videos || [];
        setVideos((prev) => [...prev, ...newVideos]);
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
  }, [hasMore, nextCursor, loadingMore, tab, token, searchQuery, filterCategory]);

  const handleMatch = async (video: Video) => {
    if (!user) { navigate("login"); return; }
    if (!user || user.id === video.user_id) return;

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
        if (data.detail?.includes("already exists")) {
          // Already matched — go to matches screen
          navigate("matches");
        } else if (data.detail) {
          setError(data.detail);
        }
      }
    } catch {}
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
    setFilterCategory("all");
    setBookmarkedOnly(false);
  };

  const hasActiveFilters = searchQuery || filterCategory !== "all" || bookmarkedOnly;

  return (
    <div className="flex flex-col h-full bg-black">
      {/* Tabs — fixed above scroll */}
      <div className="flex-shrink-0 flex gap-0.5 px-3 py-2 bg-background border-b border-border z-20 shadow-sm relative">
        {(["all", "workers", "employers"] as FeedTab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all flex items-center justify-center gap-1
              ${tab === t ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            {t === "workers" ? <><HardHat size={14} /> Crew</> : t === "employers" ? <><Building2 size={14} /> Kitchens</> : "All"}
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex-shrink-0 bg-background border-b border-border z-10 px-3 py-1.5">
        <div className="flex items-center gap-2">
          {/* Search toggle */}
          <button
            onClick={() => setSearchOpen(!searchOpen)}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${searchOpen ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"}`}
          >
            <Search size={15} />
          </button>

          {/* Category filter chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none flex-1">
            {(["all", "general", "sale", "event"] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setFilterCategory(cat)}
                className={`px-2.5 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap transition-colors flex items-center gap-1
                  ${filterCategory === cat ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"}`}
              >
                {cat === "all" ? "All" : cat === "sale" ? <><Tag size={12} /> For Sale</> : cat === "event" ? <><Calendar size={12} /> Events</> : <><Sparkles size={12} /> General</>}
              </button>
            ))}
          </div>

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
        className="flex-1 min-h-0 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-3 px-2 pb-6 pt-3 md:pt-2 items-start"
      >
        {loading ? (
          <div className="flex items-center justify-center h-full col-span-full">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : videos.length === 0 ? (
          <EmptyFeed tab={tab} navigate={navigate} user={user} />
        ) : (
          <>
            {(() => {
              // Build a flat list of feed items: posts, tickers, and carousels interleaved
              const items: { type: "post"; video: Video; idx: number } | { type: "ticker"; idx: number } | { type: "carousel"; carouselIdx: number; idx: number }[] = [];
              let carouselCounter = 0;
              // Random seed based on video IDs so it stays stable across re-renders
              const seed = videos.length > 0 ? videos[0].id : 1;
              
              videos.forEach((video, idx) => {
                items.push({ type: "post", video, idx });
                
                // Inject carousel after 2nd post, then randomly every 4-7 posts
                if (idx === 1) {
                  if (injectedCarousels[0]?.length > 0) {
                    items.push({ type: "carousel", carouselIdx: 0, idx });
                    carouselCounter++;
                  }
                } else if (idx > 1 && (idx + seed) % (4 + (idx % 4)) === 0) {
                  const ci = carouselCounter % injectedCarousels.length;
                  if (injectedCarousels[ci]?.length > 0) {
                    items.push({ type: "carousel", carouselIdx: ci, idx });
                    carouselCounter++;
                  }
                }
                
                // Ticker every N posts
                const shouldShowTicker = (idx + 1) % tickerFrequency === 0;
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
                      />
                    </div>
                  );
                }
                if (item.type === "ticker") {
                  const desktopSpan = "col-span-full";
                  return (
                    <div key={`ticker-${item.idx}`} className={`col-span-full flex items-center py-2 ${desktopSpan}`}>
                      <TickerTape />
                    </div>
                  );
                }
                if (item.type === "carousel") {
                  return (
                    <div key={`carousel-${item.carouselIdx}-${item.idx}`} className="col-span-full pb-2">
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
                <p className="text-muted-foreground text-xs mb-4 max-w-xs">Match with your next shift. Workers and kitchens, one feed.</p>
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
    <div className="relative bg-black overflow-hidden rounded-xl border border-white/5 w-full min-h-[200px] md:min-h-0 aspect-[3/2] md:aspect-video py-1">
      {/* Horizontal Scroll Content */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex gap-2.5 px-3 overflow-x-auto snap-x snap-mandatory scrollbar-none h-full w-full items-center"
      >
        {videos.map((video, idx) => (
          <div key={video.id} className="w-[65%] sm:w-[47%] h-full shrink-0 snap-center relative rounded-xl border border-white/10 overflow-hidden bg-black shadow-lg">
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
  isHorizontal,
  isActiveHorizontal,
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
  isHorizontal?: boolean;
  isActiveHorizontal?: boolean;
}) {
  const { setFullscreenActive } = useNav();
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

  // Aspect ratio style for the media container
  const ar = video.aspect_ratio || "9:16";
  const isDefault = ar === "9:16";

  const sponsored = video.author_is_admin || video.author_is_advertiser;

  return (
    <div
      ref={cardRef}
      className={
        isHorizontal
          ? `relative bg-black w-full h-full overflow-hidden ${sponsored ? "sponsored-shimmer" : ""}`
          : `relative bg-black w-full overflow-hidden rounded-xl ${sponsored ? "sponsored-shimmer border-2 border-amber-400/50" : "border border-white/10"} aspect-[3/4] md:aspect-[4/5]`
      }
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
              <img src={video.author_avatar} alt={video.author_name || ""} className="w-full h-full object-cover" />
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
      ) : video.image_url && video.video_url ? (
        /* Both image and video */
        <>
          <img src={video.image_url} alt={video.title || ""} className="absolute inset-0 w-full h-full object-cover" />
          <video ref={videoRef} src={video.video_url} preload="metadata" className="absolute inset-0 w-full h-full object-cover" loop playsInline webkit-playsinline="true" muted onClick={togglePlay} style={{ opacity: playing ? 1 : 0, transition: 'opacity 0.3s' }} />
        </>
      ) : video.image_url ? (
        /* Image only */
        <img src={video.image_url} alt={video.title || ""} className="absolute inset-0 w-full h-full object-cover" />
      ) : video.video_url ? (
        /* Video only */
        <video ref={videoRef} src={video.video_url} preload="metadata" className="absolute inset-0 w-full h-full object-cover" loop playsInline webkit-playsinline="true" muted onClick={togglePlay} />
      ) : video.description ? (
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
              {video.type === "worker" ? <HardHat size={48} className="text-orange-400" /> : <Building2 size={48} className="text-blue-400" />}
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
      <div className="absolute top-0 left-0 right-0 h-20 bg-gradient-to-b from-black/50 to-transparent pointer-events-none" />
      {/* Bottom gradient — taller to cover info area */}
      <div className="absolute bottom-0 left-0 right-0 h-56 bg-gradient-to-t from-black/80 via-black/40 to-transparent pointer-events-none" />

      {/* Type badges — top left */}
      {!isHorizontal && (
        <div className="absolute z-10 top-3 md:top-4 left-3 md:left-4 flex gap-1.5 md:gap-2 flex-wrap pointer-events-auto">
          {(video.is_sponsored || video.category === "sponsored" || video.author_is_admin) && (
            <Badge className="font-bold border backdrop-blur text-[10px] md:text-xs px-2 md:px-3 py-0.5 md:py-1 border-amber-400/40 bg-amber-500/20 text-amber-300">
              ✦ Sponsored
            </Badge>
          )}
          {!video.author_is_admin && video.category !== "sponsored" && (
            <Badge
              className={cn("font-semibold border-0 backdrop-blur text-[10px] md:text-xs px-2 md:px-3 py-0.5 md:py-1 flex items-center gap-1",
                video.type === "worker"
                  ? "bg-orange-500/20 text-orange-300"
                  : "bg-blue-500/20 text-blue-300"
              )}
            >
              {video.type === "worker" ? <><HardHat size={12} /> Crew</> : <><Building2 size={12} /> Kitchen</>}
            </Badge>
          )}
          {video.category === "sale" && (
            <Badge 
              onClick={(e) => { e.stopPropagation(); setShowDetail(true); }}
              className="font-bold border backdrop-blur text-[10px] md:text-xs px-2 md:px-3 py-0.5 md:py-1 border-emerald-400/40 bg-emerald-500/20 text-emerald-300 cursor-pointer hover:bg-emerald-500/30 transition-colors active:scale-95 flex items-center gap-1">
              <Tag size={12} /> For Sale{video.price ? ` · ${video.price}` : ""}
            </Badge>
          )}
          {video.category === "event" && (
            <Badge 
              onClick={(e) => { e.stopPropagation(); setShowDetail(true); }}
              className="font-bold border backdrop-blur text-[10px] md:text-xs px-2 md:px-3 py-0.5 md:py-1 border-violet-400/40 bg-violet-500/20 text-violet-300 cursor-pointer hover:bg-violet-500/30 transition-colors active:scale-95 flex items-center gap-1">
              <Calendar size={12} /> Event{video.event_date ? ` · ${video.event_date}` : ""}{video.event_time ? ` ${video.event_time}` : ""}
            </Badge>
          )}
          {(() => {
            const age = (Date.now() - new Date(video.created_at).getTime()) / 1000;
            if (age < 900) return (
              <Badge className="font-bold border backdrop-blur text-[10px] md:text-xs px-2 md:px-3 py-0.5 md:py-1 border-lime-400/40 bg-lime-500/20 text-lime-300">
                🔥 FRESH
              </Badge>
            );
            if (age < 3600) return (
              <Badge className="font-semibold border backdrop-blur text-[10px] md:text-xs px-2 md:px-3 py-0.5 md:py-1 border-yellow-400/30 bg-yellow-500/15 text-yellow-300">
                ⚡ NEW
              </Badge>
            );
            return null;
          })()}
        </div>
      )}
      {isHorizontal && (
        <div className="absolute z-10 top-1.5 left-1.5 flex flex-col gap-1 pointer-events-auto">
          {(video.is_sponsored || video.category === "sponsored" || video.author_is_admin) && (
            <Badge className="font-bold border backdrop-blur text-[8px] px-1.5 py-0 border-amber-400/25 bg-amber-500/10 text-amber-300">
              ✦ Sponsored
            </Badge>
          )}
          {!video.author_is_admin && video.category !== "sponsored" && (
            <Badge
              className={cn("font-semibold border-0 backdrop-blur text-[8px] px-1.5 py-0 flex items-center gap-0.5",
                video.type === "worker"
                  ? "bg-orange-500/20 text-orange-300"
                  : "bg-blue-500/20 text-blue-300"
              )}
            >
              {video.type === "worker" ? <><HardHat size={10} /> Crew</> : <><Building2 size={10} /> Kitchen</>}
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
          {(() => {
            const age = (Date.now() - new Date(video.created_at).getTime()) / 1000;
            if (age < 900) return (
              <Badge className="font-bold border backdrop-blur text-[8px] px-1.5 py-0 border-lime-400/25 bg-lime-500/10 text-lime-300">
                🔥 FRESH
              </Badge>
            );
            if (age < 3600) return (
              <Badge className="font-semibold border backdrop-blur text-[8px] px-1.5 py-0 border-yellow-400/20 bg-yellow-500/10 text-yellow-300">
                ⚡ NEW
              </Badge>
            );
            return null;
          })()}
        </div>
      )}

      {/* Volume toggle + Fullscreen expand — left side stacked vertically (hidden on text-only posts and horizontal cards) */}
      {!isHorizontal && (video.video_url || video.image_url) && (
      <div className="absolute left-3 z-10 flex flex-col gap-1.5 top-14">
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
        <button
          onClick={() => setFullscreen(true)}
          className="bg-black/40 backdrop-blur rounded-full flex items-center justify-center w-8 h-8"
        >
          <Maximize2 size={13} className="text-white/80" />
        </button>
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
          <ActionBtn onClick={handleMatch} label="Match" isHorizontal={isHorizontal} isWorker={video.type === "worker"}>
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
          <ActionBtn onClick={() => onDelete(video)} label="Delete" isHorizontal={isHorizontal} isWorker={video.type === "worker"}>
            <Trash2 size={18} className="text-white/60 md:w-4 md:h-4" />
          </ActionBtn>
        ) : currentUser ? (
          <ActionBtn onClick={() => setShowReport(true)} label="Report" isHorizontal={isHorizontal} isWorker={video.type === "worker"}>
            <Flag size={18} className="text-white/60 md:w-4 md:h-4" />
          </ActionBtn>
        ) : null}
      </div>
      )}

      {/* Bottom info — ultra-compact overlay with profile border */}
      <div className={cn("absolute bottom-0 left-0 pointer-events-none", isHorizontal ? "px-2 pb-3" : "right-14 md:right-16 px-3 md:px-4 pb-5 md:pb-4")}>
        {/* Author + title in one line */}
        <div className="flex items-center gap-1 mb-1">
          <button className="flex items-center gap-1 pointer-events-auto shrink-0 bg-black/40 backdrop-blur-sm rounded-full pr-1.5 pl-0.5 py-0.5 border border-white/10" onClick={onProfile}>
            <div className={cn("rounded-full bg-secondary border border-primary overflow-hidden flex-shrink-0", isHorizontal ? "w-5 h-5" : "w-7 h-7 md:w-7 md:h-7")}>
              {video.author_avatar ? (
                <img src={video.author_avatar} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-[8px] font-bold text-primary">
                  {video.author_name?.[0]?.toUpperCase()}
                </div>
              )}
            </div>
            <span className="text-white font-semibold text-[11px] leading-none md:text-xs">{video.author_name}</span>
            <Star size={isHorizontal ? 6 : 8} className="text-primary fill-primary md:w-3 md:h-3" />
            <span className="text-white/60 text-[9px] md:text-[10px]">{video.author_rating ? Number(video.author_rating).toFixed(1) : "New"}</span>
            <span className="text-white/40 text-[9px] ml-1 md:text-[10px]">· {timeAgo(video.created_at)}</span>
          </button>
        </div>

        {!isHorizontal && video.title && (
          <p
            onClick={() => setTitleExpanded((v) => !v)}
            className={cn(
              "text-white font-bold leading-tight mb-1 pointer-events-auto cursor-pointer text-[14px] md:text-lg drop-shadow-md",
              !titleExpanded && "line-clamp-1"
            )}
          >
            {video.title}
          </p>
        )}
        {isHorizontal && video.title && (
          <p className="text-white font-bold leading-tight text-[11px] drop-shadow-md line-clamp-1">
            {video.title}
          </p>
        )}
        {!isHorizontal && !video.title && video.description && (video.video_url || video.image_url) && (
          <p
            onClick={() => setTitleExpanded((v) => !v)}
            className={cn(
              "text-white/90 leading-snug mb-1 pointer-events-auto cursor-pointer text-[12px] md:text-sm drop-shadow-md",
              !titleExpanded && "line-clamp-2"
            )}
          >
            {video.description}
          </p>
        )}

        {/* All meta in one row — hidden in horizontal */}
        {!isHorizontal && (
        <div className="flex flex-wrap gap-1.5 mt-1">
          {video.location && (
            <Chip 
              icon={<MapPin size={10} />} 
              text={video.location} 
              isHorizontal={isHorizontal} 
              onClick={() => {
                const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(video.location || '')}`;
                window.open(url, '_blank', 'noopener,noreferrer');
              }}
            />
          )}
          {video.pay_rate && <Chip icon={<DollarSign size={10} />} text={video.pay_rate} isHorizontal={isHorizontal} />}
          {video.hours && <Chip icon={<Clock size={10} />} text={video.hours} />}
          {video.cuisine_type && <Chip icon={<ChefHat size={10} />} text={video.cuisine_type} />}
        </div>
        )}
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
            {video.video_url ? (
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
                        <img src={video.author_avatar} alt="" className="w-full h-full object-cover" />
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
                      ? <HardHat size={20} className="text-orange-400" />
                      : <Building2 size={20} className="text-blue-400" />}
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
                      <span className="inline-flex items-center gap-1 bg-white/10 backdrop-blur text-white/80 rounded-full px-3 py-1 text-xs">
                        <MapPin size={12} /> {video.location}
                      </span>
                    )}
                    {video.pay_rate && (
                      <span className="inline-flex items-center gap-1 bg-white/10 backdrop-blur text-white/80 rounded-full px-3 py-1 text-xs">
                        <DollarSign size={12} /> {video.pay_rate}
                      </span>
                    )}
                    {video.hours && (
                      <span className="inline-flex items-center gap-1 bg-white/10 backdrop-blur text-white/80 rounded-full px-3 py-1 text-xs">
                        <Clock size={12} /> {video.hours}
                      </span>
                    )}
                    {video.cuisine_type && (
                      <span className="inline-flex items-center gap-1 bg-white/10 backdrop-blur text-white/80 rounded-full px-3 py-1 text-xs">
                        <ChefHat size={12} /> {video.cuisine_type}
                      </span>
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
                      <img src={video.author_avatar} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-xs font-bold text-primary">{video.author_name?.[0]?.toUpperCase()}</div>
                    )}
                  </div>
                  <div className="text-white text-sm font-semibold">{video.author_name}</div>
                  {video.location && (
                    <span className="text-white/50 text-xs ml-auto"><MapPin size={11} className="inline mr-0.5" />{video.location}</span>
                  )}
                </div>
                {video.description && (
                  <p className="text-white/70 text-xs leading-relaxed line-clamp-2 mt-1">{video.description}</p>
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
  children,
  isHorizontal,
  isWorker,
}: {
  onClick: () => void;
  label?: string;
  loading?: boolean;
  children: React.ReactNode;
  isHorizontal?: boolean;
  isWorker?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center gap-0.5"
    >
      <div className={cn(
        "bg-black/30 backdrop-blur rounded-full flex items-center justify-center transition-transform",
        isHorizontal ? "w-6 h-6" : "w-9 h-9 md:w-8 md:h-8",
        loading ? "scale-90" : "active:scale-90"
      )}>
        {children}
      </div>
      {label && <span className="text-white text-[9px] md:text-[10px] font-semibold drop-shadow shadow-black">{label}</span>}
    </button>
  );
}

function EmptyFeed({ tab, navigate, user }: { tab: FeedTab; navigate: (s: import("../types").Screen) => void; user: import("../types").User | null }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 p-6 text-center">
      <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
        {tab === "workers" ? (
          <HardHat className="w-8 h-8 text-primary" />
        ) : tab === "employers" ? (
          <Building2 className="w-8 h-8 text-primary" />
        ) : (
          <ChefHat className="w-8 h-8 text-primary" />
        )}
      </div>
      <h3 className="text-xl text-foreground mb-2" style={{ fontFamily: "'Bebas Neue'" }}>No posts yet</h3>
      <p className="text-muted-foreground text-sm mb-4">
        Be the first to post {tab === "workers" ? "a crew profile" : tab === "employers" ? "a shift listing" : ""}
      </p>
      {user && (
        <button
          onClick={() => navigate("post")}
          className="bg-primary text-primary-foreground px-5 py-2 rounded-xl text-sm font-semibold ember-glow"
        >
          Post Now
        </button>
      )}
    </div>
  );
}
