import { useState, useEffect, useRef } from "react";
import { useAuth, useNav } from "../App";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Send,
  MessageCircle,
  CheckCircle2,
  Bot,
  User,
  Shield,
} from "lucide-react";

interface SupportThread {
  id: number;
  subject: string;
  status: string;
  last_message: string | null;
  admin_replies: number;
  created_at: string;
  updated_at: string;
}

interface SupportMessage {
  id: number;
  thread_id: number;
  sender_id: number;
  sender_role: "user" | "admin" | "auto";
  content: string;
  created_at: string;
  sender_name: string;
  sender_avatar: string;
}

export default function SupportScreen() {
  const { user, token } = useAuth();
  const { navigate } = useNav();
  const [view, setView] = useState<"list" | "new" | "chat">("list");
  const [threads, setThreads] = useState<SupportThread[]>([]);
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [activeThread, setActiveThread] = useState<number | null>(null);
  const [newSubject, setNewSubject] = useState("");
  const [newMessage, setNewMessage] = useState("");
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const [replyError, setReplyError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!token) return;
    fetchThreads();
  }, [token]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const fetchThreads = async () => {
    const res = await fetch("/api/support", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setThreads(await res.json());
  };

  const openThread = async (threadId: number) => {
    setActiveThread(threadId);
    setView("chat");
    const res = await fetch(`/api/support/${threadId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setMessages(await res.json());
  };

  const handleSend = async () => {
    if (!newMessage.trim() || sending) return;
    setSending(true);
    setSendError("");
    try {
      const res = await fetch("/api/support", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ subject: newSubject, message: newMessage }),
      });
      if (!res.ok) throw new Error("Failed to send message");
      const data = await res.json();
      setActiveThread(data.thread_id);
      setNewSubject("");
      setNewMessage("");
      await fetchThreads();
      await openThread(data.thread_id);
      setView("chat");
    } catch {
      setSendError("Failed to send message. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const handleReply = async () => {
    if (!replyText.trim() || !activeThread || sending) return;
    setSending(true);
    setReplyError("");
    try {
      const res = await fetch(`/api/support/${activeThread}/reply`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ message: replyText }),
      });
      if (!res.ok) throw new Error("Failed to send reply");
      const msg = await res.json();
      setMessages((prev) => [...prev, msg]);
      setReplyText("");
      await fetchThreads();
    } catch {
      setReplyError("Failed to send reply. Please try again.");
    } finally {
      setSending(false);
    }
  };

  // Allow anyone to access support

  if (!user) {
    return <GuestSupportForm />;
  }

  return (
    <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-border">
        {(view === "chat" || view === "new") && (
          <button
            onClick={() => {
              setView("list");
              setActiveThread(null);
            }}
            className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center"
          >
            <ArrowLeft size={16} />
          </button>
        )}
        <div className="flex-1">
          <h2 className="text-2xl text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>
            {view === "chat" ? "Conversation" : view === "new" ? "New Message" : "Contact Day Shift"}
          </h2>
          <p className="text-muted-foreground text-xs">
            {view === "list"
              ? "We're here to help"
              : view === "new"
              ? "Describe your issue or question"
              : "Typically responds within 24 hours"}
          </p>
        </div>
        {view === "list" && (
          <div className="text-primary">
            <Shield size={20} />
          </div>
        )}
      </div>

      <div className="p-5">
        {/* ── Thread List ── */}
        {view === "list" && (
          <div className="space-y-4">
            {/* New message button */}
            <button
              onClick={() => setView("new")}
              className="w-full p-4 border-2 border-dashed border-primary/30 rounded-xl flex items-center gap-3 hover:border-primary/60 hover:bg-primary/5 transition-all"
            >
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                <MessageCircle size={18} className="text-primary" />
              </div>
              <div className="text-left">
                <p className="text-foreground font-semibold text-sm">Send a New Message</p>
                <p className="text-muted-foreground text-xs">Ask a question, report an issue, or get help</p>
              </div>
            </button>

            {/* Existing threads */}
            {threads.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Your Conversations</p>
                <div className="space-y-2">
                  {threads.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => openThread(t.id)}
                      className="w-full bg-card border border-border rounded-xl p-3 text-left hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-foreground font-semibold text-sm truncate flex-1 mr-2">
                          {t.subject}
                        </span>
                        <Badge
                          className={`text-[10px] border-0 ${
                            t.status === "open"
                              ? "bg-green-500/20 text-green-300"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {t.status === "open" ? "Open" : "Closed"}
                        </Badge>
                      </div>
                      {t.last_message && (
                        <p className="text-muted-foreground text-xs line-clamp-1">{t.last_message}</p>
                      )}
                      <p className="text-muted-foreground/60 text-[10px] mt-1">
                        {new Date(t.updated_at).toLocaleDateString()}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {threads.length === 0 && (
              <div className="text-center py-8">
                <MessageCircle size={32} className="text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground text-sm">No conversations yet</p>
                <p className="text-muted-foreground/60 text-xs mt-1">Tap above to start one</p>
              </div>
            )}
          </div>
        )}

        {/* ── New Message Form ── */}
        {view === "new" && (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">Subject</Label>
              <Input
                value={newSubject}
                onChange={(e) => setNewSubject(e.target.value)}
                placeholder="e.g. Account issue, Feature request, Bug report"
                className="bg-secondary border-border"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">Message</Label>
              <Textarea
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Tell us what's going on…"
                rows={6}
                className="bg-secondary border-border resize-none"
              />
            </div>
            <Button
              onClick={handleSend}
              disabled={!newMessage.trim() || sending}
              className="w-full bg-primary text-primary-foreground ember-glow"
            >
              {sending ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                  Sending…
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Send size={16} /> Send Message
                </span>
              )}
            </Button>
            {sendError && (
              <p className="text-destructive text-xs text-center">{sendError}</p>
            )}
          </div>
        )}

        {/* ── Chat View ── */}
        {view === "chat" && activeThread && (
          <div className="flex flex-col" style={{ minHeight: "calc(100vh - 220px)" }}>
            <div className="flex-1 space-y-3 mb-4">
              {messages.map((m) => {
                const isUser = m.sender_role === "user";
                const isAuto = m.sender_role === "auto";
                return (
                  <div key={m.id} className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
                    {!isUser && (
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                          isAuto ? "bg-primary/20" : "bg-primary"
                        }`}
                      >
                        {isAuto ? (
                          <Bot size={14} className="text-primary" />
                        ) : (
                          <Shield size={14} className="text-primary-foreground" />
                        )}
                      </div>
                    )}
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${
                        isUser
                          ? "bg-primary text-primary-foreground rounded-br-md"
                          : isAuto
                          ? "bg-primary/10 border border-primary/20 rounded-bl-md"
                          : "bg-card border border-border rounded-bl-md"
                      }`}
                    >
                      {!isUser && (
                        <p className={`text-[10px] font-semibold mb-0.5 ${isAuto ? "text-primary" : "text-foreground"}`}>
                          {isAuto ? "Day Shift" : "Admin"}
                        </p>
                      )}
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
                      <p
                        className={`text-[10px] mt-1 ${
                          isUser ? "text-primary-foreground/60" : "text-muted-foreground"
                        }`}
                      >
                        {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                    {isUser && (
                      <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                        <User size={14} className="text-muted-foreground" />
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Reply input */}
            <div className="sticky bottom-0 bg-background pt-2">
              <div className="flex gap-2">
                <Input
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Type a reply…"
                  className="bg-secondary border-border flex-1"
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
                  {sending ? (
                    <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Send size={16} />
                  )}
                </Button>
              </div>
              {replyError && (
                <p className="text-destructive text-xs mt-1.5">{replyError}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function GuestSupportForm() {
  const { navigate } = useNav();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch("/api/support/guest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, message }),
      });
      if (!res.ok) throw new Error("Failed to send message");
      setSent(true);
    } catch {
      setError("Failed to send message. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-border">
          <h2 className="text-2xl text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>Contact Day Shift</h2>
        </div>
        <div className="p-6 text-center space-y-3">
          <div className="text-4xl">✅</div>
          <p className="text-foreground font-semibold">Message sent</p>
          <p className="text-muted-foreground text-sm">We'll get back to you soon.</p>
          <button onClick={() => navigate("feed")} className="text-primary text-sm hover:underline">Back to feed</button>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-border">
        <h2 className="text-2xl text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>Contact Day Shift</h2>
      </div>
      <div className="p-5">
        <p className="text-muted-foreground text-sm mb-4">Have a question or issue? Send us a message.</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label className="text-xs">Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required className="bg-secondary border-border h-11" />
          </div>
          <div>
            <Label className="text-xs">Email</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="bg-secondary border-border h-11" />
          </div>
          <div>
            <Label className="text-xs">Message</Label>
            <Textarea value={message} onChange={(e) => setMessage(e.target.value)} required rows={4} className="bg-secondary border-border resize-none" />
          </div>
          <Button type="submit" disabled={submitting} className="w-full h-11 bg-primary text-primary-foreground font-semibold">
            {submitting ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                Sending…
              </span>
            ) : (
              "Send Message"
            )}
          </Button>
          {error && (
            <p className="text-destructive text-xs text-center">{error}</p>
          )}
        </form>
      </div>
    </div>
  );
}
