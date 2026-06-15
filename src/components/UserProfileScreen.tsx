import { useState, useEffect } from "react";
import type { User, Video, Review } from "../types";
import { useAuth, useNav } from "../App";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Star, Play, ArrowLeft, MessageCircle, Flag, Ban, ShieldCheck } from "lucide-react";
import { RoleIcon } from "./Icons";
import { trackEvent } from "../lib/analytics";

export default function UserProfileScreen({ userId }: { userId: number }) {
  const { user: currentUser, token } = useAuth();
  const { navigate } = useNav();
  const [profile, setProfile] = useState<User | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [showReport, setShowReport] = useState(false);
  const [reportReason, setReportReason] = useState("other");
  const [reportComment, setReportComment] = useState("");
  const [reportSent, setReportSent] = useState(false);
  const [blocked, setBlocked] = useState(false);

  useEffect(() => {
    if (!userId) return;
    const fetchData = async () => {
      setLoading(true);
      try {
        const [uRes, vRes, rRes] = await Promise.all([
          fetch(`/api/users/${userId}`),
          fetch(`/api/videos?user_id=${userId}`),
          fetch(`/api/users/${userId}/reviews`),
        ]);
        if (uRes.ok) setProfile(await uRes.json());
        if (vRes.ok) setVideos(await vRes.json());
        if (rRes.ok) setReviews(await rRes.json());

        // Check if user is blocked
        if (token && currentUser) {
          const bRes = await fetch("/api/blocks", { headers: { Authorization: `Bearer ${token}` } });
          if (bRes.ok) {
            const blocks = await bRes.json();
            setBlocked(blocks.some((b: { blocked_id: number }) => b.blocked_id === userId));
          }
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [userId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-muted-foreground">User not found</p>
      </div>
    );
  }

  const isOwnProfile = currentUser?.id === userId;

  const handleToggleBlock = async () => {
    if (!token) return;
    try {
      const res = await fetch("/api/blocks", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      if (res.ok) {
        const data = await res.json();
        setBlocked(data.blocked);
      }
    } catch {}
  };

  return (
    <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
      {/* Back button */}
      <div className="p-4">
        <button
          onClick={() => navigate("feed")}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={18} /> Back
        </button>
      </div>

      {/* Profile header */}
      <div className="px-5 flex items-center gap-4 mb-4">
        <div className="w-20 h-20 rounded-2xl bg-secondary border-2 border-border overflow-hidden ember-glow flex-shrink-0">
          {profile.avatar_url ? (
            <img src={profile.avatar_url} alt="" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-3xl font-black text-primary">
              {profile.name[0]?.toUpperCase()}
            </div>
          )}
        </div>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold text-foreground">{profile.name}</h2>
            <Badge className={`text-[10px] border-0 ${
              profile.role === "admin" ? "bg-purple-500/20 text-purple-400" :
              profile.role === "worker" ? "bg-orange-500/20 text-orange-400" : "bg-blue-500/20 text-blue-400"
            }`}>
              <RoleIcon role={profile.role as "admin" | "worker" | "employer"} className="w-3 h-3 mr-1" />
              {profile.role === "admin" ? "Admin" : profile.role === "worker" ? "Crew" : "Kitchen"}
            </Badge>
          </div>
          <div className="flex gap-4 text-sm">
            <div className="text-center">
              <p className="font-bold text-foreground">{videos.length}</p>
              <p className="text-[10px] text-muted-foreground">Posts</p>
            </div>
            {!profile.is_admin && (
              <>
                <div className="text-center">
                  <p className="font-bold text-foreground">{profile.total_shifts}</p>
                  <p className="text-[10px] text-muted-foreground">Shifts</p>
                </div>
                <div className="text-center">
                  <p className="font-bold text-primary flex items-center gap-0.5">
                    <Star size={12} className="fill-primary" />
                    {profile.avg_rating ? Number(profile.avg_rating).toFixed(1) : "New"}
                  </p>
                  <p className="text-[10px] text-muted-foreground">Rating</p>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {profile.bio && (
        <div className="px-5 mb-4">
          <p className="text-muted-foreground text-sm">{profile.bio}</p>
        </div>
      )}

      {/* Match / Chat button if other user */}
      {!isOwnProfile && currentUser && (
        <div className="px-5 mb-5 flex gap-2">
          <Button
            onClick={() => navigate("matches")}
            className="flex-1 bg-primary text-primary-foreground ember-glow"
          >
            <MessageCircle size={16} className="mr-2" /> View Matches
          </Button>
          <Button
            onClick={handleToggleBlock}
            variant={blocked ? "default" : "outline"}
            className={`flex-none ${blocked ? "bg-destructive text-destructive-foreground" : "border-border text-muted-foreground hover:bg-destructive/10 hover:text-destructive"}`}
          >
            <Ban size={16} />
          </Button>
          <Button
            onClick={() => setShowReport(true)}
            variant="outline"
            className="flex-none border-destructive/40 text-destructive hover:bg-destructive/10"
          >
            <Flag size={16} />
          </Button>
        </div>
      )}

      {/* Blocked banner */}
      {blocked && !isOwnProfile && (
        <div className="px-5 mb-4">
          <div className="flex items-center gap-2 bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
            <Ban size={14} className="text-destructive flex-shrink-0" />
            <p className="text-destructive text-xs">This user is blocked. Tap the block button to unblock.</p>
          </div>
        </div>
      )}

      {/* Report modal */}
      {showReport && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setShowReport(false)}>
          <div className="bg-card border border-border rounded-2xl p-5 w-full max-w-sm space-y-3" onClick={(e) => e.stopPropagation()}>
            {reportSent ? (
              <div className="text-center py-4">
                <p className="text-primary text-lg font-semibold">Report Submitted</p>
                <p className="text-muted-foreground text-sm mt-1">We'll review this account</p>
              </div>
            ) : (
              <>
                <h3 className="text-foreground font-semibold text-sm">Report {profile?.name}</h3>
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
                  <button onClick={() => setShowReport(false)} className="flex-1 px-4 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground">Cancel</button>
                  <button
                    onClick={async () => {
                      try {
                        const res = await fetch("/api/reports", {
                          method: "POST",
                          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
                          body: JSON.stringify({ target_type: "user", target_id: userId, reason: reportReason, comment: reportComment || null }),
                        });
                        if (res.ok) {
                          setReportSent(true);
                          trackEvent("user_reported", { user_id: userId, reason: reportReason });
                          setTimeout(() => { setShowReport(false); setReportSent(false); setReportComment(""); }, 1500);
                        }
                      } catch {}
                    }}
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

      {/* Videos */}
      {videos.length > 0 && (
        <div className="px-5 mb-5">
          <h3 className="text-lg text-foreground mb-3" style={{ fontFamily: "'Bebas Neue'" }}>
                      Posts ({videos.length})
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {videos.map((video) => {
              const ar = video.aspect_ratio || "9:16";
              const cardAspect = ar === "9:16" ? "3/4" : ar === "4:5" ? "4/5" : ar === "1:1" ? "1/1" : ar === "16:9" ? "16/9" : "3/4";
              return (
              <div key={video.id} className="relative bg-card rounded-xl overflow-hidden border border-border" style={{ aspectRatio: cardAspect }}>
                {video.image_url ? (
                  <img src={video.image_url} alt={video.title || ""} className="w-full h-full object-cover" />
                ) : video.video_url ? (
                  <video src={video.video_url} className="w-full h-full object-cover" muted />
                ) : video.description ? (
                  <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-purple-900/40 to-purple-950/60 p-3">
                    <p className="text-white/80 text-[10px] text-center line-clamp-3">{video.description}</p>
                  </div>
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Play size={24} className="text-muted-foreground" />
                  </div>
                )}
                <div className="absolute bottom-1 left-1 right-1">
                  <p className="text-white text-[10px] font-medium truncate drop-shadow">{video.title || video.description?.slice(0, 30)}</p>
                </div>
                <Badge
                  className={`absolute top-1 left-1 text-[9px] border-0 py-0 px-1
                    ${video.type === "worker" ? "bg-orange-500/80 text-white" : "bg-blue-500/80 text-white"}`}
                >
                  <RoleIcon role={video.type === "worker" ? "worker" : "employer"} className="w-3 h-3" />
                </Badge>
              </div>
            );
            })}
          </div>
        </div>
      )}

      {/* Reviews */}
      {reviews.length > 0 && (
        <div className="px-5">
          <h3 className="text-lg text-foreground mb-3" style={{ fontFamily: "'Bebas Neue'" }}>
            Reviews ({reviews.length})
          </h3>
          <div className="space-y-3">
            {reviews.map((review) => (
              <div key={review.id} className="bg-card rounded-xl p-4 border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-7 h-7 rounded-full bg-secondary overflow-hidden flex-shrink-0">
                    {review.reviewer_avatar ? (
                      <img src={review.reviewer_avatar} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-xs font-bold text-primary">
                        {review.reviewer_name?.[0]}
                      </div>
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-semibold text-foreground">{review.reviewer_name}</p>
                    <div className="flex gap-0.5">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star
                          key={i}
                          size={10}
                          className={i < review.rating ? "fill-primary text-primary" : "text-border"}
                        />
                      ))}
                    </div>
                  </div>
                </div>
                {review.feedback && (
                  <p className="text-muted-foreground text-xs">{review.feedback}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
