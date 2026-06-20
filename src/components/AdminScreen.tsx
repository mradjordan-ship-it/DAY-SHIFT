import { useState, useEffect } from "react";
import { useAuth, useNav } from "../App";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Users,
  Video,
  Handshake,
  Trash2,
  Shield,
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Flag,
  Ban,
  XCircle,
  MessageCircle,
  Heart,
  Send,
  ArrowLeft,
  Bot,
  User,
  DollarSign,
  Zap,
  HardHat,
  Building2,
  Calendar,
  Tag,
  Pencil,
  X,
  ImageIcon,
  Sparkles,
  Star,
} from "lucide-react";
import { RoleIcon, CategoryIcon } from "./Icons";

interface Stats {
  total_users: number;
  workers: number;
  employers: number;
  total_videos: number;
  total_matches: number;
  pending_matches: number;
  active_matches: number;
  completed_matches: number;
  signups_last_7d: number;
  signups_today: number;
}

interface AdminUser {
  id: number;
  name: string;
  email: string;
  role: string;
  is_admin: boolean;
  is_advertiser: boolean;
  advertiser_agreement_accepted: boolean;
  avg_rating: number | null;
  total_shifts: number;
  avatar_url: string | null;
  created_at: string;
  bio: string | null;
}

interface AdminVideo {
  id: number;
  title: string;
  description: string;
  type: string;
  category: string;
  image_url: string | null;
  video_url: string | null;
  aspect_ratio: string;
  user_id: number;
  user_name: string;
  user_role: string;
  created_at: string;
  likes: number;
  scheduled_at: string | null;
  cuisine_type: string | null;
  pay_rate: string | null;
  hours: string | null;
  experience_level: string | null;
  location: string | null;
  price: string | null;
  event_date: string | null;
  event_time: string | null;
}

interface ScheduledPost {
  id: number;
  title: string;
  description: string;
  type: string;
  category: string;
  scheduled_at: string;
  created_at: string;
  image_url: string | null;
  video_url: string | null;
  user_id: number;
  user_name: string;
  user_role: string;
  is_advertiser: boolean;
}

interface AdminMatch {
  id: number;
  worker_id: number;
  employer_id: number;
  worker_name: string;
  employer_name: string;
  status: string;
  initiated_by: number;
  created_at: string;
}

interface AdminReport {
  id: number;
  reporter_id: number;
  target_type: string;
  target_id: number;
  reason: string;
  comment: string | null;
  status: string;
  admin_action: string | null;
  reporter_name: string;
  target_name: string | null;
  target_detail: string | null;
  created_at: string;
}

type Tab = "overview" | "users" | "videos" | "matches" | "reports" | "sponsors" | "tips" | "scheduled" | "boosts";

export default function AdminScreen() {
  const { user, token } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [videos, setVideos] = useState<AdminVideo[]>([]);
  const [matches, setMatches] = useState<AdminMatch[]>([]);
  const [reports, setReports] = useState<AdminReport[]>([]);
  const [supportThreads, setSupportThreads] = useState<any[]>([]);
  const [sponsorContacts, setSponsorContacts] = useState<any[]>([]);
  const [tips, setTips] = useState<any[]>([]);
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedUser, setExpandedUser] = useState<number | null>(null);
  const [editingVideo, setEditingVideo] = useState<AdminVideo | null>(null);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [editSaving, setEditSaving] = useState(false);

  const fetchSupport = async () => {
    const headers = { Authorization: `Bearer ${token}` };
    const [supRes, spoRes, tipsRes] = await Promise.all([
      fetch("/api/admin/support", { headers }),
      fetch("/api/admin/sponsors", { headers }),
      fetch("/api/admin/tips", { headers }),
    ]);
    if (supRes.ok) setSupportThreads(await supRes.json());
    if (spoRes.ok) setSponsorContacts(await spoRes.json());
    if (tipsRes.ok) setTips(await tipsRes.json());
  };

  useEffect(() => {
    if (!token) return;
    const fetchData = async () => {
      setLoading(true);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [statsRes, usersRes, videosRes, matchesRes, reportsRes, supRes, spoRes, tipsRes, schedRes] = await Promise.all([
          fetch("/api/admin/stats", { headers }),
          fetch("/api/admin/users", { headers }),
          fetch("/api/admin/videos", { headers }),
          fetch("/api/admin/matches", { headers }),
          fetch("/api/admin/reports", { headers }),
          fetch("/api/admin/support", { headers }),
          fetch("/api/admin/sponsors", { headers }),
          fetch("/api/admin/tips", { headers }),
          fetch("/api/admin/scheduled", { headers }),
        ]);
        if (statsRes.ok) setStats(await statsRes.json());
        if (usersRes.ok) setUsers(await usersRes.json());
        if (videosRes.ok) setVideos(await videosRes.json());
        if (matchesRes.ok) setMatches(await matchesRes.json());
        if (reportsRes.ok) setReports(await reportsRes.json());
        if (supRes.ok) setSupportThreads(await supRes.json());
        if (spoRes.ok) setSponsorContacts(await spoRes.json());
        if (tipsRes.ok) setTips(await tipsRes.json());
        if (schedRes.ok) setScheduledPosts(await schedRes.json());
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const deleteUser = async (userId: number) => {
    const res = await fetch(`/api/admin/users/${userId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setUsers((prev) => prev.filter((u) => u.id !== userId));
  };

  const toggleAdmin = async (userId: number, is_admin: boolean) => {
    const res = await fetch(`/api/admin/users/${userId}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ is_admin }),
    });
    if (res.ok) {
      const updated = await res.json();
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, is_admin: updated.is_admin } : u)));
    }
  };

  const toggleAdvertiser = async (userId: number, is_advertiser: boolean) => {
    const res = await fetch(`/api/admin/users/${userId}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ is_advertiser }),
    });
    if (res.ok) {
      const updated = await res.json();
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, is_advertiser: updated.is_advertiser } : u)));
    }
  };

  const deleteVideo = async (videoId: number) => {
    const res = await fetch(`/api/admin/videos/${videoId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setVideos((prev) => prev.filter((v) => v.id !== videoId));
  };

  const boostVideo = async (videoId: number, tier: string, durationDays: number) => {
    const res = await fetch(`/api/admin/boosts`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, tier, duration_days: durationDays }),
    });
    return res.ok;
  };

  const openEditVideo = (video: AdminVideo) => {
    setEditingVideo(video);
    setEditForm({
      title: video.title || "",
      description: video.description || "",
      category: video.category || "general",
      price: video.price || "",
      event_date: video.event_date || "",
      event_time: video.event_time || "",
      aspect_ratio: video.aspect_ratio || "9:16",
      cuisine_type: video.cuisine_type || "",
      pay_rate: video.pay_rate || "",
      hours: video.hours || "",
      experience_level: video.experience_level || "",
      location: video.location || "",
    });
  };

  const saveEditVideo = async () => {
    if (!editingVideo) return;
    setEditSaving(true);
    try {
      const fd = new FormData();
      for (const [k, v] of Object.entries(editForm)) {
        if (v !== undefined && v !== null) fd.append(k, v);
      }
      const res = await fetch(`/api/admin/videos/${editingVideo.id}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (res.ok) {
        const updated = await res.json();
        setVideos((prev) => prev.map((v) => (v.id === editingVideo.id ? { ...v, ...updated } : v)));
        setEditingVideo(null);
      } else {
        alert("Failed to save changes");
      }
    } finally {
      setEditSaving(false);
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-6 text-center">
        <Shield size={48} className="text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Admin access required</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const openReports = reports.filter((r) => r.status === "open").length;
  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "users", label: `Users (${users.length})`, icon: <Users size={14} /> },
    { key: "videos", label: `Videos (${videos.length})`, icon: <Video size={14} /> },
    { key: "matches", label: `Matches (${matches.length})`, icon: <Handshake size={14} /> },
    { key: "reports", label: `Reports${openReports > 0 ? ` (${openReports})` : ""}`, icon: <Flag size={14} /> },
    { key: "tips", label: `Tips${tips.length > 0 ? ` (${tips.length})` : ""}`, icon: <DollarSign size={14} /> },
    { key: "scheduled", label: `Scheduled${scheduledPosts.length > 0 ? ` (${scheduledPosts.length})` : ""}`, icon: <Clock size={14} /> },
    { key: "boosts", label: "Boosts", icon: <Zap size={14} /> },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2 mb-2">
          <Shield size={20} className="text-primary" />
          <h1 className="text-2xl text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>
            Admin Dashboard
          </h1>
          <Badge className="text-[10px] border-0 bg-primary/20 text-primary ml-auto">Overview</Badge>
          {tab !== "overview" && (
            <button onClick={() => setTab("overview")} className="text-muted-foreground hover:text-foreground ml-1">
              <ArrowLeft size={16} />
            </button>
          )}
        </div>
        {tab !== "overview" && (
          <div className="flex gap-1 overflow-x-auto">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all
                  ${tab === t.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {tab === "overview" && stats && <OverviewTab stats={stats} onNavigate={(t) => setTab(t)} />}
        {tab === "users" && (
          <UsersTab
            users={users}
            expandedUser={expandedUser}
            setExpandedUser={setExpandedUser}
            onDelete={deleteUser}
            onToggleAdmin={toggleAdmin}
            onToggleAdvertiser={toggleAdvertiser}
            currentUserId={user.id}
          />
        )}
        {tab === "videos" && <VideosTab videos={videos} onDelete={deleteVideo} onBoost={boostVideo} onEdit={openEditVideo} />}
        {tab === "scheduled" && <ScheduledTab posts={scheduledPosts} />}
        {tab === "matches" && <MatchesTab matches={matches} />}
        {tab === "reports" && (
          <ReportsTab
            reports={reports}
            onReview={async (reportId: number, action: string) => {
              const res = await fetch(`/api/admin/reports/${reportId}`, {
                method: "PATCH",
                headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
                body: JSON.stringify({ action }),
              });
              if (res.ok) {
                setReports((prev) => prev.map((r) => (r.id === reportId ? { ...r, status: "reviewed", admin_action: action } : r)));
              }
            }}
          />
        )}
        {tab === "tips" && <TipsTab tips={tips} onRefresh={fetchSupport} />}
        {tab === "boosts" && <BoostsTab token={token!} />}
      </div>

      {/* Edit Post Dialog */}
      {editingVideo && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="text-lg font-bold text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>
                Edit Post #{editingVideo.id}
              </h3>
              <button onClick={() => setEditingVideo(null)} className="text-muted-foreground hover:text-foreground">
                <X size={20} />
              </button>
            </div>
            <div className="p-4 space-y-3">
              {/* Thumbnail */}
              {(editingVideo.image_url || editingVideo.video_url) && (
                <div className="rounded-lg overflow-hidden bg-black">
                  {editingVideo.image_url ? (
                    <img src={editingVideo.image_url} alt="" className="w-full max-h-40 object-contain" />
                  ) : (
                    <video src={editingVideo.video_url!} className="w-full max-h-40" controls />
                  )}
                </div>
              )}
              <div className="space-y-0.5">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Title</Label>
                <Input value={editForm.title || ""} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} className="bg-secondary border-border h-8 text-sm" />
              </div>
              <div className="space-y-0.5">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Description</Label>
                <Textarea value={editForm.description || ""} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} rows={3} className="bg-secondary border-border text-sm resize-none" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Category</Label>
                  <Select value={editForm.category || "general"} onValueChange={(v) => setEditForm({ ...editForm, category: v })}>
                    <SelectTrigger className="bg-secondary border-border h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="general"><Sparkles size={12} className="inline mr-1" /> General</SelectItem>
                      <SelectItem value="crew"><HardHat size={12} className="inline mr-1" /> Crew</SelectItem>
                      <SelectItem value="kitchen"><Building2 size={12} className="inline mr-1" /> Kitchen</SelectItem>
                      <SelectItem value="sale"><Tag size={12} className="inline mr-1" /> For Sale</SelectItem>
                      <SelectItem value="event"><Calendar size={12} className="inline mr-1" /> Event</SelectItem>
                      <SelectItem value="sponsored"><Star size={12} className="inline mr-1 fill-primary text-primary" /> Sponsored</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Aspect Ratio</Label>
                  <Select value={editForm.aspect_ratio || "9:16"} onValueChange={(v) => setEditForm({ ...editForm, aspect_ratio: v })}>
                    <SelectTrigger className="bg-secondary border-border h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="9:16">9:16</SelectItem>
                      <SelectItem value="4:5">4:5</SelectItem>
                      <SelectItem value="1:1">1:1</SelectItem>
                      <SelectItem value="16:9">16:9</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Location</Label>
                  <Input value={editForm.location || ""} onChange={(e) => setEditForm({ ...editForm, location: e.target.value })} className="bg-secondary border-border h-8 text-sm" />
                </div>
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Pay Rate</Label>
                  <Input value={editForm.pay_rate || ""} onChange={(e) => setEditForm({ ...editForm, pay_rate: e.target.value })} className="bg-secondary border-border h-8 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Cuisine Type</Label>
                  <Input value={editForm.cuisine_type || ""} onChange={(e) => setEditForm({ ...editForm, cuisine_type: e.target.value })} className="bg-secondary border-border h-8 text-sm" />
                </div>
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Hours</Label>
                  <Input value={editForm.hours || ""} onChange={(e) => setEditForm({ ...editForm, hours: e.target.value })} className="bg-secondary border-border h-8 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Experience</Label>
                  <Select value={editForm.experience_level || ""} onValueChange={(v) => setEditForm({ ...editForm, experience_level: v })}>
                    <SelectTrigger className="bg-secondary border-border h-8 text-xs">
                      <SelectValue placeholder="Level" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="entry">Entry Level</SelectItem>
                      <SelectItem value="mid">2–5 Years</SelectItem>
                      <SelectItem value="senior">5+ Years</SelectItem>
                      <SelectItem value="executive">Executive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-0.5">
                  <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Price</Label>
                  <Input value={editForm.price || ""} onChange={(e) => setEditForm({ ...editForm, price: e.target.value })} className="bg-secondary border-border h-8 text-sm" />
                </div>
              </div>
              {(editForm.category === "event" || editingVideo.category === "event") && (
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-0.5">
                    <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Event Date</Label>
                    <Input type="date" value={editForm.event_date || ""} onChange={(e) => setEditForm({ ...editForm, event_date: e.target.value })} className="bg-secondary border-border h-8 text-sm" />
                  </div>
                  <div className="space-y-0.5">
                    <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Event Time</Label>
                    <Input type="time" value={editForm.event_time || ""} onChange={(e) => setEditForm({ ...editForm, event_time: e.target.value })} className="bg-secondary border-border h-8 text-sm" />
                  </div>
                </div>
              )}
              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setEditingVideo(null)} className="flex-1">
                  Cancel
                </Button>
                <Button onClick={saveEditVideo} disabled={editSaving} className="flex-1 bg-primary text-primary-foreground">
                  {editSaving ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: number | string; icon: React.ReactNode; color: string }) {
  return (
    <div className="bg-card border border-border rounded-xl p-3 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>{icon}</div>
      <div>
        <p className="text-2xl font-bold text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>{value}</p>
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
      </div>
    </div>
  );
}

function OverviewTab({ stats, onNavigate }: { stats: Stats; onNavigate: (tab: Tab) => void }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <button onClick={() => onNavigate("users")}>
          <StatCard label="Total Users" value={stats.total_users} icon={<Users size={18} className="text-blue-400" />} color="bg-blue-500/10" />
        </button>
        <button onClick={() => onNavigate("users")}>
          <StatCard label="Crew" value={stats.workers} icon={<Users size={18} className="text-orange-400" />} color="bg-orange-500/10" />
        </button>
        <button onClick={() => onNavigate("users")}>
          <StatCard label="Spots" value={stats.employers} icon={<Users size={18} className="text-blue-400" />} color="bg-blue-500/10" />
        </button>
        <button onClick={() => onNavigate("videos")}>
          <StatCard label="Videos" value={stats.total_videos} icon={<Video size={18} className="text-purple-400" />} color="bg-purple-500/10" />
        </button>
        <button onClick={() => onNavigate("matches")}>
          <StatCard label="Pending" value={stats.pending_matches} icon={<Clock size={18} className="text-yellow-400" />} color="bg-yellow-500/10" />
        </button>
        <button onClick={() => onNavigate("matches")}>
          <StatCard label="Active" value={stats.active_matches} icon={<TrendingUp size={18} className="text-green-400" />} color="bg-green-500/10" />
        </button>
        <button onClick={() => onNavigate("matches")}>
          <StatCard label="Completed" value={stats.completed_matches} icon={<CheckCircle2 size={18} className="text-primary" />} color="bg-primary/10" />
        </button>
        <button onClick={() => onNavigate("matches")}>
          <StatCard label="Total Matches" value={stats.total_matches} icon={<Handshake size={18} className="text-primary" />} color="bg-primary/10" />
        </button>
      </div>

      <div className="bg-card border border-border rounded-xl p-4">
        <h3 className="text-sm font-semibold text-foreground mb-2">Growth</h3>
        <div className="flex gap-4">
          <div className="flex-1 text-center">
            <p className="text-xl font-bold text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>{stats.signups_today}</p>
            <p className="text-[10px] text-muted-foreground">Signups Today</p>
          </div>
          <div className="flex-1 text-center">
            <p className="text-xl font-bold text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>{stats.signups_last_7d}</p>
            <p className="text-[10px] text-muted-foreground">Last 7 Days</p>
          </div>
          <div className="flex-1 text-center">
            <p className="text-xl font-bold text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>
              {stats.total_users > 0 ? ((stats.employers / stats.total_users) * 100).toFixed(0) : 0}%
            </p>
            <p className="text-[10px] text-muted-foreground">Kitchen Ratio</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function UsersTab({
  users,
  expandedUser,
  setExpandedUser,
  onDelete,
  onToggleAdmin,
  onToggleAdvertiser,
  currentUserId,
}: {
  users: AdminUser[];
  expandedUser: number | null;
  setExpandedUser: (id: number | null) => void;
  onDelete: (id: number) => void;
  onToggleAdmin: (id: number, is_admin: boolean) => void;
  onToggleAdvertiser: (id: number, is_advertiser: boolean) => void;
  currentUserId: number;
}) {
  return (
    <div className="space-y-2">
      {users.map((u) => (
        <div key={u.id} className="bg-card border border-border rounded-xl overflow-hidden">
          <button
            onClick={() => setExpandedUser(expandedUser === u.id ? null : u.id)}
            className="w-full flex items-center gap-3 p-3 text-left"
          >
            <div className="w-9 h-9 rounded-full bg-secondary border border-border overflow-hidden flex-shrink-0">
              {u.avatar_url ? (
                <img src={u.avatar_url} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-sm font-bold text-primary">
                  {u.name?.[0]?.toUpperCase()}
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground text-sm truncate">{u.name}</span>
                {u.is_admin && (
                  <Badge className="text-[9px] bg-primary/20 text-primary border-0 px-1.5 py-0">Admin</Badge>
                )}
                {u.is_advertiser && (
                  <Badge className="text-[9px] bg-amber-500/20 text-amber-300 border-0 px-1.5 py-0">✦ Advertiser</Badge>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground truncate">{u.email}</p>
            </div>
            <Badge className={`text-[10px] border-0 ${
              u.role === "admin" ? "bg-purple-500/20 text-purple-300" :
              u.role === "worker" ? "bg-orange-500/20 text-orange-300" : "bg-blue-500/20 text-blue-300"
            }`}>
              <RoleIcon role={u.role as "admin" | "worker" | "employer"} className="w-3 h-3 mr-1" />
              {u.role === "admin" ? "Admin" : u.role === "worker" ? "Crew" : "Kitchen"}
            </Badge>
            {expandedUser === u.id ? <ChevronUp size={16} className="text-muted-foreground" /> : <ChevronDown size={16} className="text-muted-foreground" />}
          </button>

          {expandedUser === u.id && (
            <div className="px-3 pb-3 border-t border-border pt-2 space-y-2">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <p className="text-sm font-bold text-foreground">{u.avg_rating ? Number(u.avg_rating).toFixed(1) : "—"}</p>
                  <p className="text-[9px] text-muted-foreground">Rating</p>
                </div>
                <div>
                  <p className="text-sm font-bold text-foreground">{u.total_shifts}</p>
                  <p className="text-[9px] text-muted-foreground">Shifts</p>
                </div>
                <div>
                  <p className="text-sm font-bold text-foreground">{new Date(u.created_at).toLocaleDateString()}</p>
                  <p className="text-[9px] text-muted-foreground">Joined</p>
                </div>
              </div>
              {u.bio && <p className="text-xs text-muted-foreground">{u.bio}</p>}
              <div className="flex gap-2">
                {u.id !== currentUserId && (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onToggleAdvertiser(u.id, !u.is_advertiser)}
                      className={`text-xs flex-1 ${u.is_advertiser ? "border-amber-500/40 text-amber-400 hover:bg-amber-500/10" : ""}`}
                    >
                      <span className="mr-1">✦</span> {u.is_advertiser ? "Remove Advertiser" : "Make Advertiser"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onDelete(u.id)}
                      className="text-xs text-destructive border-destructive/40 hover:bg-destructive/10"
                    >
                      <Trash2 size={12} />
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function VideosTab({ videos, onDelete, onBoost, onEdit }: { videos: AdminVideo[]; onDelete: (id: number) => void; onBoost: (id: number, tier: string, days: number) => Promise<boolean>; onEdit: (video: AdminVideo) => void }) {
  const [expandedUser, setExpandedUser] = useState<number | null>(null);
  const [boostingVideoId, setBoostingVideoId] = useState<number | null>(null);
  const [boostTier, setBoostTier] = useState<string>("boost");
  const [boostDays, setBoostDays] = useState<number>(1);

  // Group videos by user
  const groupedByUser = videos.reduce((acc, v) => {
    if (!acc[v.user_id]) {
      acc[v.user_id] = {
        user_name: v.user_name,
        user_role: v.user_role,
        videos: [],
      };
    }
    acc[v.user_id].videos.push(v);
    return acc;
  }, {} as Record<number, { user_name: string; user_role: string; videos: AdminVideo[] }>);

  const users = Object.entries(groupedByUser).sort((a, b) => b[1].videos.length - a[1].videos.length);

  const handleBoost = async (videoId: number) => {
    setBoostingVideoId(videoId);
    const success = await onBoost(videoId, boostTier, boostDays);
    setBoostingVideoId(null);
    if (success) {
      alert(`Post boosted for ${boostDays} day${boostDays > 1 ? "s" : ""}!`);
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground mb-2">Grouped by user — tap to expand and see all posts</p>
      {users.map(([userId, data]) => (
        <div key={userId} className="bg-card border border-border rounded-xl overflow-hidden">
          {/* User header row */}
          <button
            onClick={() => setExpandedUser(expandedUser === Number(userId) ? null : Number(userId))}
            className="w-full p-3 flex items-center justify-between hover:bg-secondary/30 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                <User size={14} className="text-primary" />
              </div>
              <div className="text-left">
                <p className="font-semibold text-foreground text-sm">{data.user_name}</p>
                <p className="text-[11px] text-muted-foreground">
                  <RoleIcon role={data.user_role === "worker" ? "worker" : "employer"} className="w-3 h-3 inline mr-1" />
                  {data.user_role === "worker" ? "Crew" : "Kitchen"} · {data.videos.length} post{data.videos.length !== 1 ? "s" : ""}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={`text-[10px] border-0 ${data.user_role === "worker" ? "bg-orange-500/20 text-orange-300" : "bg-blue-500/20 text-blue-300"}`}>
                {data.videos.length} post{data.videos.length !== 1 ? "s" : ""}
              </Badge>
              {expandedUser === Number(userId) ? (
                <ChevronUp size={16} className="text-muted-foreground" />
              ) : (
                <ChevronDown size={16} className="text-muted-foreground" />
              )}
            </div>
          </button>

          {/* Expanded videos list */}
          {expandedUser === Number(userId) && (
            <div className="border-t border-border divide-y divide-border">
              {data.videos.map((v) => (
                <div key={v.id} className="p-3 bg-secondary/20">
                  <div className="flex items-start gap-3">
                    {/* Thumbnail */}
                    {v.image_url ? (
                      <img src={v.image_url} alt="" className="w-16 h-16 rounded-lg object-cover bg-black flex-shrink-0" />
                    ) : v.video_url ? (
                      <div className="w-16 h-16 rounded-lg bg-black flex-shrink-0 flex items-center justify-center text-muted-foreground">
                        <Video size={20} />
                      </div>
                    ) : (
                      <div className="w-16 h-16 rounded-lg bg-secondary flex-shrink-0 flex items-center justify-center text-muted-foreground text-[10px]">
                        Text
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground text-sm truncate">{v.title || "Untitled"}</span>
                        {v.category && (
                          <Badge className="text-[9px] border-0 bg-muted text-muted-foreground">
                            {v.category}
                          </Badge>
                        )}
                      </div>
                      {v.description && (
                        <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5">{v.description}</p>
                      )}
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        {v.location && <span className="text-[10px] text-muted-foreground">📍 {v.location}</span>}
                        {v.pay_rate && <span className="text-[10px] text-muted-foreground">💰 {v.pay_rate}</span>}
                        <span className="text-[10px] text-muted-foreground">{v.likes} likes · {new Date(v.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/50">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onEdit(v)}
                      className="text-xs flex-shrink-0"
                    >
                      <Pencil size={12} className="mr-1" /> Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onDelete(v.id)}
                      className="text-xs text-destructive border-destructive/40 hover:bg-destructive/10 flex-shrink-0"
                    >
                      <Trash2 size={12} />
                    </Button>
                    <div className="flex-1" />
                    <Zap size={12} className="text-amber-400" />
                    <Select value={boostTier} onValueChange={setBoostTier}>
                      <SelectTrigger className="h-7 w-24 text-xs bg-secondary border-border">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="boost">Boost</SelectItem>
                        <SelectItem value="spotlight">Spotlight</SelectItem>
                        <SelectItem value="premium">Premium</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select value={String(boostDays)} onValueChange={(v) => setBoostDays(Number(v))}>
                      <SelectTrigger className="h-7 w-20 text-xs bg-secondary border-border">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1 day</SelectItem>
                        <SelectItem value="3">3 days</SelectItem>
                        <SelectItem value="7">7 days</SelectItem>
                        <SelectItem value="14">14 days</SelectItem>
                        <SelectItem value="30">30 days</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      onClick={() => handleBoost(v.id)}
                      disabled={boostingVideoId === v.id}
                      className="h-7 text-xs bg-amber-500 hover:bg-amber-600 text-white"
                    >
                      {boostingVideoId === v.id ? "..." : "Boost"}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ScheduledTab({ posts }: { posts: ScheduledPost[] }) {
  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + " at " + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  };

  if (posts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Clock size={40} className="text-muted-foreground mb-3" />
        <p className="text-muted-foreground text-sm font-medium">No Scheduled Posts</p>
        <p className="text-muted-foreground/60 text-xs mt-1">Posts scheduled by advertisers will appear here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1"><Clock size={12} /> Posts waiting to go live — sorted by soonest first</p>
      {posts.map((p) => (
        <div key={p.id} className="bg-card border border-border rounded-xl p-3">
          <div className="flex items-start gap-3">
            {/* Thumbnail */}
            {p.image_url ? (
              <img src={p.image_url} alt="" className="w-12 h-12 rounded-lg object-cover bg-black flex-shrink-0" />
            ) : p.video_url ? (
              <div className="w-12 h-12 rounded-lg bg-black flex-shrink-0 flex items-center justify-center text-muted-foreground">
                <Video size={16} />
              </div>
            ) : (
              <div className="w-12 h-12 rounded-lg bg-secondary flex-shrink-0 flex items-center justify-center text-muted-foreground text-[10px]">
                Text
              </div>
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-foreground text-sm truncate">{p.title || "Untitled"}</span>
                {p.category === "sale" && (
                  <Badge className="text-[9px] border-0 bg-emerald-500/20 text-emerald-300 px-1.5 py-0"><Tag size={10} className="inline mr-0.5" /> Sale</Badge>
                )}
                {p.category === "event" && (
                  <Badge className="text-[9px] border-0 bg-violet-500/20 text-violet-300 px-1.5 py-0"><Calendar size={10} className="inline mr-0.5" /> Event</Badge>
                )}
                {p.is_advertiser && (
                  <Badge className="text-[9px] border-0 bg-amber-500/20 text-amber-300 px-1.5 py-0">✦ Advertiser</Badge>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                by {p.user_name} ({p.user_role === "worker" ? "Crew" : "Kitchen"})
              </p>
              <p className="text-[11px] text-muted-foreground truncate mt-0.5">{p.description}</p>
              <div className="flex items-center gap-1 mt-1.5">
                <Clock size={11} className="text-primary" />
                <span className="text-[11px] font-semibold text-primary">{formatDate(p.scheduled_at)}</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function MatchesTab({ matches }: { matches: AdminMatch[] }) {
  const statusColors: Record<string, string> = {
    pending: "bg-yellow-500/20 text-yellow-300",
    active: "bg-green-500/20 text-green-300",
    completed: "bg-primary/20 text-primary",
    cancelled: "bg-destructive/20 text-destructive",
  };
  return (
    <div className="space-y-2">
      {matches.map((m) => (
        <div key={m.id} className="bg-card border border-border rounded-xl p-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-foreground">
                <HardHat size={12} className="inline mr-1" />{m.worker_name} ↔ <Building2 size={12} className="inline mx-1" />{m.employer_name}
              </p>
              <p className="text-[11px] text-muted-foreground">
                ID: {m.id} · {new Date(m.created_at).toLocaleDateString()}
              </p>
            </div>
            <Badge className={`text-[10px] border-0 ${statusColors[m.status] || "bg-muted text-muted-foreground"}`}>
              {m.status}
            </Badge>
          </div>
        </div>
      ))}
    </div>
  );
}

const REASON_LABELS: Record<string, string> = {
  harassment: "Harassment or Hate Speech",
  spam: "Spam or Misleading",
  inappropriate: "Inappropriate Content",
  fake: "Fake or Fraudulent",
  other: "Other",
};

function ReportsTab({
  reports,
  onReview,
}: {
  reports: AdminReport[];
  onReview: (reportId: number, action: string) => void;
}) {
  const openReports = reports.filter((r) => r.status === "open");
  const closedReports = reports.filter((r) => r.status !== "open");

  return (
    <div className="space-y-4">
      {openReports.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
            <AlertTriangle size={14} className="text-yellow-400" /> Open Reports ({openReports.length})
          </h3>
          <div className="space-y-2">
            {openReports.map((r) => (
              <div key={r.id} className="bg-card border border-yellow-500/30 rounded-xl p-3">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {r.target_type === "user" ? "👤" : "🎬"} {r.target_name || `#${r.target_id}`}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Reported by {r.reporter_name} · {REASON_LABELS[r.reason] || r.reason}
                    </p>
                  </div>
                  <Badge className="text-[10px] border-0 bg-yellow-500/20 text-yellow-300">Open</Badge>
                </div>
                {r.comment && (
                  <p className="text-xs text-muted-foreground bg-secondary rounded-lg px-3 py-1.5 mb-2">"{r.comment}"</p>
                )}
                <p className="text-[10px] text-muted-foreground mb-2">{new Date(r.created_at).toLocaleString()}</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => onReview(r.id, "dismiss")} className="text-xs flex-1">
                    <XCircle size={12} className="mr-1" /> Dismiss
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => onReview(r.id, "warn")} className="text-xs flex-1 border-yellow-500/40 text-yellow-400 hover:bg-yellow-500/10">
                    <AlertTriangle size={12} className="mr-1" /> Warn
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => onReview(r.id, "remove_content")} className="text-xs flex-1 border-orange-500/40 text-orange-400 hover:bg-orange-500/10">
                    <Trash2 size={12} className="mr-1" /> Remove
                  </Button>
                  <Button size="sm" onClick={() => onReview(r.id, "suspend")} className="text-xs flex-1 bg-destructive text-destructive-foreground hover:bg-destructive/90">
                    <Ban size={12} className="mr-1" /> Suspend
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {closedReports.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-2 text-muted-foreground">Reviewed ({closedReports.length})</h3>
          <div className="space-y-2">
            {closedReports.map((r) => (
              <div key={r.id} className="bg-card border border-border rounded-xl p-3 opacity-60">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-foreground">
                      {r.target_type === "user" ? "👤" : "🎬"} {r.target_name || `#${r.target_id}`}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      {REASON_LABELS[r.reason] || r.reason} → Action: {r.admin_action || "none"}
                    </p>
                  </div>
                  <Badge className="text-[10px] border-0 bg-green-500/20 text-green-300">Reviewed</Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {reports.length === 0 && (
        <div className="text-center py-12">
          <Flag size={32} className="text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">No reports yet</p>
        </div>
      )}
    </div>
  );
}

// ── Support Inbox Tab ────────────────────────────────────────────────────────

function SupportTab({ threads, token, onRefresh }: { threads: any[]; token: string; onRefresh: () => void }) {
  const [activeThread, setActiveThread] = useState<number | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);

  const openThread = async (threadId: number) => {
    setActiveThread(threadId);
    const res = await fetch(`/api/support/${threadId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setMessages(await res.json());
  };

  const handleReply = async () => {
    if (!replyText.trim() || !activeThread) return;
    setSending(true);
    try {
      const res = await fetch(`/api/support/${activeThread}/reply`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ message: replyText }),
      });
      if (res.ok) {
        const msg = await res.json();
        setMessages((prev) => [...prev, msg]);
        setReplyText("");
        onRefresh();
      }
    } finally {
      setSending(false);
    }
  };

  const handleClose = async (threadId: number) => {
    const res = await fetch(`/api/admin/support/${threadId}/close`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      setActiveThread(null);
      onRefresh();
    }
  };

  // Chat view
  if (activeThread !== null) {
    const thread = threads.find((t: any) => t.id === activeThread);
    return (
      <div className="flex flex-col" style={{ minHeight: "calc(100vh - 280px)" }}>
        <div className="flex items-center gap-2 mb-3">
          <button onClick={() => setActiveThread(null)} className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
            <ArrowLeft size={16} />
          </button>
          <div className="flex-1 min-w-0">
            <p className="text-foreground font-semibold text-sm truncate">{thread?.subject || "Support"}</p>
            <p className="text-muted-foreground text-[10px]">
              {thread?.user_name} · {thread?.user_email}
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleClose(activeThread)}
            className="text-xs text-destructive border-destructive/40 hover:bg-destructive/10"
          >
            Close
          </Button>
        </div>

        <div className="flex-1 space-y-3 mb-4">
          {messages.map((m: any) => {
            const isAdmin = m.sender_role === "admin";
            const isAuto = m.sender_role === "auto";
            return (
              <div key={m.id} className={`flex gap-2 ${isAdmin ? "justify-end" : "justify-start"}`}>
                {!isAdmin && (
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${isAuto ? "bg-primary/20" : "bg-secondary"}`}>
                    {isAuto ? <Bot size={14} className="text-primary" /> : <User size={14} className="text-muted-foreground" />}
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${
                    isAdmin
                      ? "bg-primary text-primary-foreground rounded-br-md"
                      : isAuto
                      ? "bg-primary/10 border border-primary/20 rounded-bl-md"
                      : "bg-card border border-border rounded-bl-md"
                  }`}
                >
                  {!isAdmin && (
                    <p className={`text-[10px] font-semibold mb-0.5 ${isAuto ? "text-primary" : "text-foreground"}`}>
                      {isAuto ? "Auto-Reply" : m.sender_name}
                    </p>
                  )}
                  {isAdmin && (
                    <p className="text-[10px] font-semibold mb-0.5 text-primary-foreground/80">You</p>
                  )}
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
                  <p className={`text-[10px] mt-1 ${isAdmin ? "text-primary-foreground/60" : "text-muted-foreground"}`}>
                    {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
                {isAdmin && (
                  <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                    <Shield size={14} className="text-primary-foreground" />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="sticky bottom-0 bg-background pt-2">
          <div className="flex gap-2">
            <input
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Reply as admin…"
              className="flex-1 bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleReply();
                }
              }}
            />
            <Button
              onClick={handleReply}
              disabled={!replyText.trim() || sending}
              size="icon"
              className="bg-primary text-primary-foreground flex-shrink-0"
            >
              <Send size={16} />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Thread list
  const openThreads = threads.filter((t: any) => t.status === "open");
  const closedThreads = threads.filter((t: any) => t.status === "closed");

  return (
    <div className="space-y-4">
      {openThreads.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-1">
            <MessageCircle size={14} className="text-primary" /> Open ({openThreads.length})
          </h3>
          <div className="space-y-2">
            {openThreads.map((t: any) => (
              <button
                key={t.id}
                onClick={() => openThread(t.id)}
                className="w-full bg-card border border-primary/20 rounded-xl p-3 text-left hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center text-[10px] font-bold text-primary">
                      {t.user_name?.[0]?.toUpperCase()}
                    </div>
                    <span className="text-foreground font-semibold text-sm">{t.user_name}</span>
                  </div>
                  <Badge className="text-[10px] border-0 bg-green-500/20 text-green-300">Open</Badge>
                </div>
                <p className="text-foreground text-xs font-medium">{t.subject}</p>
                {t.last_message && <p className="text-muted-foreground text-[11px] line-clamp-1 mt-0.5">{t.last_message}</p>}
                <div className="flex items-center gap-2 mt-1 text-muted-foreground/60 text-[10px]">
                  <span>{t.user_email}</span>
                  <span>·</span>
                  <span>{new Date(t.updated_at).toLocaleDateString()}</span>
                  {t.admin_replies === 0 && <Badge className="text-[9px] border-0 bg-yellow-500/20 text-yellow-300 ml-1">Unanswered</Badge>}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {closedThreads.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-2">Closed ({closedThreads.length})</h3>
          <div className="space-y-2">
            {closedThreads.map((t: any) => (
              <button
                key={t.id}
                onClick={() => openThread(t.id)}
                className="w-full bg-card border border-border rounded-xl p-3 text-left opacity-60 hover:opacity-80 transition-opacity"
              >
                <div className="flex items-center justify-between">
                  <span className="text-foreground text-sm font-semibold">{t.user_name} — {t.subject}</span>
                  <Badge className="text-[10px] border-0 bg-muted text-muted-foreground">Closed</Badge>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {threads.length === 0 && (
        <div className="text-center py-12">
          <MessageCircle size={32} className="text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">No support messages yet</p>
        </div>
      )}
    </div>
  );
}

// ── Sponsors Tab ─────────────────────────────────────────────────────────────

function SponsorsTab({ contacts, token, onRefresh }: { contacts: any[]; token: string; onRefresh: () => void }) {
  const [activeId, setActiveId] = useState<number | null>(null);
  const [replies, setReplies] = useState<any[]>([]);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);

  const openContact = async (id: number) => {
    setActiveId(id);
    const res = await fetch(`/api/admin/sponsors/${id}/replies`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setReplies(await res.json());
  };

  const handleReply = async () => {
    if (!replyText.trim() || !activeId) return;
    setSending(true);
    try {
      const res = await fetch(`/api/admin/sponsors/${activeId}/replies`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ content: replyText }),
      });
      if (res.ok) {
        const msg = await res.json();
        setReplies((prev) => [...prev, msg]);
        setReplyText("");
        onRefresh();
      }
    } finally {
      setSending(false);
    }
  };

  const typeColors: Record<string, string> = {
    sponsor: "bg-blue-500/20 text-blue-300",
    donor: "bg-green-500/20 text-green-300",
    supporter: "bg-purple-500/20 text-purple-300",
    other: "bg-muted text-muted-foreground",
  };

  // Chat view for a specific sponsor contact
  if (activeId !== null) {
    const contact = contacts.find((c: any) => c.id === activeId);
    return (
      <div className="flex flex-col" style={{ minHeight: "calc(100vh - 280px)" }}>
        <div className="flex items-center gap-2 mb-3">
          <button onClick={() => setActiveId(null)} className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
            <ArrowLeft size={16} />
          </button>
          <div className="flex-1 min-w-0">
            <p className="text-foreground font-semibold text-sm truncate">{contact?.name}</p>
            <p className="text-muted-foreground text-[10px]">{contact?.email}{contact?.organization ? ` · ${contact.organization}` : ""}</p>
          </div>
          <Badge className={`text-[10px] border-0 ${typeColors[contact?.type] || typeColors.other}`}>{contact?.type}</Badge>
        </div>

        {/* Original message */}
        <div className="flex gap-2 mb-3">
          <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
            <User size={14} className="text-muted-foreground" />
          </div>
          <div className="bg-card border border-border rounded-2xl rounded-bl-md px-4 py-2.5 max-w-[85%]">
            <p className="text-[10px] font-semibold text-foreground mb-0.5">{contact?.name}</p>
            <p className="text-sm whitespace-pre-wrap leading-relaxed">{contact?.message}</p>
            <p className="text-muted-foreground text-[10px] mt-1">{new Date(contact?.created_at).toLocaleString()}</p>
          </div>
        </div>

        {/* Replies */}
        {replies.map((r: any) => (
          <div key={r.id} className="flex gap-2 mb-3 justify-end">
            <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-2.5 max-w-[85%]">
              <p className="text-[10px] font-semibold text-primary-foreground/80 mb-0.5">You</p>
              <p className="text-sm whitespace-pre-wrap leading-relaxed">{r.content}</p>
              <p className="text-primary-foreground/60 text-[10px] mt-1">{new Date(r.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>
            </div>
            <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
              <Shield size={14} className="text-primary-foreground" />
            </div>
          </div>
        ))}

        <div className="flex-1" />

        {/* Reply input */}
        <div className="sticky bottom-0 bg-background pt-2">
          <div className="flex gap-2">
            <input
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Reply to this contact…"
              className="flex-1 bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleReply();
                }
              }}
            />
            <Button
              onClick={handleReply}
              disabled={!replyText.trim() || sending}
              size="icon"
              className="bg-primary text-primary-foreground flex-shrink-0"
            >
              <Send size={16} />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Contact list
  return (
    <div className="space-y-2">
      {contacts.map((c: any) => (
        <button
          key={c.id}
          onClick={() => openContact(c.id)}
          className="w-full bg-card border border-border rounded-xl p-3 text-left hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Heart size={14} className="text-primary" />
              <span className="text-foreground font-semibold text-sm">{c.name}</span>
              {c.organization && <span className="text-muted-foreground text-xs">· {c.organization}</span>}
              {c.phone && <span className="text-muted-foreground text-xs">· {c.phone}</span>}
            </div>
            <div className="flex items-center gap-1.5">
              {c.reply_count > 0 && (
                <Badge className="text-[10px] border-0 bg-primary/20 text-primary">{c.reply_count} {c.reply_count === 1 ? "reply" : "replies"}</Badge>
              )}
              {c.reply_count === 0 && (
                <Badge className="text-[10px] border-0 bg-yellow-500/20 text-yellow-300">Unanswered</Badge>
              )}
              <Badge className={`text-[10px] border-0 ${typeColors[c.type] || typeColors.other}`}>{c.type}</Badge>
            </div>
          </div>
          <p className="text-muted-foreground text-xs">{c.email}</p>
          {c.message && <p className="text-foreground text-sm mt-1 line-clamp-2">{c.message}</p>}
          <p className="text-muted-foreground/60 text-[10px] mt-1">{new Date(c.created_at).toLocaleDateString()}</p>
        </button>
      ))}
      {contacts.length === 0 && (
        <div className="text-center py-12">
          <Heart size={32} className="text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">No sponsor/donor contacts yet</p>
        </div>
      )}
    </div>
  );
}

function TipsTab({ tips, onRefresh }: { tips: any[]; onRefresh: () => void }) {
  const { token } = useAuth();
  const totalCents = tips.reduce((sum: number, t: any) => sum + (t.amount || 0), 0);
  const completedCents = tips.filter((t: any) => t.status === "completed").reduce((sum: number, t: any) => sum + (t.amount || 0), 0);

  const markCompleted = async (tipId: number) => {
    const res = await fetch(`/api/admin/tips/${tipId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ status: "completed" }),
    });
    if (res.ok) onRefresh();
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-card border border-border rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>${(totalCents / 100).toFixed(0)}</p>
          <p className="text-[10px] text-muted-foreground">Total Tips</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-primary" style={{ fontFamily: "'Bebas Neue'" }}>${(completedCents / 100).toFixed(0)}</p>
          <p className="text-[10px] text-muted-foreground">Completed</p>
        </div>
      </div>

      <div className="space-y-2">
        {tips.map((t: any) => (
          <div key={t.id} className="bg-card border border-border rounded-xl p-3 flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-amber-500/10 flex items-center justify-center flex-shrink-0">
              <DollarSign size={16} className="text-amber-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground text-sm">${(t.amount / 100).toFixed(0)}</span>
                <Badge className={`text-[9px] border-0 ${t.status === "completed" ? "bg-green-500/20 text-green-300" : t.status === "pending" ? "bg-amber-500/20 text-amber-300" : "bg-red-500/20 text-red-300"}`}>
                  {t.status}
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground truncate">{t.name || t.email || "Anonymous"}</p>
              {t.message && <p className="text-[10px] text-muted-foreground truncate mt-0.5">"{t.message}"</p>}
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-[10px] text-muted-foreground">{new Date(t.created_at).toLocaleDateString()}</p>
              {t.status === "pending" && (
                <Button size="sm" variant="outline" className="text-[10px] h-6 mt-1" onClick={() => markCompleted(t.id)}>
                  Mark Done
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
      {tips.length === 0 && (
        <div className="text-center py-12">
          <DollarSign size={32} className="text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">No tips yet</p>
        </div>
      )}
    </div>
  );
}

function BoostsTab({ token }: { token: string }) {
  const [boosts, setBoosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actioning, setActioning] = useState<number | null>(null);

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` };
    fetch("/api/admin/boosts", { headers })
      .then((r) => (r.ok ? r.json() : []))
      .then(setBoosts)
      .finally(() => setLoading(false));
  }, [token]);

  const handleAction = async (boostId: number, action: "approve" | "reject") => {
    setActioning(boostId);
    await fetch(`/api/admin/boosts/${boostId}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    setBoosts((prev) => prev.map((b) => (b.id === boostId ? { ...b, status: action === "approve" ? "active" : "rejected" } : b)));
    setActioning(null);
  };

  const pending = boosts.filter((b) => b.status === "pending");
  const active = boosts.filter((b) => b.status === "active");
  const other = boosts.filter((b) => !["pending", "active"].includes(b.status));

  const tierColors: Record<string, string> = {
    boost: "bg-green-500/20 text-green-300",
    spotlight: "bg-amber-500/20 text-amber-300",
    premium: "bg-purple-500/20 text-purple-300",
  };
  const tierPrices: Record<string, number> = { boost: 25, spotlight: 75, premium: 150 };

  if (loading) {
    return <div className="flex items-center justify-center h-32"><div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" /></div>;
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">Manage advertiser post boosts. Payments via Stripe.</p>

      {pending.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
            <Clock size={14} className="text-amber-400" /> Pending ({pending.length})
          </h3>
          {pending.map((b: any) => (
            <div key={b.id} className="bg-card border border-border rounded-xl p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Badge className={`text-[10px] border-0 ${tierColors[b.tier] || "bg-muted"}`}>{b.tier}</Badge>
                <span className="text-foreground font-semibold text-sm flex-1 truncate">{b.video_title || "Post"}</span>
                <span className="text-foreground font-bold">${tierPrices[b.tier] || "?"}</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                <span>{b.user_name}</span>
                <span>·</span>
                <span>{new Date(b.created_at).toLocaleDateString()}</span>
                <Badge className={`text-[9px] border-0 ${b.payment_status === "paid" ? "bg-green-500/20 text-green-300" : "bg-amber-500/20 text-amber-300"}`}>
                  {b.payment_status === "paid" ? "✓ Paid" : "⏳ Not paid"}
                </Badge>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleAction(b.id, "approve")} disabled={actioning === b.id || b.payment_status !== "paid"} className="flex-1 bg-green-600 text-white text-xs">
                  {actioning === b.id ? "..." : "✓ Approve"}
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleAction(b.id, "reject")} disabled={actioning === b.id} className="flex-1 text-xs text-destructive">
                  ✕ Reject
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {active.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
            <CheckCircle2 size={14} className="text-green-400" /> Active ({active.length})
          </h3>
          {active.map((b: any) => (
            <div key={b.id} className="bg-card border border-green-500/20 rounded-xl p-3 flex items-center gap-3">
              <Badge className={`text-[10px] border-0 ${tierColors[b.tier] || "bg-muted"}`}>{b.tier}</Badge>
              <div className="flex-1 min-w-0">
                <p className="text-foreground text-sm font-semibold truncate">{b.video_title || "Post"}</p>
                <p className="text-muted-foreground text-[10px]">{b.user_name} · expires {b.end_date ? new Date(b.end_date).toLocaleDateString() : "?"}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {other.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
            <XCircle size={14} className="text-muted-foreground" /> Past ({other.length})
          </h3>
          {other.slice(0, 10).map((b: any) => (
            <div key={b.id} className="bg-card border border-border rounded-xl p-3 flex items-center gap-3">
              <Badge className={`text-[10px] border-0 bg-muted text-muted-foreground`}>{b.tier}</Badge>
              <div className="flex-1 min-w-0">
                <p className="text-muted-foreground text-xs truncate">{b.video_title || "Post"}</p>
              </div>
              <Badge className="text-[9px] border-0 bg-muted text-muted-foreground">{b.status}</Badge>
            </div>
          ))}
        </div>
      )}

      {boosts.length === 0 && (
        <div className="text-center py-12">
          <Zap size={32} className="text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">No boosts yet</p>
        </div>
      )}
    </div>
  );
}
