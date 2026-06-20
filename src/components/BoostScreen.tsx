import { useState, useEffect } from "react";
import type { PostBoost, AdvertiserSubscription } from "../types";
import { useAuth, useNav } from "../App";
import { ArrowLeft, CheckCircle2, Clock, XCircle, Zap, Eye, Star, Crown, ExternalLink, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { trackEvent } from "../lib/analytics";

const TIERS = [
  {
    key: "boost",
    name: "Boost",
    price: 25,
    duration: "24 hours",
    icon: Zap,
    color: "from-green-500/20 to-emerald-500/20",
    border: "border-green-500/30",
    features: ["Pin to top of feed", "Sponsored badge", "24-hour visibility"],
  },
  {
    key: "spotlight",
    name: "Spotlight",
    price: 75,
    duration: "7 days",
    icon: Eye,
    color: "from-amber-500/20 to-yellow-500/20",
    border: "border-amber-500/30",
    popular: true,
    features: ["Carousel placement", "7-day boost", "Priority feed position", "Up to 3 posts"],
  },
  {
    key: "premium",
    name: "Premium",
    price: 150,
    duration: "14 days",
    icon: Crown,
    color: "from-purple-500/20 to-violet-500/20",
    border: "border-purple-500/30",
    features: ["Every carousel section", "14-day boost", "Full analytics", "Up to 10 posts", "Featured badge"],
  },
];

export default function BoostScreen() {
  const { user, token } = useAuth();
  const { navigate, params: navParams } = useNav();
  const preselectedVideoId = navParams?.videoId as number | undefined;
  const [boosts, setBoosts] = useState<PostBoost[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTier, setSelectedTier] = useState<string | null>(preselectedVideoId ? "boost" : null);
  const [boostingPostId, setBoostingPostId] = useState<number | null>(preselectedVideoId ?? null);
  const [error, setError] = useState("");
  const [checkingPayment, setCheckingPayment] = useState(false);
  const [promoRedemption, setPromoRedemption] = useState<{ code: string; boost_tier: string; boost_days: number; source: string; boost_used: boolean } | null>(null);
  const [freeBoostLoading, setFreeBoostLoading] = useState(false);

  // Check for Stripe redirect success
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const success = params.get("success");
    const sessionId = params.get("session_id");

    if (success && sessionId && token) {
      setCheckingPayment(true);
      // Clear URL params
      window.history.replaceState({}, "", window.location.pathname);

      // Poll for payment confirmation (webhook may take a few seconds)
      const checkPayment = async () => {
        for (let i = 0; i < 10; i++) {
          await new Promise((r) => setTimeout(r, 2000));
          const res = await fetch("/api/advertiser/boosts", {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.ok) {
            const data = await res.json();
            const paid = data.find((b: PostBoost) => b.stripe_session_id === sessionId && b.payment_status === "paid");
            if (paid) {
              setBoosts(data);
              setCheckingPayment(false);
              return;
            }
          }
        }
        setCheckingPayment(false);
      };
      checkPayment();
    }
  }, [token]);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    const loadData = async () => {
      try {
        const boostRes = await fetch("/api/advertiser/boosts", { headers: { Authorization: `Bearer ${token}` } });
        if (boostRes.ok) setBoosts(await boostRes.json());
        // Check for promo redemption
        const promoRes = await fetch("/api/promo/my-redemption", { headers: { Authorization: `Bearer ${token}` } });
        if (promoRes.ok) {
          const promoData = await promoRes.json();
          if (promoData.redeemed && !promoData.boost_used && promoData.boost_tier) {
            setPromoRedemption(promoData);
          }
        }
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [token]);

  const handleBoost = async (postId: number, tier: string) => {
    if (!token) return;
    setBoostingPostId(postId);
    setError("");
    try {
      if (user?.is_admin) {
        // Admin: free boost, no Stripe
        const res = await fetch("/api/admin/boosts", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ video_id: postId, tier }),
        });
        if (res.ok) {
          trackEvent("boost_created", { video_id: postId, tier });
          loadData(); // refresh list
        } else {
          const data = await res.json().catch(() => ({}));
          setError(data.detail || "Failed to create boost");
        }
      } else {
        const res = await fetch("/api/advertiser/boosts", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ video_id: postId, tier }),
        });
        if (res.ok) {
          const data = await res.json();
          trackEvent("boost_created", { video_id: postId, tier });
          window.location.href = data.stripe_checkout_url;
        } else {
          const data = await res.json().catch(() => ({}));
          setError(data.detail || "Failed to create boost");
        }
      }
    } finally {
      setBoostingPostId(null);
    }
  };

  const handleCancelBoost = async (boostId: number) => {
    if (!token) return;
    await fetch(`/api/advertiser/boosts/${boostId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    setBoosts((prev) => prev.filter((b) => b.id !== boostId));
  };

  const handleFreeBoost = async (postId: number) => {
    if (!token) return;
    setFreeBoostLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/advertiser/free-boost/${postId}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        trackEvent("free_promo_boost", { video_id: postId, source: promoRedemption?.source });
        setPromoRedemption(null);
        // Refresh boosts
        const boostRes = await fetch("/api/advertiser/boosts", { headers: { Authorization: `Bearer ${token}` } });
        if (boostRes.ok) setBoosts(await boostRes.json());
      } else {
        setError(data.detail || "Failed to apply free boost");
      }
    } finally {
      setFreeBoostLoading(false);
    }
  };

  // Not logged in — show public tiers
  if (!user) {
    return (
      <div className="h-full bg-black overflow-y-auto">
        <div className="p-4">
          <button onClick={() => navigate("feed")} className="flex items-center gap-2 text-muted-foreground mb-4">
            <ArrowLeft size={16} /> Back
          </button>
          <h1 className="text-2xl text-white mb-1" style={{ fontFamily: "'Bebas Neue'" }}>Boost Your Posts</h1>
          <p className="text-white/60 text-sm mb-6">Get more visibility on Day Shift</p>
          <div className="space-y-3">
            {TIERS.map((tier) => (
              <div key={tier.key} className={`rounded-xl border p-4 bg-gradient-to-r ${tier.color} ${tier.border}`}>
                <div className="flex items-center gap-2 mb-2">
                  <tier.icon size={18} className="text-white" />
                  <span className="text-white font-bold">{tier.name}</span>
                  {tier.popular && <Badge className="text-[9px] bg-amber-500/30 text-amber-300 border-0 ml-auto">POPULAR</Badge>}
                </div>
                <p className="text-white text-lg font-bold mb-1">${tier.price}</p>
                <p className="text-white/50 text-xs mb-2">{tier.duration}</p>
                <ul className="space-y-1">
                  {tier.features.map((f) => (
                    <li key={f} className="text-white/70 text-xs flex items-center gap-1.5">
                      <CheckCircle2 size={12} className="text-green-400 flex-shrink-0" /> {f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <button
            onClick={() => navigate("register")}
            className="w-full mt-6 py-3 bg-primary text-primary-foreground rounded-xl font-bold ember-glow text-sm"
          >
            Sign Up to Boost
          </button>
        </div>
      </div>
    );
  }

  // Main view (any logged-in user can boost)
  if (checkingPayment) {
    return (
      <div className="h-full bg-black overflow-y-auto">
        <div className="p-4 flex flex-col items-center justify-center min-h-[60vh] text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
          <h2 className="text-xl text-white font-bold mb-2">Confirming Payment...</h2>
          <p className="text-white/60 text-sm">Please wait while we verify your payment.</p>
        </div>
      </div>
    );
  }

  // Main advertiser view
  const unpaidBoosts = boosts.filter((b) => b.status === "pending" && b.payment_status !== "paid");
  const activeBoosts = boosts.filter((b) => b.status === "active");

  return (
    <div className="h-full bg-black overflow-y-auto">
      <div className="p-4">
        <button onClick={() => navigate("profile")} className="flex items-center gap-2 text-muted-foreground mb-4">
          <ArrowLeft size={16} /> Back
        </button>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl text-white" style={{ fontFamily: "'Bebas Neue'" }}>Boost Your Posts</h1>
            <p className="text-white/50 text-xs">Get more visibility on Day Shift</p>
          </div>
          <button
            onClick={() => navigate("analytics")}
            className="px-3 py-1.5 bg-white/10 text-white rounded-lg text-xs font-medium flex items-center gap-1"
          >
            <Eye size={12} /> Analytics
          </button>
        </div>

        {/* Unpaid boosts */}
        {unpaidBoosts.length > 0 && (
          <div className="mb-4 space-y-2">
            <p className="text-white/50 text-xs font-semibold uppercase tracking-wider">Payment Required</p>
            {unpaidBoosts.map((b) => {
              const tier = TIERS.find((t) => t.key === b.tier);
              return (
                <div key={b.id} className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 flex items-center gap-3">
                  <div className="flex-1">
                    <p className="text-white text-sm font-semibold">{tier?.name}</p>
                    <p className="text-white/50 text-xs">{b.video_title || "Post"}</p>
                  </div>
                  <span className="text-white font-bold">${tier?.price}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Active boosts */}
        {activeBoosts.length > 0 && (
          <div className="mb-4 space-y-2">
            <p className="text-white/50 text-xs font-semibold uppercase tracking-wider">Active Boosts</p>
            {activeBoosts.map((b) => (
              <div key={b.id} className="bg-green-500/10 border border-green-500/20 rounded-xl p-3 flex items-center gap-3">
                <CheckCircle2 size={16} className="text-green-400 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-white text-sm font-semibold">{TIERS.find((t) => t.key === b.tier)?.name} — {b.video_title || "Post"}</p>
                  <p className="text-white/50 text-xs">{b.end_date ? `Expires ${new Date(b.end_date).toLocaleDateString()}` : "Active"}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Free promo boost banner */}
        {promoRedemption && (
          <div className="mb-4 bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/40 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <Zap size={16} className="text-amber-400" />
              <span className="text-white font-bold text-sm">Free {promoRedemption.boost_tier} Boost Available!</span>
            </div>
            <p className="text-white/60 text-xs mb-3">
              You have a free {promoRedemption.boost_tier} boost ({promoRedemption.boost_days} days) from promo code "{promoRedemption.code}"
              {promoRedemption.source ? ` via ${promoRedemption.source}` : ""}. Select a post below to apply it — no payment needed.
            </p>
          </div>
        )}

        {/* Tier selection */}
        <p className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-3">Choose a Boost Tier</p>
        <div className="space-y-3">
          {TIERS.map((tier) => (
            <div key={tier.key} className={`rounded-xl border p-4 bg-gradient-to-r ${tier.color} ${tier.border}`}>
              <div className="flex items-center gap-2 mb-2">
                <tier.icon size={18} className="text-white" />
                <span className="text-white font-bold text-sm">{tier.name}</span>
                {tier.popular && <Badge className="text-[9px] bg-amber-500/30 text-amber-300 border-0 ml-auto">POPULAR</Badge>}
                <span className="text-white font-bold ml-auto">{user.is_admin ? "Free" : (!tier.popular ? `$${tier.price}` : "")}</span>
              </div>
              {tier.popular && <p className="text-white text-lg font-bold mb-1">{user.is_admin ? "Free" : `$${tier.price}`}</p>}
              <p className="text-white/50 text-xs mb-2">{tier.duration}</p>
              <ul className="space-y-1 mb-3">
                {tier.features.map((f) => (
                  <li key={f} className="text-white/70 text-xs flex items-center gap-1.5">
                    <CheckCircle2 size={12} className="text-green-400 flex-shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => setSelectedTier(selectedTier === tier.key ? null : tier.key)}
                className={`w-full py-2 rounded-lg text-xs font-bold transition-all ${selectedTier === tier.key ? "bg-white text-black" : "bg-white/10 text-white"}`}
              >
                {selectedTier === tier.key ? "Selected ✓" : "Select"}
              </button>
            </div>
          ))}
        </div>

        {/* Post selector */}
        {selectedTier && user && (
          <div className="mt-6">
            <p className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-3">Select Post to Boost</p>
            <PostSelector
              token={token}
              tier={selectedTier}
              boostingPostId={boostingPostId}
              onBoost={handleBoost}
              error={error}
              userId={user.id}
              preselectedId={preselectedVideoId}
              promoRedemption={promoRedemption}
              onFreeBoost={handleFreeBoost}
              freeBoostLoading={freeBoostLoading}
              isAdmin={user.is_admin}
            />
          </div>
        )}

        {/* Expired/rejected */}
        {boosts.filter((b) => b.status === "expired" || b.status === "rejected").length > 0 && (
          <div className="mt-6">
            <p className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-2">Past Boosts</p>
            <div className="space-y-2">
              {boosts.filter((b) => b.status === "expired" || b.status === "rejected").slice(0, 5).map((b) => (
                <div key={b.id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-3">
                  <XCircle size={14} className="text-white/30 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-white/50 text-xs">{b.video_title || "Post"}</p>
                  </div>
                  <Badge className="text-[9px] border-0 bg-white/10 text-white/40">{b.status}</Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function PostSelector({ token, tier, boostingPostId, onBoost, error, userId, preselectedId, promoRedemption, onFreeBoost, freeBoostLoading, isAdmin }: {
  token: string;
  tier: string;
  boostingPostId: number | null;
  onBoost: (postId: number, tier: string) => void;
  error: string;
  userId: number;
  preselectedId?: number | null;
  promoRedemption: { code: string; boost_tier: string; boost_days: number; source: string; boost_used: boolean } | null;
  onFreeBoost: (postId: number) => void;
  freeBoostLoading: boolean;
  isAdmin?: boolean;
}) {
  const [posts, setPosts] = useState<Array<{ id: number; title: string | null; thumbnail_url: string; image_url: string | null; type: string; category: string }>>([]);

  useEffect(() => {
    fetch(`/api/videos?user_id=${userId}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : [])
      .then((data) => {
        const arr = Array.isArray(data) ? data : data.videos || [];
        // If preselected, sort it to top
        if (preselectedId) {
          const idx = arr.findIndex((p: { id: number }) => p.id === preselectedId);
          if (idx > 0) arr.unshift(arr.splice(idx, 1)[0]);
        }
        setPosts(arr);
      });
  }, [token, userId, preselectedId]);

  if (posts.length === 0) {
    return <p className="text-white/40 text-sm text-center py-4">No posts available to boost</p>;
  }

  return (
    <div className="space-y-2">
      {posts.slice(0, 10).map((post) => (
        <div key={post.id} className={`border rounded-xl p-3 flex items-center gap-3 transition-all ${preselectedId === post.id ? "bg-primary/10 border-primary/40" : "bg-white/5 border-white/10"}`}>
          <div className="w-12 h-12 rounded-lg bg-secondary overflow-hidden flex-shrink-0">
            {post.image_url ? (
              <img src={post.image_url} alt="" className="w-full h-full object-cover" />
            ) : post.thumbnail_url ? (
              <img src={post.thumbnail_url} alt="" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Building2 className="w-5 h-5 text-muted-foreground" />
              </div>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-semibold truncate">{post.title || "Untitled Post"}</p>
            <p className="text-white/40 text-[10px]">{post.type === "worker" ? "Crew" : "Kitchen"} · {post.category}</p>
          </div>
          <div className="flex flex-col gap-1.5">
            <Button
              size="sm"
              onClick={() => onBoost(post.id, tier)}
              disabled={boostingPostId === post.id}
              className="bg-primary text-primary-foreground text-xs ember-glow"
            >
              {boostingPostId === post.id ? "..." : isAdmin ? "Boost Free" : `Boost $${TIERS.find((t) => t.key === tier)?.price ?? ""}`}
            </Button>
            {promoRedemption && (
              <Button
                size="sm"
                onClick={() => onFreeBoost(post.id)}
                disabled={freeBoostLoading}
                className="bg-amber-500 text-black text-xs font-bold hover:bg-amber-400"
              >
                {freeBoostLoading ? "..." : "Use Free Boost"}
              </Button>
            )}
          </div>
        </div>
      ))}
      {error && <p className="text-red-400 text-xs text-center">{error}</p>}
    </div>
  );
}
