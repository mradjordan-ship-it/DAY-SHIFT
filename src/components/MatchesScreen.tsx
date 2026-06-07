import { useState, useEffect } from "react";
import type { Match } from "../types";
import { useAuth, useNav } from "../App";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Clock, MessageCircle, Star, XCircle, CarFront, HardHat, Building2, Hourglass, Sparkles } from "lucide-react";

export default function MatchesScreen() {
  const { user, token } = useAuth();
  const { navigate } = useNav();
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"pending" | "active" | "completed">("pending");
  const [confirming, setConfirming] = useState<number | null>(null);

  useEffect(() => {
    if (!token) return;
    const fetchMatches = async () => {
      setLoading(true);
      try {
        const res = await fetch("/api/matches", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          setMatches(await res.json());
        }
      } finally {
        setLoading(false);
      }
    };
    fetchMatches();
  }, [token]);

  const handleAccept = async (matchId: number) => {
    setConfirming(matchId);
    try {
      const res = await fetch(`/api/matches/${matchId}/accept`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMatches((prev) =>
          prev.map((m) => (m.id === matchId ? { ...m, status: "active" } : m))
        );
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Failed to accept match.");
      }
    } finally {
      setConfirming(null);
    }
  };

  const handleDecline = async (matchId: number) => {
    setConfirming(matchId);
    try {
      const res = await fetch(`/api/matches/${matchId}/decline`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMatches((prev) => prev.filter((m) => m.id !== matchId));
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Failed to decline match.");
      }
    } finally {
      setConfirming(null);
    }
  };

  const handleConfirmComplete = async (matchId: number) => {
    setConfirming(matchId);
    try {
      const res = await fetch(`/api/matches/${matchId}/confirm`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMatches((prev) =>
        prev.map((m) =>
          m.id === matchId
            ? {
                ...m,
                ...(user?.id === m.worker_id
                  ? { worker_confirmed: true }
                  : { employer_confirmed: true }),
              }
            : m
        )
      );
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Failed to confirm match.");
      }
    } finally {
      setConfirming(null);
    }
  };

  const handleCancel = async (matchId: number) => {
    setConfirming(matchId);
    try {
      const res = await fetch(`/api/matches/${matchId}/cancel`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMatches((prev) => prev.filter((m) => m.id !== matchId));
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Failed to cancel match.");
      }
    } finally {
      setConfirming(null);
    }
  };

  const filtered = matches.filter((m) => m.status === tab);

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-6 text-center">
        <p className="text-muted-foreground">Sign in to see your matches</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="p-4 border-b border-border">
        <h1 className="text-2xl text-foreground mb-3" style={{ fontFamily: "'Bebas Neue'" }}>
          Your Matches
        </h1>
        <div className="flex gap-1">
          {(["pending", "active", "completed"] as const).map((t) => {
            const count = matches.filter((m) => m.status === t).length;
            return (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all flex items-center justify-center gap-1
                  ${tab === t ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
              >
                {t === "pending" && <Clock size={11} />}
                {t === "active" && <MessageCircle size={11} />}
                {t === "completed" && <CheckCircle2 size={11} />}
                {t}
                {count > 0 && (
                  <span className={`rounded-full px-1.5 text-[10px] ${tab === t ? "bg-primary-foreground/20" : "bg-muted"}`}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center p-6">
            <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center mb-3">
              {tab === "pending" ? (
                <Hourglass className="w-7 h-7 text-primary" />
              ) : tab === "active" ? (
                <MessageCircle className="w-7 h-7 text-primary" />
              ) : (
                <CheckCircle2 className="w-7 h-7 text-primary" />
              )}
            </div>
            <p className="text-muted-foreground text-sm">
              No {tab} matches yet
            </p>
            {tab === "pending" && (
              <p className="text-muted-foreground text-xs mt-1">
                Browse the feed and connect with {user.role === "worker" ? "spots" : "crew"}
              </p>
            )}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                currentUser={user}
                onChat={() => navigate("chat", { matchId: match.id })}
                onAccept={() => handleAccept(match.id)}
                onDecline={() => handleDecline(match.id)}
                onCancel={() => handleCancel(match.id)}
                onConfirm={() => handleConfirmComplete(match.id)}
                onReview={(revieweeId, name) =>
                  navigate("review", { matchId: match.id, revieweeId, revieweeName: name })
                }
                onProfile={(uid) => navigate("user-profile", { userId: uid })}
                confirming={confirming === match.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MatchCard({
  match,
  currentUser,
  onChat,
  onAccept,
  onDecline,
  onCancel,
  onConfirm,
  onReview,
  onProfile,
  confirming,
}: {
  match: Match;
  currentUser: import("../types").User;
  onChat: () => void;
  onAccept: () => void;
  onDecline: () => void;
  onCancel: () => void;
  onConfirm: () => void;
  onReview: (revieweeId: number, name: string) => void;
  onProfile: (uid: number) => void;
  confirming: boolean;
}) {
  const isWorker = currentUser.id === match.worker_id;
  const otherName = isWorker ? match.employer_name : match.worker_name;
  const otherAvatar = isWorker ? match.employer_avatar : match.worker_avatar;
  const otherId = isWorker ? match.employer_id : match.worker_id;

  const myConfirmed = isWorker ? match.worker_confirmed : match.employer_confirmed;
  const theirConfirmed = isWorker ? match.employer_confirmed : match.worker_confirmed;

  const isInitiator = match.initiated_by === currentUser.id;

  const statusConfig = {
    pending: { color: "bg-yellow-500/20 text-yellow-400", label: "Pending" },
    active: { color: "bg-green-500/20 text-green-400", label: "Active" },
    completed: { color: "bg-primary/20 text-primary", label: "Completed" },
    cancelled: { color: "bg-destructive/20 text-destructive", label: "Cancelled" },
  };

  const sc = statusConfig[match.status];

  const handleRide = () => {
    if (!match.employer_location) return;
    const loc = encodeURIComponent(match.employer_location);
    // Use deep links that fallback to the mobile web sites if apps aren't installed
    const uberUrl = `https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]=${loc}`;
    const lyftUrl = `https://ride.lyft.com/?destination[address]=${loc}`;
    
    // Quick custom action sheet logic
    if (window.confirm(`Need a ride to: ${match.employer_location}?\n\nOK for Uber, Cancel for Lyft.`)) {
      window.open(uberUrl, "_blank");
    } else {
      window.open(lyftUrl, "_blank");
    }
  };

  return (
    <div className="p-4">
      <div className="flex items-center gap-3 mb-3">
        <button
          className="w-12 h-12 rounded-full bg-secondary border border-border overflow-hidden flex-shrink-0"
          onClick={() => onProfile(otherId)}
        >
          {otherAvatar ? (
            <img src={otherAvatar} alt="" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center font-bold text-primary">
              {otherName?.[0]?.toUpperCase()}
            </div>
          )}
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <p className="font-semibold text-foreground">{otherName}</p>
            <Badge className={`text-[10px] border-0 ${sc.color}`}>{sc.label}</Badge>
          </div>
          <p className="text-muted-foreground text-xs">
            {isWorker ? (
              <><Building2 size={12} className="inline mr-1" /> Kitchen</>
            ) : (
              <><HardHat size={12} className="inline mr-1" /> Crew</>
            )} · {isInitiator ? "You reached out" : "Reached out to you"}
          </p>
        </div>
      </div>

      {/* Actions based on status */}
      <div className="flex gap-2">
        {match.status === "pending" && !isInitiator && (
          <>
            <Button
              size="sm"
              onClick={onAccept}
              disabled={confirming}
              className="flex-1 bg-primary text-primary-foreground ember-glow text-xs"
            >
              {confirming ? "..." : "Accept"}
            </Button>
            <Button
              size="sm"
              onClick={onDecline}
              disabled={confirming}
              variant="outline"
              className="flex-none text-xs text-destructive border-destructive/40 hover:bg-destructive/10"
            >
              Decline
            </Button>
          </>
        )}

        {match.status === "active" && (
          <div className="flex w-full gap-2">
            <Button
              size="sm"
              onClick={onChat}
              variant="outline"
              className="flex-1 text-xs"
            >
              <MessageCircle size={13} className="mr-1" /> Chat
            </Button>

            {match.employer_location && isWorker && (
              <Button
                size="sm"
                onClick={handleRide}
                variant="outline"
                className="flex-none px-3 text-xs bg-black text-white hover:bg-black/80 hover:text-white"
              >
                <CarFront size={13} />
              </Button>
            )}

            {!myConfirmed && (
              <Button
                size="sm"
                onClick={onConfirm}
                disabled={confirming}
                className="flex-1 bg-primary text-primary-foreground text-xs ember-glow"
              >
                <CheckCircle2 size={14} className="mr-1" />
                {confirming ? "..." : "Confirm Complete"}
              </Button>
            )}
            {myConfirmed && !theirConfirmed && (
              <div className="flex-1 text-xs text-muted-foreground text-center py-1.5 flex items-center justify-center">
                Waiting...
              </div>
            )}
          </div>
        )}

        {match.status === "pending" && isInitiator && (
          <div className="flex items-center gap-2">
            <div className="flex-1 text-xs text-muted-foreground flex items-center justify-center gap-1">
              <Clock size={12} /> Waiting for response
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={onCancel}
              disabled={confirming}
              className="text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              <XCircle size={13} className="mr-1" /> Cancel
            </Button>
          </div>
        )}

        {match.status === "completed" && (
          <>
            <Button
              size="sm"
              onClick={onChat}
              variant="outline"
              className="flex-1 text-xs"
            >
              <MessageCircle size={13} className="mr-1" /> History
            </Button>
            <Button
              size="sm"
              onClick={() => onReview(otherId, otherName)}
              className="flex-1 bg-primary text-primary-foreground text-xs ember-glow"
            >
              <Star size={12} className="mr-1" /> Review
            </Button>
          </>
        )}
      </div>

      {/* Confirmation status for active */}
      {match.status === "active" && (myConfirmed || theirConfirmed) && (
        <div className="mt-2 flex gap-1">
          <span className={`text-[10px] flex items-center gap-0.5 ${myConfirmed ? "text-green-400" : "text-muted-foreground"}`}>
            {myConfirmed ? <CheckCircle2 size={10} /> : <XCircle size={10} />} You
          </span>
          <span className="text-muted-foreground text-[10px]">·</span>
          <span className={`text-[10px] flex items-center gap-0.5 ${theirConfirmed ? "text-green-400" : "text-muted-foreground"}`}>
            {theirConfirmed ? <CheckCircle2 size={10} /> : <XCircle size={10} />} {otherName.split(" ")[0]}
          </span>
        </div>
      )}
    </div>
  );
}
