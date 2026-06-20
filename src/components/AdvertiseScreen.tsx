import { useState, useEffect } from "react";
import { useAuth, useNav } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, ChevronLeft, Sparkles, Building2, Star, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TermsContent, PrivacyContent } from "./LegalContent";

interface AdTier {
  name: string;
  price: number;
  interval: string;
  boosts_per_month: number;
  features: string[];
}

const TIER_ICONS: Record<string, React.ReactNode> = {
  business: <Building2 size={24} className="text-blue-400" />,
  premium: <Star size={24} className="text-amber-400" />,
  enterprise: <Zap size={24} className="text-orange-400" />,
};

const TIER_COLORS: Record<string, string> = {
  business: "border-blue-500/30",
  premium: "border-amber-500/40",
  enterprise: "border-orange-500/40",
};

export default function AdvertiseScreen() {
  const { user, token } = useAuth();
  const { navigate } = useNav();
  const [tiers, setTiers] = useState<Record<string, AdTier>>({});
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState<string | null>(null);
  const [subStatus, setSubStatus] = useState<{ active: boolean; tier: string | null }>({ active: false, tier: null });
  const [error, setError] = useState("");

  // Agreement dialog state
  const [agreementOpen, setAgreementOpen] = useState(false);
  const [pendingTier, setPendingTier] = useState<string | null>(null);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [adAgreementAccepted, setAdAgreementAccepted] = useState(false);
  const [legalDialog, setLegalDialog] = useState<"terms" | "privacy" | null>(null);

  useEffect(() => {
    fetch("/api/advertiser/ad-tiers")
      .then((r) => r.json())
      .then((d) => { setTiers(d); setLoading(false); })
      .catch(() => setLoading(false));

    if (token) {
      fetch("/api/advertiser/subscription-status", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then((d) => setSubStatus(d))
        .catch(() => {});
    }
  }, [token]);

  const handleTierClick = (tierKey: string) => {
    if (!user) {
      // Non-user: send to register with advertiser role pre-selected
      navigate("register", { advertiser: true });
      return;
    }
    if (!token) return;
    // Existing user: open agreement dialog
    setPendingTier(tierKey);
    setTermsAccepted(false);
    setPrivacyAccepted(false);
    setAdAgreementAccepted(false);
    setAgreementOpen(true);
  };

  const handleAgreeAndSubscribe = async () => {
    if (!pendingTier || !token) return;
    setAgreementOpen(false);
    setSubscribing(pendingTier);
    setError("");
    try {
      // Accept advertiser agreement
      await fetch("/api/advertiser/agreement", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      // Create subscription checkout
      const res = await fetch("/api/advertiser/subscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tier: pendingTier }),
      });
      const data = await res.json();
      if (data.stripe_checkout_url) {
        window.location.href = data.stripe_checkout_url;
      } else {
        setError(data.detail || "Failed to start checkout");
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubscribing(null);
      setPendingTier(null);
    }
  };

  const tierEntries = Object.entries(tiers);

  return (
    <div className="min-h-screen bg-background overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b border-border px-4 py-3 flex items-center gap-3">
        {user && (
          <button onClick={() => navigate("profile")} className="text-muted-foreground hover:text-foreground">
            <ChevronLeft size={22} />
          </button>
        )}
        <h1 className="text-xl font-bold" style={{ fontFamily: "'Bebas Neue', sans-serif", letterSpacing: "0.05em" }}>
          Advertise on Day Shift
        </h1>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6 pb-24">
        {/* Current plan indicator */}
        {subStatus.active && subStatus.tier && (
          <div className="text-center">
            <p className="text-sm text-primary font-medium">
              ✨ Active subscription: <span className="capitalize">{subStatus.tier}</span> plan
            </p>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : tierEntries.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {tierEntries.map(([key, tier]) => {
              const isPopular = key === "premium";
              const isCurrent = subStatus.active && subStatus.tier === key;
              return (
                <Card
                  key={key}
                  className={cn(
                    "relative flex flex-col",
                    TIER_COLORS[key],
                    isPopular && "ring-1 ring-amber-500/50",
                  )}
                >
                  {isPopular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="bg-amber-500 text-amber-950 text-[10px] font-bold px-3 py-0.5 rounded-full">
                        MOST POPULAR
                      </span>
                    </div>
                  )}
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2">
                      {TIER_ICONS[key]}
                      <CardTitle className="text-lg">{tier.name}</CardTitle>
                    </div>
                    <div className="pt-1">
                      <span className="text-3xl font-bold">${tier.price}</span>
                      <span className="text-muted-foreground text-sm">/mo</span>
                    </div>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col gap-4">
                    <ul className="space-y-2 flex-1">
                      {tier.features.map((feature, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <Check size={14} className="text-primary shrink-0 mt-0.5" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                    {/* Billing info inside card */}
                    <p className="text-[10px] text-muted-foreground/70 text-center leading-relaxed">
                      Subscriptions are billed monthly. Cancel anytime from your profile settings.
                    </p>
                    <Button
                      className={cn(
                        "w-full",
                        isPopular ? "bg-amber-500 text-amber-950 hover:bg-amber-600" : "bg-primary text-primary-foreground hover:bg-primary/90"
                      )}
                      disabled={isCurrent || subscribing === key}
                      onClick={() => handleTierClick(key)}
                    >
                      {isCurrent ? "Current Plan" : subscribing === key ? "Redirecting..." : user ? "Get Started" : "Sign Up to Get Started"}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          <p className="text-center text-muted-foreground py-10">Unable to load plans.</p>
        )}

        {error && (
          <p className="text-destructive text-sm text-center bg-destructive/10 rounded-lg py-2 px-3">{error}</p>
        )}
      </div>

      {/* Agreement Dialog — for existing users */}
      <Dialog open={agreementOpen} onOpenChange={setAgreementOpen}>
        <DialogContent className="max-w-md mx-auto">
          <DialogHeader>
            <DialogTitle>Before you subscribe</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 pt-2">
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={adAgreementAccepted}
                onChange={(e) => setAdAgreementAccepted(e.target.checked)}
                className="mt-1"
              />
              <span className="text-sm text-foreground">
                I agree to the <button type="button" onClick={() => setLegalDialog("terms")} className="text-primary underline">Advertiser Agreement</button>
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                className="mt-1"
              />
              <span className="text-sm text-foreground">
                I agree to the <button type="button" onClick={() => setLegalDialog("terms")} className="text-primary underline">Terms of Use</button>
              </span>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={privacyAccepted}
                onChange={(e) => setPrivacyAccepted(e.target.checked)}
                className="mt-1"
              />
              <span className="text-sm text-foreground">
                I agree to the <button type="button" onClick={() => setLegalDialog("privacy")} className="text-primary underline">Privacy Policy</button>
              </span>
            </label>

            <Button
              className="w-full mt-2"
              disabled={!adAgreementAccepted || !termsAccepted || !privacyAccepted}
              onClick={handleAgreeAndSubscribe}
            >
              Continue to Payment
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Legal content dialog */}
      <Dialog open={!!legalDialog} onOpenChange={() => setLegalDialog(null)}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{legalDialog === "terms" ? "Terms of Service" : "Privacy Policy"}</DialogTitle>
          </DialogHeader>
          <div className="text-sm text-muted-foreground leading-relaxed">
            {legalDialog === "terms" ? <TermsContent /> : <PrivacyContent />}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
