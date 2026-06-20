import { useState, useEffect, useRef } from "react";
import type { Video, Review } from "../types";
import { useAuth, useNav } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Settings, LogOut, Camera, Star, Trash2, Pencil, X, AlertTriangle, MessageCircle, DollarSign, Zap, Sparkles, HardHat, Building2, Bell, BellOff, Video as VideoIcon, Lock, ChevronDown, ChevronUp
} from "lucide-react";
import { RoleIcon, CategoryIcon, SaleIcon, EventIcon } from "./Icons";
import { cn } from "@/lib/utils";
import { usePushNotifications } from "../hooks/usePushNotifications";

export default function ProfileScreen() {
  const { user, token, logout, refreshUser } = useAuth();
  const { navigate } = useNav();
  const [videos, setVideos] = useState<Video[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [form, setForm] = useState({ name: "", email: "", bio: "" });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarPreview, setAvatarPreview] = useState<string>("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const avatarRef = useRef<HTMLInputElement>(null);
  
  // Post Edit State
  const [postEditOpen, setPostEditOpen] = useState(false);
  const [editingPost, setEditingPost] = useState<Video | null>(null);
  const [postForm, setPostForm] = useState<{ title: string; description: string; repost: boolean; category: string; price: string; event_date: string; event_time: string; aspect_ratio: string; file?: File }>({ title: "", description: "", repost: false, category: "general", price: "", event_date: "", event_time: "", aspect_ratio: "9:16" });
  const [postSaving, setPostSaving] = useState(false);
  const [expandedPost, setExpandedPost] = useState<number | null>(null);

  // Password change state
  const [pwOpen, setPwOpen] = useState(false);
  const [pwForm, setPwForm] = useState({ current: "", next: "", confirm: "" });
  const [pwSaving, setPwSaving] = useState(false);
  const [pwError, setPwError] = useState("");
  const [pwSuccess, setPwSuccess] = useState(false);

  // Push notifications
  const { permission, subscribed, loading: pushLoading, subscribe, unsubscribe } = usePushNotifications();

  // Dashboard state
  const [expandedDash, setExpandedDash] = useState(false);
  const [dashData, setDashData] = useState<{
    total_posts: number; total_likes: number; total_matches: number; pending_matches: number; active_matches: number;
    active_boosts: Array<{ id: number; tier: string; video_title: string; end_date: string }>;
    advertiser_status: { active: boolean; tier: string | null };
    recent_activity: Array<{ type: string; label: string; created_at: string }>;
  } | null>(null);

  useEffect(() => {
    if (!user || !token) return;
    setForm({ name: user.name, email: user.email || "", bio: user.bio || "" });

    const fetchData = async () => {
      const [vRes, rRes, dRes] = await Promise.all([
        fetch(`/api/videos?user_id=${user.id}`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`/api/users/${user.id}/reviews`),
        fetch(`/api/dashboard`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (vRes.ok) {
        const vData = await vRes.json();
        setVideos(Array.isArray(vData) ? vData : vData.videos || []);
      }
      if (rRes.ok) setReviews(await rRes.json());
      if (dRes.ok) setDashData(await dRes.json());
    };
    fetchData();
  }, [user, token]);

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-6 text-center">
        <p className="text-muted-foreground">Sign in to view your profile</p>
      </div>
    );
  }

  const openEdit = () => {
    setForm({ name: user.name, email: user.email || "", bio: user.bio || "" });
    setAvatarPreview("");
    setAvatarFile(null);
    setSaveError("");
    setEditOpen(true);
  };

  const handleAvatarPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveError("");
    try {
      // Upload avatar first if changed
      if (avatarFile) {
        setAvatarUploading(true);
        const fd = new FormData();
        fd.append("file", avatarFile);
        const res = await fetch("/api/users/me/avatar", {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
          body: fd,
        });
        setAvatarUploading(false);
        if (!res.ok) throw new Error("Failed to upload photo");
      }

      // Save profile fields
      const res = await fetch("/api/users/me", {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ name: form.name, email: form.email, bio: form.bio }),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || "Failed to save");
      }
      await refreshUser();
      setEditOpen(false);
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSaving(false);
      setAvatarUploading(false);
    }
  };

  const handleDeleteVideo = async (id: number) => {
    if (!window.confirm("Delete this video?")) return;
    await fetch(`/api/videos/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    setVideos((prev) => prev.filter((v) => v.id !== id));
  };

  const openEditPost = (video: Video) => {
    setEditingPost(video);
    setPostForm({ title: video.title || "", description: video.description || "", repost: false, category: video.category || "general", price: video.price || "", event_date: video.event_date || "", event_time: video.event_time || "", aspect_ratio: video.aspect_ratio || "9:16" });
    setPostEditOpen(true);
  };

  const handleSavePost = async () => {
    if (!editingPost) return;
    setPostSaving(true);
    try {
      const fd = new FormData();
      fd.append("title", postForm.title);
      fd.append("description", postForm.description);
      fd.append("repost", postForm.repost ? "true" : "false");
      fd.append("category", postForm.category);
      fd.append("price", postForm.price);
      fd.append("event_date", postForm.event_date);
      fd.append("event_time", postForm.event_time);
      fd.append("aspect_ratio", postForm.aspect_ratio);
      if (postForm.file) {
        fd.append("file", postForm.file);
      }

      const res = await fetch(`/api/videos/${editingPost.id}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });

      if (!res.ok) throw new Error("Failed to update post");
      const updated = await res.json();
      
      setVideos(prev => prev.map(v => v.id === updated.id ? updated : v));
      // if reposted, we might want to sort or simply refresh
      if (postForm.repost) {
        setVideos(prev => {
          const others = prev.filter(v => v.id !== updated.id);
          return [updated, ...others];
        });
      }
      setPostEditOpen(false);
    } catch (err) {
      console.error(err);
      alert("Failed to update post");
    } finally {
      setPostSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    try {
      await fetch("/api/users/me", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      logout();
    } finally {
      setDeleting(false);
    }
  };

  const isWorker = user.role === "worker";
  const isAdmin = user.role === "admin";
  const confirmWord = "DELETE";

  return (
    <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">

      {/* Header banner */}
      <div
        className="relative h-32"
        style={{
          background: "linear-gradient(135deg, hsl(25 95% 20%) 0%, hsl(25 95% 35%) 100%)",
        }}
      >
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-4 left-4 w-16 h-16 rounded-full bg-primary/40" />
          <div className="absolute top-8 right-8 w-24 h-24 rounded-full bg-primary/20" />
        </div>
        {/* Action buttons */}
        <div className="absolute top-3 right-3 flex gap-2">
          <button
            onClick={openEdit}
            className="w-8 h-8 bg-black/30 backdrop-blur rounded-full flex items-center justify-center text-white/80 hover:text-white transition-colors"
            title="Edit profile"
          >
            <Settings size={15} />
          </button>
          <button
            onClick={logout}
            className="w-8 h-8 bg-black/30 backdrop-blur rounded-full flex items-center justify-center text-white/80 hover:text-white transition-colors"
            title="Sign out"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>

      {/* Avatar */}
      <div className="px-5 -mt-10 mb-4 flex items-end justify-between">
        <div className="relative">
          <div className="w-20 h-20 rounded-2xl bg-secondary border-4 border-background overflow-hidden ember-glow">
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-2xl font-black text-primary">
                {user.name[0]?.toUpperCase()}
              </div>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="flex gap-4 text-center">
          <div>
            <p className="text-lg font-bold text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>
              {videos.length}
            </p>
            <p className="text-[10px] text-muted-foreground">Posts</p>
          </div>
          {!user.is_admin && (
            <>
              <div>
                <p className="text-lg font-bold text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>
                  {user.total_shifts}
                </p>
                <p className="text-[10px] text-muted-foreground">Shifts</p>
              </div>
              <div>
                <p className="text-lg font-bold text-primary flex items-center gap-0.5" style={{ fontFamily: "'Bebas Neue'" }}>
                  <Star size={14} className="fill-primary" />
                  {user.avg_rating ? Number(user.avg_rating).toFixed(1) : "—"}
                </p>
                <p className="text-[10px] text-muted-foreground">Rating</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Name / role / bio */}
      <div className="px-5 mb-5">
        <div className="flex items-center gap-2 mb-1">
          <h2 className="text-xl font-bold text-foreground">{user.name}</h2>
          <Badge className={`text-[10px] border-0 ${
            isAdmin ? "bg-purple-500/20 text-purple-300" :
            isWorker ? "bg-orange-500/20 text-orange-300" : "bg-blue-500/20 text-blue-300"
          }`}>
            <RoleIcon role={user.role} className="w-3 h-3 mr-1" />
            {isAdmin ? "Admin" : isWorker ? "Crew" : "Kitchen"}
          </Badge>
          <button
            onClick={openEdit}
            className="ml-auto text-muted-foreground hover:text-primary transition-colors"
            title="Edit profile"
          >
            <Pencil size={14} />
          </button>
        </div>
        {user.bio && <p className="text-muted-foreground text-sm leading-snug">{user.bio}</p>}

        {/* Contact Day Shift */}
        <button
          onClick={() => navigate("support")}
          className="w-full mt-3 p-3 bg-card border border-border rounded-xl flex items-center gap-3 hover:bg-muted/50 transition-colors text-left"
        >
          <div className="w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
            <MessageCircle size={16} className="text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-foreground font-semibold text-sm">Contact Day Shift</p>
            <p className="text-muted-foreground text-xs">Get help, report an issue, or ask a question</p>
          </div>
        </button>

        {/* Push Notifications Toggle */}
        <button
          onClick={subscribed ? unsubscribe : subscribe}
          disabled={pushLoading || permission === "denied"}
          className="w-full mt-2 p-3 bg-card border border-border rounded-xl flex items-center gap-3 hover:bg-muted/50 transition-colors text-left disabled:opacity-50"
        >
          <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${subscribed ? "bg-green-500/20" : "bg-secondary"}`}>
            {subscribed ? <Bell size={16} className="text-green-400" /> : <BellOff size={16} className="text-muted-foreground" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-foreground font-semibold text-sm">
              {pushLoading ? "Setting up…" : subscribed ? "Notifications On" : "Enable Notifications"}
            </p>
            <p className="text-muted-foreground text-xs">
              {permission === "denied"
                ? "Blocked by browser — enable in Settings"
                : subscribed
                ? "You'll get notified for matches & messages"
                : "Get alerts for new matches and messages"}
            </p>
          </div>
        </button>

        {/* Change Password */}
        <button
          onClick={() => { setPwForm({ current: "", next: "", confirm: "" }); setPwError(""); setPwSuccess(false); setPwOpen(true); }}
          className="w-full mt-2 p-3 bg-card border border-border rounded-xl flex items-center gap-3 hover:bg-muted/50 transition-colors text-left"
        >
          <div className="w-9 h-9 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
            <Lock size={16} className="text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-foreground font-semibold text-sm">Change Password</p>
          </div>
        </button>

      </div>

      {/* Dashboard — collapsible overview */}
      {dashData && (
        <div className="px-5 mb-5">
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <button
              onClick={() => setExpandedDash(!expandedDash)}
              className="w-full p-3 flex items-center justify-between hover:bg-secondary/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <Building2 size={14} className="text-purple-400" />
                </div>
                <div className="text-left">
                  <p className="font-semibold text-foreground text-sm">Dashboard</p>
                  <p className="text-[11px] text-muted-foreground">{dashData.total_posts} posts · {dashData.total_matches} matches</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {dashData.active_boosts.length > 0 && (
                  <Badge className="text-[10px] border-0 bg-green-500/20 text-green-400">
                    {dashData.active_boosts.length} boost{dashData.active_boosts.length !== 1 ? "s" : ""} active
                  </Badge>
                )}
                {expandedDash ? (
                  <ChevronUp size={16} className="text-muted-foreground" />
                ) : (
                  <ChevronDown size={16} className="text-muted-foreground" />
                )}
              </div>
            </button>

            {expandedDash && (
              <div className="border-t border-border p-3 space-y-4">
                {/* Account Status */}
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-2">Account Status</p>
                  <div className="grid grid-cols-4 gap-2">
                    <div className="text-center">
                      <p className="text-sm font-bold text-foreground">{dashData.total_posts}</p>
                      <p className="text-[9px] text-muted-foreground">Posts</p>
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-bold text-foreground">{dashData.total_likes}</p>
                      <p className="text-[9px] text-muted-foreground">Likes</p>
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-bold text-foreground">{dashData.total_matches}</p>
                      <p className="text-[9px] text-muted-foreground">Matches</p>
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-bold text-primary flex items-center justify-center gap-0.5">
                        <Star size={10} className="fill-primary" />
                        {user.avg_rating ? Number(user.avg_rating).toFixed(1) : "—"}
                      </p>
                      <p className="text-[9px] text-muted-foreground">Rating</p>
                    </div>
                  </div>
                  {dashData.pending_matches > 0 && (
                    <div className="mt-2 flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                      <MessageCircle size={12} className="text-amber-400 flex-shrink-0" />
                      <p className="text-[11px] text-amber-400">{dashData.pending_matches} pending match{dashData.pending_matches !== 1 ? "es" : ""} waiting for response</p>
                    </div>
                  )}
                </div>

                {/* Active Boosts */}
                {dashData.active_boosts.length > 0 && (
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-2">Active Boosts</p>
                    <div className="space-y-1.5">
                      {dashData.active_boosts.map((b) => (
                        <div key={b.id} className="flex items-center justify-between bg-secondary/30 rounded-lg px-3 py-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <Zap size={12} className="text-amber-400 flex-shrink-0" />
                            <span className="text-xs text-foreground truncate">{b.video_title || "Post"}</span>
                          </div>
                          <Badge className="text-[9px] border-0 bg-amber-500/20 text-amber-400 flex-shrink-0">
                            {b.tier} · {new Date(b.end_date).toLocaleDateString()}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Advertiser Status */}
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-2">Advertiser Status</p>
                  <div className="flex items-center justify-between bg-secondary/30 rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Sparkles size={12} className={dashData.advertiser_status.active ? "text-purple-400" : "text-muted-foreground"} />
                      <span className="text-xs text-foreground">
                        {dashData.advertiser_status.active
                          ? `Active — ${dashData.advertiser_status.tier?.charAt(0).toUpperCase() + dashData.advertiser_status.tier?.slice(1)} Plan`
                          : "Not subscribed"}
                      </span>
                    </div>
                    {!dashData.advertiser_status.active && (
                      <Button
                        size="sm"
                        onClick={() => navigate("advertise")}
                        className="h-6 px-2 text-[10px] bg-primary hover:bg-primary/90 text-primary-foreground"
                      >
                        Subscribe
                      </Button>
                    )}
                  </div>
                </div>

                {/* Quick Links */}
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-2">Quick Links</p>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => navigate("boost")}
                      className="flex items-center gap-2 bg-secondary/30 rounded-lg px-3 py-2 hover:bg-secondary/50 transition-colors"
                    >
                      <Zap size={14} className="text-amber-400" />
                      <span className="text-xs text-foreground font-medium">Boost a Post</span>
                    </button>
                    <button
                      onClick={() => navigate("analytics")}
                      className="flex items-center gap-2 bg-secondary/30 rounded-lg px-3 py-2 hover:bg-secondary/50 transition-colors"
                    >
                      <Building2 size={14} className="text-purple-400" />
                      <span className="text-xs text-foreground font-medium">Analytics</span>
                    </button>
                    {dashData.advertiser_status.active && (
                      <button
                        onClick={() => navigate("advertise")}
                        className="flex items-center gap-2 bg-secondary/30 rounded-lg px-3 py-2 hover:bg-secondary/50 transition-colors"
                      >
                        <Sparkles size={14} className="text-purple-400" />
                        <span className="text-xs text-foreground font-medium">Manage Ads</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Recent Activity */}
                {dashData.recent_activity.length > 0 && (
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-2">Recent Activity</p>
                    <div className="space-y-1.5">
                      {dashData.recent_activity.slice(0, 5).map((item, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <Badge className="text-[8px] border-0 w-6 justify-center flex-shrink-0 bg-muted text-muted-foreground">
                            {item.type === "post" ? "📝" : item.type === "match" ? "🤝" : "⭐"}
                          </Badge>
                          <span className="text-foreground truncate flex-1">
                            {item.type === "post" ? "New post" : item.type === "match" ? `Match ${item.label}` : `Review received`}
                            {item.label && item.type !== "match" ? `: ${item.label}` : ""}
                          </span>
                          <span className="text-muted-foreground text-[10px] flex-shrink-0">{new Date(item.created_at).toLocaleDateString()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* My Posts — single collapsible container */}
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
                  <p className="font-semibold text-foreground text-sm">My Posts</p>
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
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-foreground text-sm truncate">{video.title || "Untitled"}</span>
                          {video.category && (
                            <Badge className="text-[9px] border-0 bg-muted text-muted-foreground">{video.category}</Badge>
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
                      <Button size="sm" variant="outline" onClick={() => openEditPost(video)} className="text-xs flex-shrink-0">
                        <Pencil size={12} className="mr-1" /> Edit
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleDeleteVideo(video.id)} className="text-xs text-destructive border-destructive/40 hover:bg-destructive/10 flex-shrink-0">
                        <Trash2 size={12} />
                      </Button>
                      <div className="flex-1" />
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
          <div className="flex flex-col items-center justify-center py-8 text-center border-2 border-dashed border-border rounded-xl">
            <p className="text-muted-foreground text-sm mb-2">No posts yet</p>
            <button
              onClick={() => navigate("post")}
              className="text-xs text-primary font-semibold hover:underline"
            >
              Create your first post →
            </button>
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
                  <div className="w-7 h-7 rounded-full bg-secondary overflow-hidden">
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
                        <Star key={i} size={10} className={i < review.rating ? "fill-primary text-primary" : "text-border"} />
                      ))}
                    </div>
                  </div>
                </div>
                {review.feedback && <p className="text-muted-foreground text-xs">{review.feedback}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Legal Footer ──────────────────────────────────────────── */}
      <div className="flex items-center justify-center gap-3 py-4 text-[10px] text-muted-foreground/60">
        <button onClick={() => navigate("terms")} className="hover:text-primary transition-colors">Terms of Use</button>
        <span>·</span>
        <button onClick={() => navigate("privacy")} className="hover:text-primary transition-colors">Privacy Policy</button>
      </div>

      {/* ── Edit Profile Dialog ──────────────────────────────────────────── */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="bg-card border-border max-w-sm mx-auto rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-foreground" style={{ fontFamily: "'Bebas Neue'", fontSize: "1.4rem" }}>
              Edit Profile
            </DialogTitle>
          </DialogHeader>

          <div className="overflow-y-auto max-h-[65vh] space-y-4 pt-1 pr-1">
            {/* Avatar picker */}
            <div className="flex items-center gap-3">
              <div className="relative flex-shrink-0">
                <div className="w-16 h-16 rounded-2xl overflow-hidden bg-secondary border-2 border-border">
                  {avatarPreview ? (
                    <img src={avatarPreview} alt="" className="w-full h-full object-cover" />
                  ) : user.avatar_url ? (
                    <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xl font-black text-primary">
                      {user.name[0]?.toUpperCase()}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => avatarRef.current?.click()}
                  className="absolute -bottom-1 -right-1 w-6 h-6 bg-primary rounded-full flex items-center justify-center"
                >
                  <Camera size={12} className="text-primary-foreground" />
                </button>
                <input ref={avatarRef} type="file" accept="image/*" className="hidden" onChange={handleAvatarPick} />
              </div>
              <div className="flex flex-col gap-1">
                <button
                  onClick={() => avatarRef.current?.click()}
                  className="text-xs text-primary hover:underline text-left"
                >
                  {avatarPreview ? "Change photo" : "Upload photo"}
                </button>
                {avatarPreview && (
                  <button
                    onClick={() => { setAvatarPreview(""); setAvatarFile(null); }}
                    className="text-xs text-muted-foreground hover:text-destructive text-left flex items-center gap-1"
                  >
                    <X size={10} /> Cancel
                  </button>
                )}
              </div>
            </div>

            {/* Name */}
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">Name</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="bg-secondary border-border"
                placeholder="Your name"
              />
            </div>

            {/* Email */}
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">Email</Label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="bg-secondary border-border"
                placeholder="you@example.com"
              />
            </div>

            {/* Bio */}
            <div className="space-y-1.5">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">Bio</Label>
              <Textarea
                value={form.bio}
                onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
                className="bg-secondary border-border resize-none text-sm"
                rows={3}
                placeholder={isWorker ? "Your experience, availability, specialties..." : "Your spot, cuisine type, team culture..."}
              />
            </div>

            {saveError && (
              <p className="text-destructive text-xs text-center bg-destructive/10 rounded-lg py-2 px-3">{saveError}</p>
            )}

            <div className="flex gap-2 pt-1">
              <Button
                variant="outline"
                className="flex-1 border-border text-foreground"
                onClick={() => setEditOpen(false)}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={handleSave}
                disabled={saving || !form.name.trim()}
              >
                {saving ? (
                  <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                ) : avatarUploading ? "Uploading…" : "Save Changes"}
              </Button>
            </div>
          </div>

          {/* Delete account */}
          <div className="pt-3 border-t border-border mt-1">
            <button
              onClick={() => { setEditOpen(false); setConfirmText(""); setDeleteOpen(true); }}
              className="w-full text-xs text-destructive/60 hover:text-destructive transition-colors text-center py-2"
            >
              Delete account
            </button>
          </div>
        </DialogContent>
      </Dialog>
      {/* ── Edit Post Dialog ──────────────────────────────────────────── */}
      <Dialog open={postEditOpen} onOpenChange={setPostEditOpen}>
        <DialogContent className="bg-card border-border max-w-sm mx-auto rounded-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-foreground" style={{ fontFamily: "'Bebas Neue'", fontSize: "1.4rem" }}>
              Edit Post
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-1">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Description</Label>
              <Textarea
                placeholder="What's this post about?"
                value={postForm.description}
                onChange={(e) => setPostForm({ ...postForm, description: e.target.value })}
                className="bg-secondary border-border min-h-[80px]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Category</Label>
                {user?.is_admin ? (
                  <Input
                    value={postForm.category}
                    onChange={(e) => setPostForm({ ...postForm, category: e.target.value })}
                    placeholder="Type any category..."
                    className="bg-secondary border-border"
                  />
                ) : (
                <Select onValueChange={(v) => setPostForm({ ...postForm, category: v })} value={postForm.category}>
                  <SelectTrigger className="bg-secondary border-border">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(user?.role === "worker" || user?.is_admin) && <SelectItem value="crew"><HardHat size={12} className="inline mr-1" /> Crew</SelectItem>}
                    <SelectItem value="sale"><SaleIcon className="w-3 h-3 inline mr-1" />For Sale</SelectItem>
                    <SelectItem value="event"><EventIcon className="w-3 h-3 inline mr-1" />Event</SelectItem>
                  </SelectContent>
                </Select>
                )}
              </div>
              {postForm.category === "sale" && (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Price</Label>
                  <Input value={postForm.price} onChange={(e) => setPostForm({ ...postForm, price: e.target.value })} placeholder="$150" className="bg-secondary border-border" />
                </div>
              )}
              {postForm.category === "event" && (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Date</Label>
                  <Input type="date" value={postForm.event_date} onChange={(e) => setPostForm({ ...postForm, event_date: e.target.value })} className="bg-secondary border-border" />
                </div>
              )}
            </div>
            {postForm.category === "event" && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Time</Label>
                  <Input type="time" value={postForm.event_time} onChange={(e) => setPostForm({ ...postForm, event_time: e.target.value })} className="bg-secondary border-border" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Price</Label>
                  <Input value={postForm.price} onChange={(e) => setPostForm({ ...postForm, price: e.target.value })} placeholder="$25 or Free" className="bg-secondary border-border" />
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Aspect Ratio</Label>
              <div className="flex items-center gap-1">
                <span className="text-[9px] text-muted-foreground mr-1">Tall</span>
                {(["9:16", "4:5", "1:1", "16:9"] as const).map((r) => (
                  <button key={r} type="button" onClick={() => setPostForm({ ...postForm, aspect_ratio: r })}
                    className={cn("px-2 py-0.5 rounded text-[9px] font-bold transition-all", postForm.aspect_ratio === r ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground bg-secondary")}
                  >{r}</button>
                ))}
                <span className="text-[9px] text-muted-foreground ml-1">Wide</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Replace Media</Label>
              <Input
                type="file"
                accept="image/*,video/*"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    setPostForm({ ...postForm, file });
                  }
                }}
                className="bg-secondary border-border"
              />
              <p className="text-[10px] text-muted-foreground">Upload a new photo or video to replace the current one.</p>
            </div>

            <div className="flex gap-2 pt-4 pb-2">
              <Button
                variant="outline"
                className="flex-1 border-border text-foreground"
                onClick={() => setPostEditOpen(false)}
                disabled={postSaving}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={handleSavePost}
                disabled={postSaving}
              >
                {postSaving ? (
                  <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                ) : "Save Changes"}
              </Button>
            </div>
          </div>
          
          <div className="pt-2 border-t border-border mt-2 sticky bottom-0 bg-card">
            <button
              onClick={() => {
                setPostEditOpen(false);
                if (editingPost) handleDeleteVideo(editingPost.id);
              }}
              className="w-full text-xs text-destructive/80 hover:text-destructive transition-colors text-center py-1 flex items-center justify-center gap-1.5 font-medium"
            >
              <Trash2 size={13} />
              Delete Post
            </button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── Delete Account Confirmation Dialog ─────────────────────────── */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="bg-card border-border max-w-sm mx-auto rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2" style={{ fontFamily: "'Bebas Neue'", fontSize: "1.4rem" }}>
              <AlertTriangle size={20} />
              Delete Account
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 pt-1">
            <div className="bg-destructive/10 border border-destructive/30 rounded-xl p-3 space-y-1">
              <p className="text-sm font-semibold text-destructive">This cannot be undone.</p>
              <ul className="text-xs text-destructive/80 space-y-0.5 list-disc list-inside">
                <li>All your videos will be deleted</li>
                <li>All your matches and messages will be deleted</li>
                <li>All your reviews will be deleted</li>
                <li>Your account will be permanently removed</li>
              </ul>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">
                Type <span className="font-bold text-destructive">{confirmWord}</span> to confirm
              </Label>
              <Input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                className="bg-secondary border-destructive/40 focus:border-destructive text-sm"
                placeholder={confirmWord}
              />
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1 border-border text-foreground"
                onClick={() => setDeleteOpen(false)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onClick={handleDeleteAccount}
                disabled={deleting || confirmText !== confirmWord}
              >
                {deleting ? (
                  <div className="w-4 h-4 border-2 border-destructive-foreground border-t-transparent rounded-full animate-spin" />
                ) : "Delete Forever"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── Change Password Dialog ──────────────────────────────────────── */}
      <Dialog open={pwOpen} onOpenChange={setPwOpen}>
        <DialogContent className="bg-card border-border max-w-sm mx-auto rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-foreground flex items-center gap-2" style={{ fontFamily: "'Bebas Neue'", fontSize: "1.4rem" }}>
              <Lock size={18} /> Change Password
            </DialogTitle>
          </DialogHeader>
          {pwSuccess ? (
            <div className="text-center py-4">
              <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-3">
                <Star size={20} className="text-green-400" />
              </div>
              <p className="text-foreground font-semibold text-sm">Password updated!</p>
              <p className="text-muted-foreground text-xs mt-1">Use your new password next time you sign in.</p>
              <Button onClick={() => setPwOpen(false)} className="mt-4 w-full">Done</Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <Label className="text-muted-foreground text-xs">Current Password</Label>
                <Input
                  type="password"
                  value={pwForm.current}
                  onChange={(e) => setPwForm(f => ({ ...f, current: e.target.value }))}
                  className="bg-background border-border mt-1"
                  placeholder="Enter current password"
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">New Password</Label>
                <Input
                  type="password"
                  value={pwForm.next}
                  onChange={(e) => setPwForm(f => ({ ...f, next: e.target.value }))}
                  className="bg-background border-border mt-1"
                  placeholder="At least 8 chars, 1 letter, 1 number"
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">Confirm New Password</Label>
                <Input
                  type="password"
                  value={pwForm.confirm}
                  onChange={(e) => setPwForm(f => ({ ...f, confirm: e.target.value }))}
                  className="bg-background border-border mt-1"
                  placeholder="Re-enter new password"
                />
              </div>
              {pwError && <p className="text-red-400 text-xs text-center">{pwError}</p>}
              <Button
                onClick={async () => {
                  if (pwForm.next !== pwForm.confirm) { setPwError("Passwords don't match"); return; }
                  if (pwForm.next.length < 8) { setPwError("Password must be at least 8 characters"); return; }
                  setPwSaving(true); setPwError("");
                  try {
                    const res = await fetch("/api/auth/change-password", {
                      method: "POST",
                      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
                      body: JSON.stringify({ current_password: pwForm.current, new_password: pwForm.next }),
                    });
                    const data = await res.json();
                    if (!res.ok) { setPwError(data.detail || "Failed to change password"); return; }
                    setPwSuccess(true);
                  } catch { setPwError("Network error"); }
                  finally { setPwSaving(false); }
                }}
                disabled={pwSaving || !pwForm.current || !pwForm.next || !pwForm.confirm}
                className="w-full"
              >
                {pwSaving ? "Updating..." : "Update Password"}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

    </div>
  );
}