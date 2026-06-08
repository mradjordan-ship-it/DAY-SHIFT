import { useState, useEffect, useRef } from "react";
import type { Message, Match } from "../types";
import { useAuth } from "../App";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Send, ArrowLeft, Flag } from "lucide-react";
import { useNav } from "../App";

export default function ChatScreen({ matchId }: { matchId: number }) {
  const { user, token } = useAuth();
  const { navigate } = useNav();
  const [messages, setMessages] = useState<Message[]>([]);
  const [match, setMatch] = useState<Match | null>(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showReport, setShowReport] = useState(false);
  const [reportReason, setReportReason] = useState("other");
  const [reportComment, setReportComment] = useState("");
  const [reportSent, setReportSent] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!token || !matchId) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const [matchRes, msgRes] = await Promise.all([
          fetch("/api/matches", { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`/api/matches/${matchId}/messages`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);
        if (matchRes.ok) {
          const all: Match[] = await matchRes.json();
          setMatch(all.find((m) => m.id === matchId) ?? null);
        }
        if (msgRes.ok) {
          setMessages(await msgRes.json());
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();

    // Poll for new messages
    const id = setInterval(async () => {
      try {
        const res = await fetch(`/api/matches/${matchId}/messages`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) setMessages(await res.json());
      } catch {}
    }, 5000);

    return () => clearInterval(id);
  }, [token, matchId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!text.trim() || sending) return;
    const content = text.trim();
    setText("");
    setSending(true);
    try {
      const res = await fetch(`/api/matches/${matchId}/messages`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        const msg: Message = await res.json();
        setMessages((prev) => [...prev, msg]);
      }
    } finally {
      setSending(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  if (!user) return null;

  const isWorker = match ? user.id === match.worker_id : false;
  const otherName = match ? (isWorker ? match.employer_name : match.worker_name) : "";
  const otherAvatar = match ? (isWorker ? match.employer_avatar : match.worker_avatar) : "";
  const otherUserId = match ? (isWorker ? match.employer_id : match.worker_id) : null;

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const groupByDate = (msgs: Message[]) => {
    const groups: { date: string; messages: Message[] }[] = [];
    for (const msg of msgs) {
      const date = new Date(msg.created_at).toLocaleDateString();
      const last = groups[groups.length - 1];
      if (last?.date === date) {
        last.messages.push(msg);
      } else {
        groups.push({ date, messages: [msg] });
      }
    }
    return groups;
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Chat header */}
      <div className="flex items-center gap-3 p-4 border-b border-border bg-card/50">
        <button
          onClick={() => navigate("matches")}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="w-9 h-9 rounded-full bg-secondary border border-border overflow-hidden flex-shrink-0">
          {otherAvatar ? (
            <img src={otherAvatar} alt="" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-sm font-bold text-primary">
              {otherName?.[0]?.toUpperCase()}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-foreground text-sm">{otherName}</p>
          {match && (
            <p className="text-[10px] text-muted-foreground capitalize">
              {match.status === "active" ? (
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full pulse-orange" />
                  Active match
                </span>
              ) : match.status === "pending" ? "Pending match" : "Completed shift"}
            </p>
          )}
        </div>
        {match && otherUserId && (
          <button
            onClick={() => { setShowReport(true); setReportSent(false); setReportComment(""); setReportReason("other"); }}
            className="text-muted-foreground hover:text-destructive transition-colors p-1"
            aria-label="Report user"
          >
            <Flag size={18} />
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loading ? (
          <div className="flex justify-center mt-10">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-center">
            <div className="text-4xl mb-3">💬</div>
            <p className="text-muted-foreground text-sm">
              Start the conversation with {otherName}
            </p>
          </div>
        ) : (
          groupByDate(messages).map((group) => (
            <div key={group.date}>
              <div className="flex items-center gap-3 my-3">
                <div className="flex-1 h-px bg-border" />
                <span className="text-[10px] text-muted-foreground">
                  {new Date(group.date).toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" })}
                </span>
                <div className="flex-1 h-px bg-border" />
              </div>
              <div className="space-y-2">
                {group.messages.map((msg) => {
                  const isMe = msg.sender_id === user.id;
                  return (
                    <div key={msg.id} className={`flex ${isMe ? "justify-end" : "justify-start"} gap-2`}>
                      {!isMe && (
                        <div className="w-6 h-6 rounded-full bg-secondary border border-border overflow-hidden flex-shrink-0 self-end">
                          {msg.sender_avatar ? (
                            <img src={msg.sender_avatar} alt="" className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-[10px] font-bold text-primary">
                              {msg.sender_name?.[0]?.toUpperCase()}
                            </div>
                          )}
                        </div>
                      )}
                      <div className={`max-w-[72%] ${isMe ? "items-end" : "items-start"} flex flex-col gap-0.5`}>
                        <div className={`px-3 py-2 text-sm ${isMe ? "bubble-me" : "bubble-them"}`}>
                          {msg.content}
                        </div>
                        <span className="text-[10px] text-muted-foreground px-1">
                          {formatTime(msg.created_at)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {match && match.status === "pending" ? (
        <div className="p-3 border-t border-border bg-card/50 text-center">
          <p className="text-muted-foreground text-xs">Messages will be available once the match is accepted</p>
        </div>
      ) : (
      <div className="p-3 border-t border-border bg-card/50">
        <div className="flex gap-2">
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Type a message..."
            className="flex-1 bg-secondary border-border rounded-2xl"
          />
          <Button
            onClick={send}
            disabled={!text.trim() || sending}
            size="icon"
            className="w-10 h-10 rounded-xl bg-primary text-primary-foreground ember-glow flex-shrink-0"
          >
            <Send size={16} />
          </Button>
        </div>
      </div>
      )}
      {/* Report modal */}
      {showReport && otherUserId && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setShowReport(false)}>
          <div className="bg-card border border-border rounded-2xl p-5 w-full max-w-sm space-y-3" onClick={(e) => e.stopPropagation()}>
            {reportSent ? (
              <div className="text-center py-4">
                <p className="text-primary text-lg font-semibold">Report Submitted</p>
                <p className="text-muted-foreground text-sm mt-1">We'll review this account</p>
              </div>
            ) : (
              <>
                <h3 className="text-foreground font-semibold text-sm">Report {otherName}</h3>
                <p className="text-xs text-muted-foreground">Select a reason for your report:</p>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { value: "harassment", label: "Harassment" },
                    { value: "spam", label: "Spam" },
                    { value: "inappropriate", label: "Inappropriate" },
                    { value: "other", label: "Other" },
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
                          body: JSON.stringify({ target_type: "user", target_id: otherUserId, reason: reportReason, comment: reportComment || null }),
                        });
                        if (res.ok) {
                          setReportSent(true);
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
    </div>
  );
}
