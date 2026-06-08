import { useState, useEffect } from "react";
import { setAnalyticsConsent, hasAnalyticsConsent } from "../lib/analytics";

const CONSENT_KEY = "ds_cookie_consent";

type ConsentChoice = "all" | "essential" | null;

export default function CookieConsent() {
  const [choice, setChoice] = useState<ConsentChoice>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(CONSENT_KEY) as ConsentChoice;
    if (stored) {
      setChoice(stored);
      if (stored === "all") {
        setAnalyticsConsent(true);
      }
    } else {
      // Show banner after a short delay so it doesn't flash on every page
      const timer = setTimeout(() => setVisible(true), 1500);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    setChoice("all");
    localStorage.setItem(CONSENT_KEY, "all");
    setAnalyticsConsent(true);
    setVisible(false);
  };

  const handleEssential = () => {
    setChoice("essential");
    localStorage.setItem(CONSENT_KEY, "essential");
    setAnalyticsConsent(false);
    setVisible(false);
  };

  if (!visible || choice) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-3 animate-in slide-in-from-bottom-4 duration-300">
      <div className="max-w-lg mx-auto bg-card border border-border rounded-2xl shadow-2xl p-4 space-y-3">
        <div className="flex items-start gap-3">
          <div className="shrink-0 w-8 h-8 rounded-full bg-amber-500/15 flex items-center justify-center mt-0.5">
            <svg className="w-4 h-4 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-foreground">Your privacy matters</p>
            <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
              We use cookies for essential functionality and optional analytics to improve Day Shift. You can change this anytime in your profile.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleEssential}
            className="flex-1 text-xs font-medium py-2.5 px-3 rounded-xl border border-border text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors"
          >
            Essential Only
          </button>
          <button
            onClick={handleAccept}
            className="flex-1 text-xs font-semibold py-2.5 px-3 rounded-xl bg-amber-500 text-black hover:bg-amber-400 transition-colors"
          >
            Accept All Cookies
          </button>
        </div>
      </div>
    </div>
  );
}
