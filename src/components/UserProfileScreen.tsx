import { useState, useEffect } from "react";
import type { User, Video, Review } from "../types";
import { useAuth, useNav } from "../App";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Star, Play, ArrowLeft, MessageCircle, Flag, Ban, ShieldCheck, Video as VideoIcon, ChevronDown, ChevronUp, Zap, Sparkles } from "lucide-react";
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
  const [expandedPost, setExpandedPost] = useState<number | null>(null);
  const [blockLoading, setBlockLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");

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
        if (vRes.ok) {
          const vData = await vRes.json();
          setVideos(Array.isArray(vData) ? vData : vData.videos || []);
        }
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
    if (blockLoading) return;
    if (!token) return;
    setBlockLoading(true);
    try {
      const res = await fetch("/api/blocks", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      if (!res.ok) throw new Error("Failed to update block");
      const data = await res.json();
      setBlocked(data.blocked);
    } catch (err: unknown) {
      setReportError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBlockLoading(false);
    }
  };

  const handleSubmitReport = async () => {
    if (reportLoading) return;
    setReportLoading(true);
    setReportError("");
    try {
      const res = await fetch("/api/reports", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ target_type: "user", target_id: userId, reason: reportReason, comment: reportComment || null }),
      });
      if (!res.ok) throw new Error("Failed to submit report");
      setReportSent(true);
      trackEvent("user_reported", { user_id: userId, reason: reportReason });
      setTimeout(() => { setShowReport(false); setReportSent(false); setReportComment(""); }, 1500);
    } catch (err: unknown) {
      setReportError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setReportLoading(false);
    }
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
            disabled={blockLoading}
            variant={blocked ? "default" : "outline"}
            className={`flex-none ${blocked ? "bg-destructive text-destructive-foreground" : "border-border text-muted-foreground hover:bg-destructive/10 hover:text-destructive"}`}
          >
            {blockLoading ? (
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <Ban size={16} />
            )}
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
                    onClick={handleSubmitReport}
                    disabled={reportLoading}
                    className="flex-1 px-4 py-2 rounded-lg text-xs font-medium bg-destructive text-destructive-foreground disabled:opacity-50 flex items-center justify-center gap-1.5"
                  >
                    {reportLoading ? (
                      <div className="w-3 h-3 border-2 border-destructive-foreground border-t-transparent rounded-full animate-spin" />
                    ) : null}
                    Submit Report
                  </button>
                </div>
                {reportError && (
                  <p className="text-destructive text-xs text-center">{reportError}</p>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Posts — single collapsible container */}
      {videos.length > 0 && (
        <div className="px-5 mb-5">
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <button
              onClick={() => setExpandedPost(expandedPost === -1 ? null : -1)}
              className="w-full p-3 flex items-center justify-between hover:bg-secondary/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <VideoIcon size={14} className="text-primary" />
                </div>
                <div className="text-left">
                  <p className="font-semibold text-foreground text-sm">Posts</p>
                  <p className="text-[11px] text-muted-foreground">{videos.length} post{videos.length !== 1 ? "s" : ""}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className="text-[10px] border-0 bg-primary/20 text-primary">
                  {videos.length}
                </Badge>
                {expandedPost === -1 ? (
                  <ChevronUp size={16} className="text-muted-foreground" />
                ) : (
                  <ChevronDown size={16} className="text-muted-foreground" />
                )}
              </div>
            </button>

            {expandedPost === -1 && (
              <div className="border-t border-border divide-y divide-border">
                {videos.map((video) => (
                  <div key={video.id} className="p-3 bg-secondary/20">
                    <div className="flex items-start gap-3">
                      {video.image_url ? (
                        <img src={video.image_url} alt="" className="w-16 h-16 rounded-lg object-cover bg-black flex-shrink-0" />
                      ) : video.video_url ? (
                        <div className="w-16 h-16 rounded-lg bg-black flex-shrink-0 flex items-center justify-center text-muted-foreground">
                          <VideoIcon size={20} />
                        </div>
                      ) : (
                        <div className="w-16 h-16 rounded-lg bg-secondary flex-shrink-0 flex items-center justify-center text-muted-foreground text-[10px]">
                          Text
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-foreground text-sm truncate">{video.title || "Untitled"}</span>
                          {video.category && (
                            <Badge className={`text-[9px] border-0 ${video.type === "worker" ? "bg-orange-500/20 text-orange-300" : "bg-blue-500/20 text-blue-300"}`}>{video.category}</Badge>
                          )}
                        </div>
                        {video.description && (
                          <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5">{video.description}</p>
                        )}
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          {video.location && <span className="text-[10px] text-muted-foreground">📍 {video.location}</span>}
                          {video.pay_rate && <span className="text-[10px] text-muted-foreground">💰 {video.pay_rate}</span>}
                          <span className="text-[10px] text-muted-foreground">{video.likes} likes · {new Date(video.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/50">
                      <Button size="sm" onClick={() => navigate("boost", { videoId: video.id })} className="h-7 px-2 text-xs bg-amber-500 hover:bg-amber-600 text-white flex-shrink-0">
                        <Zap size={12} className="mr-0.5" /> Boost
                      </Button>
                      <Button size="sm" onClick={() => navigate("advertise")} className="h-7 px-2 text-xs bg-primary hover:bg-primary/90 text-primary-foreground flex-shrink-0">
                        <Sparkles size={12} className="mr-0.5" /> Ad
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {videos.length === 0 && (
        <div className="px-5 mb-5">
          <p className="text-muted-foreground text-sm text-center py-6">No posts yet</p>
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
