import { useState } from "react";
import { useNav } from "../App";
import { trackEvent } from "../lib/analytics";

const ONBOARDING_KEY = "ds_onboarding_done";

const steps = [
  {
    emoji: "👷‍♀️",
    title: "Welcome to Day Shift",
    desc: "The marketplace where food industry workers and employers connect through video.",
  },
  {
    emoji: "📹",
    title: "Post Your Story",
    desc: "Share videos up to 60 seconds showcasing your skills, kitchen, or job openings. Video is your resume here.",
  },
  {
    emoji: "🤝",
    title: "Match & Connect",
    desc: "See someone you want to work with? Send a match request. When accepted, you can chat directly.",
  },
  {
    emoji: "💬",
    title: "Chat & Hire",
    desc: "Message your matches, discuss shifts, and close the deal — all inside the app.",
  },
  {
    emoji: "🧡",
    title: "Support Each Other",
    desc: "Boost your posts for visibility, get reviews, and build your reputation.",
  },
];

export default function OnboardingModal() {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(() => !localStorage.getItem(ONBOARDING_KEY));
  const { navigate } = useNav();

  if (!visible) return null;

  const finish = () => {
    localStorage.setItem(ONBOARDING_KEY, "1");
    setVisible(false);
    trackEvent("onboarding_complete");
  };

  const skip = () => {
    localStorage.setItem(ONBOARDING_KEY, "1");
    setVisible(false);
    trackEvent("onboarding_skip", { step });
  };

  const next = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
      trackEvent("onboarding_step", { step: step + 1 });
    } else {
      finish();
    }
  };

  const s = steps[step];
  const progress = ((step + 1) / steps.length) * 100;

  return (
    <div className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-3xl max-w-sm w-full overflow-hidden shadow-2xl">
        {/* Progress bar */}
        <div className="h-1 bg-muted">
          <div
            className="h-full bg-amber-500 transition-all duration-300 rounded-r-full"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="p-6 space-y-5">
          {/* Emoji */}
          <div className="text-center">
            <span className="text-5xl">{s.emoji}</span>
          </div>

          {/* Content */}
          <div className="text-center space-y-2">
            <h2 className="text-xl font-bold text-foreground" style={{ fontFamily: "'Bebas Neue'" }}>
              {s.title}
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {s.desc}
            </p>
          </div>

          {/* Step dots */}
          <div className="flex justify-center gap-1.5">
            {steps.map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-colors ${
                  i === step ? "bg-amber-500" : i < step ? "bg-amber-500/40" : "bg-muted-foreground/20"
                }`}
              />
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={skip}
              className="flex-1 text-sm font-medium py-3 rounded-xl border border-border text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip
            </button>
            <button
              onClick={next}
              className="flex-1 text-sm font-semibold py-3 rounded-xl bg-amber-500 text-black hover:bg-amber-400 transition-colors"
            >
              {step === steps.length - 1 ? "Get Started" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
