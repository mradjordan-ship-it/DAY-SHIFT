import { useState, useEffect } from "react";
import { useNav, useAuth } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft, Send, CheckCircle2, DollarSign } from "lucide-react";

export default function SponsorScreen() {
  const { navigate } = useNav();
  const { user, token } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [tipAmount, setTipAmount] = useState<number>(0);
  const [customAmount, setCustomAmount] = useState<number>(0);
  const [tipMessage, setTipMessage] = useState("");
  const [tipSending, setTipSending] = useState(false);
  const [tipSent, setTipSent] = useState(false);

  // Check if returning from a successful Stripe checkout
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("tip_success") === "1") {
      setTipSent(true);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  const handleTip = async () => {
    if (!tipAmount) return;
    setTipSending(true);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const body: Record<string, unknown> = { amount: tipAmount, message: tipMessage };
      const res = await fetch("/api/tips/checkout", { method: "POST", headers, body: JSON.stringify(body) });
      if (res.ok) {
        const data = await res.json();
        if (data.stripe_checkout_url) {
          window.location.href = data.stripe_checkout_url;
          return;
        }
      }
      // Fallback: record without payment if Stripe isn't configured
      const endpoint = user ? "/api/tips" : "/api/tips/guest";
      if (!user) {
        body.name = name;
        body.email = email;
        if (!email) return;
      }
      const res2 = await fetch(endpoint, { method: "POST", headers, body: JSON.stringify(body) });
      if (res2.ok) setTipSent(true);
    } finally {
      setTipSending(false);
    }
  };

  const handleContact = async () => {
    if (!name.trim() || !email.trim() || !message.trim()) return;
    setSending(true);
    try {
      const res = await fetch("/api/contact/sponsor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, phone, message }),
      });
      if (res.ok) setSent(true);
    } finally {
      setSending(false);
    }
  };

  if (sent) {
    return (
      <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
        <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
          <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center mb-4 ember-glow">
            <CheckCircle2 size={32} className="text-primary" />
          </div>
          <h2 className="text-3xl text-foreground mb-2" style={{ fontFamily: "'Bebas Neue'" }}>Message Sent!</h2>
          <p className="text-muted-foreground text-xs mb-6 max-w-xs leading-relaxed">
            Thanks for reaching out — we'll get back to you soon.
          </p>
          <Button onClick={() => navigate("feed")} className="bg-primary text-primary-foreground ember-glow">
            Back to Feed
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-border">
        <button
          onClick={() => navigate("feed")}
          className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center"
        >
          <ArrowLeft size={16} />
        </button>
        <div className="flex-1">
          <h2 className="text-2xl text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>Support Day Shift</h2>
          <p className="text-muted-foreground text-xs">Tip, donate, or get in touch</p>
        </div>
        <DollarSign size={20} className="text-amber-400" />
      </div>

      <div className="p-5 space-y-5">
        {/* Tip Jar */}
        <div className="bg-gradient-to-br from-amber-500/10 to-amber-900/10 border border-amber-500/20 rounded-2xl p-4 space-y-3">
          {tipSent ? (
            <div className="text-center py-4">
              <div className="w-14 h-14 bg-amber-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 size={28} className="text-amber-400" />
              </div>
              <h3 className="text-xl text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>Thank You!</h3>
              <p className="text-muted-foreground text-xs mt-1">Your tip means the world to us 💛</p>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <DollarSign size={18} className="text-amber-400" />
                <h3 className="text-lg text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>Tip Jar</h3>
              </div>
              <p className="text-muted-foreground text-xs leading-relaxed">
                Day Shift is community-supported. Every contribution helps us keep the kitchen connected.
              </p>
              <div className="flex gap-2">
                {[
                  { cents: 100, label: "$1" },
                  { cents: 500, label: "$5" },
                  { cents: 1000, label: "$10" },
                ].map((t) => (
                  <button
                    key={t.cents}
                    onClick={() => { setTipAmount(t.cents); setCustomAmount(0); }}
                    className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all border ${
                      tipAmount === t.cents
                        ? "bg-amber-500 text-black border-amber-400"
                        : "bg-secondary text-muted-foreground border-border hover:bg-muted"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={1}
                  placeholder="Custom amount"
                  value={customAmount || ""}
                  onChange={(e) => {
                    const v = parseInt(e.target.value) || 0;
                    setCustomAmount(v > 0 ? v : 0);
                    if (v > 0) setTipAmount(v * 100);
                    else if (tipAmount > 0 && [100, 500, 1000].includes(tipAmount) === false) setTipAmount(0);
                  }}
                  className="bg-secondary border-border text-xs h-9 flex-1"
                />
                <span className="text-muted-foreground text-xs shrink-0">dollars</span>
              </div>
              {tipAmount > 0 && (
                <>
                  {!user && (
                    <div className="space-y-1 mb-2">
                      <Input
                        placeholder="Your email *"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="bg-secondary border-border text-xs h-8"
                      />
                    </div>
                  )}
                  <Textarea
                    placeholder="Leave a note (optional)"
                    value={tipMessage}
                    onChange={(e) => setTipMessage(e.target.value)}
                    rows={2}
                    className="bg-secondary border-border text-xs resize-none mb-2"
                  />
                  <Button
                    onClick={handleTip}
                    disabled={tipSending || (!user && !email.trim())}
                    className="w-full bg-amber-500 hover:bg-amber-600 text-black font-semibold"
                  >
                    {tipSending ? "Processing…" : `Tip $${tipAmount / 100}`}
                  </Button>
                </>
              )}
            </>
          )}
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-border" />
          <span className="text-muted-foreground text-[10px] uppercase tracking-wider">or</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* Contact form */}
        <div className="space-y-3">
          <h3 className="text-lg text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>Get in Touch</h3>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name *"
            className="bg-secondary border-border"
          />
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email *"
            className="bg-secondary border-border"
          />
          <Input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Phone number *"
            className="bg-secondary border-border"
          />
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Your message…"
            rows={4}
            className="bg-secondary border-border resize-none"
          />
          <Button
            onClick={handleContact}
            disabled={!name.trim() || !email.trim() || !phone.trim() || !message.trim() || sending}
            className="w-full bg-primary text-primary-foreground ember-glow"
          >
            {sending ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                Sending…
              </span>
            ) : (
              <span className="flex items-center gap-2"><Send size={16} /> Send Message</span>
            )}
          </Button>
        </div>

        <p className="text-center text-muted-foreground/60 text-[10px]">
          No account needed · We respond within 48 hours
        </p>
      </div>
    </div>
  );
}
