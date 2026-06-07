import { useState, useEffect } from "react";
import { useAuth, useNav } from "../App";
import { ArrowLeft, Eye, MousePointerClick, Handshake, TrendingUp, Clock, BarChart3, Building2 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface AnalyticsData {
  total_views: number;
  total_clicks: number;
  total_matches: number;
  active_boosts: Array<{
    id: number;
    tier: string;
    start_date: string;
    end_date: string;
    video_title: string;
  }>;
  per_post: Array<{
    video_id: number;
    title: string | null;
    thumbnail_url: string;
    views: number;
    clicks: number;
    matches: number;
  }>;
}

export default function AnalyticsScreen() {
  const { user, token } = useAuth();
  const { navigate } = useNav();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    fetch("/api/advertiser/analytics", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.ok ? r.json() : null)
      .then(setData)
      .finally(() => setLoading(false));
  }, [token]);

  if (!user?.is_advertiser) {
    return (
      <div className="h-full bg-black flex flex-col items-center justify-center p-6 text-center">
        <BarChart3 size={40} className="text-white/20 mb-3" />
        <p className="text-white/40 text-sm">Analytics available for advertisers</p>
        <button onClick={() => navigate("feed")} className="mt-3 px-4 py-2 bg-white/10 text-white rounded-lg text-xs">Back to Feed</button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="h-full bg-black flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const chartData = (data?.per_post || []).slice(0, 10).map((p) => ({
    name: (p.title || "Post").slice(0, 15),
    views: p.views,
    clicks: p.clicks,
    matches: p.matches,
  }));

  return (
    <div className="h-full bg-black overflow-y-auto">
      <div className="p-4">
        <button onClick={() => navigate("boost")} className="flex items-center gap-2 text-muted-foreground mb-4">
          <ArrowLeft size={16} /> Back to Boosts
        </button>
        <h1 className="text-2xl text-white mb-1" style={{ fontFamily: "'Bebas Neue'" }}>Analytics</h1>
        <p className="text-white/50 text-xs mb-6">Your post performance at a glance</p>

        {/* Stats cards */}
        <div className="grid grid-cols-3 gap-2 mb-6">
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
            <Eye size={16} className="text-blue-400 mx-auto mb-1" />
            <p className="text-white text-lg font-bold">{data?.total_views || 0}</p>
            <p className="text-white/40 text-[10px]">Views</p>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
            <MousePointerClick size={16} className="text-green-400 mx-auto mb-1" />
            <p className="text-white text-lg font-bold">{data?.total_clicks || 0}</p>
            <p className="text-white/40 text-[10px]">Clicks</p>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
            <Handshake size={16} className="text-amber-400 mx-auto mb-1" />
            <p className="text-white text-lg font-bold">{data?.total_matches || 0}</p>
            <p className="text-white/40 text-[10px]">Matches</p>
          </div>
        </div>

        {/* Active boosts */}
        {data?.active_boosts && data.active_boosts.length > 0 && (
          <div className="mb-6">
            <p className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-2">Active Boosts</p>
            <div className="space-y-2">
              {data.active_boosts.map((b) => {
                const daysLeft = b.end_date ? Math.max(0, Math.ceil((new Date(b.end_date).getTime() - Date.now()) / 86400000)) : 0;
                return (
                  <div key={b.id} className="bg-green-500/10 border border-green-500/20 rounded-xl p-3 flex items-center gap-3">
                    <TrendingUp size={14} className="text-green-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-semibold truncate">{b.video_title || "Post"}</p>
                      <p className="text-white/40 text-[10px]">{b.tier}</p>
                    </div>
                    <div className="flex items-center gap-1 text-white/60 text-xs">
                      <Clock size={10} /> {daysLeft}d left
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Chart */}
        {chartData.length > 0 && (
          <div className="mb-6">
            <p className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-2">Views by Post</p>
            <div className="bg-white/5 border border-white/10 rounded-xl p-3" style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }} />
                  <YAxis tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }} />
                  <Tooltip
                    contentStyle={{ background: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: "#fff" }}
                  />
                  <Bar dataKey="views" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Per-post breakdown */}
        <p className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-2">Post Breakdown</p>
        {data?.per_post && data.per_post.length > 0 ? (
          <div className="space-y-2">
            {data.per_post.map((post) => (
              <div key={post.video_id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-secondary overflow-hidden flex-shrink-0">
                  {post.thumbnail_url ? (
                    <img src={post.thumbnail_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Building2 size={14} className="text-muted-foreground" />
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-xs font-semibold truncate">{post.title || "Untitled"}</p>
                </div>
                <div className="flex items-center gap-3 text-[10px]">
                  <span className="text-white/50"><Eye size={10} className="inline mr-0.5" />{post.views}</span>
                  <span className="text-white/50"><MousePointerClick size={10} className="inline mr-0.5" />{post.clicks}</span>
                  <span className="text-white/50"><Handshake size={10} className="inline mr-0.5" />{post.matches}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <BarChart3 size={32} className="text-white/10 mx-auto mb-2" />
            <p className="text-white/30 text-sm">No data yet. Boost a post to start tracking!</p>
          </div>
        )}
      </div>
    </div>
  );
}
