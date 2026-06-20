import { useState, useEffect } from "react";
import { useAuth, useNav } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, ChevronLeft, Sparkles, Building2, Star, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

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

  const handleSubscribe = async (tierKey: string) => {
    if (!user) {
      navigate("register");
      return;
    }
    if (!token) return;

    setSubscribing(tierKey);
    setError("");
    try {
      const res = await fetch("/api/advertiser/subscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tier: tierKey }),
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

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Intro */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/15 mb-2">
            <Sparkles className="text-primary" size={28} />
          </div>
          <h2 className="text-2xl font-bold text-foreground">Reach Culinary Pros Every Day</h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Day Shift connects kitchens, suppliers, and culinary businesses with workers across the industry.
            Choose a monthly plan that fits your hiring and marketing needs.
          </p>
        </div>

        {/* Active subscription banner */}
        {subStatus.active && subStatus.tier && (
          <div className="bg-primary/10 border border-primary/30 rounded-xl p-4 text-center">
            <p className="text-sm font-semibold text-primary">
              ✓ Active {tiers[subStatus.tier]?.name || subStatus.tier} subscription
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Manage your subscription from your profile settings.
            </p>
          </div>
        )}

        {/* Tier cards */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">
            {tierEntries.map(([key, tier]) => {
              const isCurrent = subStatus.tier === key && subStatus.active;
              const isPopular = key === "premium";
              return (
                <Card
                  key={key}
                  className={cn(
                    "bg-card relative overflow-hidden",
                    TIER_COLORS[key] || "border-border",
                    isPopular && "ring-2 ring-amber-500/40"
                  )}
                >
                  {isPopular && (
                    <div className="absolute top-0 right-0 bg-amber-500 text-amber-950 text-[10px] font-bold px-3 py-1 rounded-bl-lg">
                      MOST POPULAR
                    </div>
                  )}
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {TIER_ICONS[key]}
                        <CardTitle className="text-lg" style={{ fontFamily: "'Bebas Neue', sans-serif", letterSpacing: "0.03em" }}>
                          {tier.name}
                        </CardTitle>
                      </div>
                      <div className="text-right">
                        <span className="text-2xl font-bold text-foreground">${tier.price}</span>
                        <span className="text-xs text-muted-foreground">/mo</span>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {tier.boosts_per_month > 0 && (
                      <p className="text-xs font-semibold text-primary">
                        {tier.boosts_per_month === -1 ? "Unlimited" : tier.boosts_per_month} boosted posts{tier.boosts_per_month !== -1 ? "/mo" : ""}
                      </p>
                    )}
                    <ul className="space-y-2">
                      {tier.features.map((feature, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <Check size={14} className="text-primary shrink-0 mt-0.5" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <Button
                      className={cn(
                        "w-full",
                        isPopular ? "bg-amber-500 text-amber-950 hover:bg-amber-600" : "bg-primary text-primary-foreground hover:bg-primary/90"
                      )}
                      disabled={isCurrent || subscribing === key}
                      onClick={() => handleSubscribe(key)}
                    >
                      {isCurrent ? "Current Plan" : subscribing === key ? "Redirecting..." : user ? "Get Started" : "Sign Up to Get Started"}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {error && (
          <p className="text-destructive text-sm text-center bg-destructive/10 rounded-lg py-2 px-3">{error}</p>
        )}

        {/* FAQ / CTA for non-users */}
        {!user && (
          <div className="text-center pt-4 pb-8 space-y-3">
            <p className="text-sm text-muted-foreground">
              Don't have an account yet? Sign up to start advertising.
            </p>
            <div className="flex gap-2 justify-center">
              <Button variant="outline" onClick={() => navigate("login")} className="border-border">
                Log In
              </Button>
              <Button onClick={() => navigate("register")} className="bg-primary text-primary-foreground">
                Get Started
              </Button>
            </div>
          </div>
        )}

        {/* Legal */}
        <div className="text-center pb-8">
          <p className="text-[10px] text-muted-foreground/60">
            Subscriptions are billed monthly. Cancel anytime from your profile settings.
            By subscribing, you agree to our{" "}
            <button onClick={() => navigate("terms")} className="text-primary hover:underline">Terms</button>
            {" "}and{" "}
            <button onClick={() => navigate("privacy")} className="text-primary hover:underline">Privacy Policy</button>.
          </p>
        </div>
      </div>
    </div>
  );
}
