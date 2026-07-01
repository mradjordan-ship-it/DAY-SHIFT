import { useNav } from "../App";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import InstallPrompt from "./InstallPrompt";

const features = [
  {
    title: "Video Profiles",
    desc: "Create short videos (up to 60 seconds) to showcase your skills, personality, or kitchen. Stand out visually.",
    bubble: "Show 'em what you got! Post a 60-second video — your skills, your kitchen, your vibe.",
  },
  {
    title: "Instant Matching",
    desc: "Swipe through crew and kitchens. Match instantly when both sides agree.",
    bubble: "Swipe, match, done. No waiting for callbacks — when both sides say yes, you're connected.",
  },
  {
    title: "Built-In Chat",
    desc: "Message your matches directly. Discuss details, confirm shifts, coordinate in-app.",
    bubble: "Talk it out right here. Shift details, start times, whatever — no need to swap numbers.",
  },
  {
    title: "Reviews & Ratings",
    desc: "Build your reputation over time. The best connections find you first.",
    bubble: "Your rep speaks for you. Leave reviews, earn stars — the best connections find you first.",
  },
  {
    title: "For Sale & Events",
    desc: "Sell equipment, post positions, or promote events. A full community hub.",
    bubble: "Sell equipment, post gigs, promote events. This ain't just a job board — it's a community.",
  },
  {
    title: "Ride Integration",
    desc: "One tap opens Uber or Lyft with the address pre-loaded. Get to shifts easily.",
    bubble: "One tap → Uber or Lyft pulls up with the kitchen's address. Never be late again.",
  },
];

/* ── Animated Feature Icons ────────────────────────────────────────────── */

function VideoProfilesIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10 shrink-0" aria-hidden="true">
      {/* Smiling face */}
      <circle cx="20" cy="20" r="16" fill="hsl(var(--primary) / 0.15)" stroke="hsl(var(--primary))" strokeWidth="1.5" />
      {/* Eyes — blink animation */}
      <ellipse cx="14" cy="17" rx="2" ry="2.5" fill="hsl(var(--primary))">
        <animate attributeName="ry" values="2.5;0.3;2.5" dur="3s" repeatCount="indefinite" begin="0.5s" />
      </ellipse>
      <ellipse cx="26" cy="17" rx="2" ry="2.5" fill="hsl(var(--primary))">
        <animate attributeName="ry" values="2.5;0.3;2.5" dur="3s" repeatCount="indefinite" begin="0.5s" />
      </ellipse>
      {/* Smile */}
      <path d="M13 25 Q20 31 27 25" stroke="hsl(var(--primary))" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      {/* Cheek blush */}
      <circle cx="10" cy="23" r="2.5" fill="hsl(var(--primary) / 0.2)" />
      <circle cx="30" cy="23" r="2.5" fill="hsl(var(--primary) / 0.2)" />
    </svg>
  );
}

function InstantMatchIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10 shrink-0" aria-hidden="true">
      {/* Left hand sliding right */}
      <g>
        <animateTransform attributeName="transform" type="translate" values="0,0;6,0;0,0" dur="2s" repeatCount="indefinite" />
        <path d="M6 22 Q4 18 8 16 L12 16 Q14 16 14 18 L14 22 Q14 24 12 24 L8 24 Q6 24 6 22Z" fill="hsl(var(--primary) / 0.3)" stroke="hsl(var(--primary))" strokeWidth="1.2" />
        <path d="M8 16 L8 12" stroke="hsl(var(--primary))" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M10 16 L10 11" stroke="hsl(var(--primary))" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M12 16 L12 12" stroke="hsl(var(--primary))" strokeWidth="1.5" strokeLinecap="round" />
      </g>
      {/* Right hand sliding left */}
      <g>
        <animateTransform attributeName="transform" type="translate" values="0,0;-6,0;0,0" dur="2s" repeatCount="indefinite" />
        <path d="M34 22 Q36 18 32 16 L28 16 Q26 16 26 18 L26 22 Q26 24 28 24 L32 24 Q34 24 34 22Z" fill="hsl(var(--primary) / 0.3)" stroke="hsl(var(--primary))" strokeWidth="1.2" />
        <path d="M32 16 L32 12" stroke="hsl(var(--primary))" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M30 16 L30 11" stroke="hsl(var(--primary))" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M28 16 L28 12" stroke="hsl(var(--primary))" strokeWidth="1.5" strokeLinecap="round" />
      </g>
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10 shrink-0" aria-hidden="true">
      {/* Chat bubble */}
      <path d="M6 10 Q6 6 10 6 L30 6 Q34 6 34 10 L34 22 Q34 26 30 26 L16 26 L10 32 L12 26 L10 26 Q6 26 6 22Z" fill="hsl(var(--primary) / 0.15)" stroke="hsl(var(--primary))" strokeWidth="1.5">
        <animate attributeName="stroke-width" values="1.5;2.5;1.5" dur="1.5s" repeatCount="indefinite" />
      </path>
      {/* Dots — typing/ding */}
      <circle cx="14" cy="16" r="2" fill="hsl(var(--primary))">
        <animate attributeName="r" values="2;2.8;2" dur="1.5s" repeatCount="indefinite" begin="0s" />
        <animate attributeName="opacity" values="1;0.5;1" dur="1.5s" repeatCount="indefinite" begin="0s" />
      </circle>
      <circle cx="20" cy="16" r="2" fill="hsl(var(--primary))">
        <animate attributeName="r" values="2;2.8;2" dur="1.5s" repeatCount="indefinite" begin="0.3s" />
        <animate attributeName="opacity" values="1;0.5;1" dur="1.5s" repeatCount="indefinite" begin="0.3s" />
      </circle>
      <circle cx="26" cy="16" r="2" fill="hsl(var(--primary))">
        <animate attributeName="r" values="2;2.8;2" dur="1.5s" repeatCount="indefinite" begin="0.6s" />
        <animate attributeName="opacity" values="1;0.5;1" dur="1.5s" repeatCount="indefinite" begin="0.6s" />
      </circle>
    </svg>
  );
}

function StarIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10 shrink-0" aria-hidden="true">
      {/* Star — flicker/sparkle */}
      <polygon
        points="20,4 23.5,14.5 34,14.5 25.5,21 28.5,32 20,25 11.5,32 14.5,21 6,14.5 16.5,14.5"
        fill="hsl(var(--primary) / 0.3)"
        stroke="hsl(var(--primary))"
        strokeWidth="1.5"
      >
        <animate attributeName="fill" values="hsl(var(--primary) / 0.3);hsl(var(--primary) / 0.6);hsl(var(--primary) / 0.3)" dur="1.8s" repeatCount="indefinite" />
        <animate attributeName="stroke-width" values="1.5;2.2;1.5" dur="1.8s" repeatCount="indefinite" />
      </polygon>
      {/* Sparkle rays */}
      <line x1="20" y1="1" x2="20" y2="3" stroke="hsl(var(--primary))" strokeWidth="1.2" strokeLinecap="round">
        <animate attributeName="opacity" values="0;1;0" dur="1.8s" repeatCount="indefinite" />
      </line>
      <line x1="20" y1="37" x2="20" y2="39" stroke="hsl(var(--primary))" strokeWidth="1.2" strokeLinecap="round">
        <animate attributeName="opacity" values="0;1;0" dur="1.8s" repeatCount="indefinite" begin="0.3s" />
      </line>
      <line x1="1" y1="18" x2="3" y2="18" stroke="hsl(var(--primary))" strokeWidth="1.2" strokeLinecap="round">
        <animate attributeName="opacity" values="0;1;0" dur="1.8s" repeatCount="indefinite" begin="0.6s" />
      </line>
      <line x1="37" y1="18" x2="39" y2="18" stroke="hsl(var(--primary))" strokeWidth="1.2" strokeLinecap="round">
        <animate attributeName="opacity" values="0;1;0" dur="1.8s" repeatCount="indefinite" begin="0.9s" />
      </line>
    </svg>
  );
}

function DollarIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10 shrink-0" aria-hidden="true">
      {/* Dollar sign floating up */}
      <g>
        <animateTransform attributeName="transform" type="translate" values="0,3;0,-3;0,3" dur="2s" repeatCount="indefinite" />
        <text x="20" y="26" textAnchor="middle" fontSize="22" fontWeight="bold" fill="hsl(var(--primary))" fontFamily="serif">$</text>
      </g>
      {/* Small coins floating */}
      <circle cx="30" cy="30" r="3" fill="hsl(var(--primary) / 0.2)" stroke="hsl(var(--primary))" strokeWidth="0.8">
        <animateTransform attributeName="transform" type="translate" values="0,0;-2,-6;0,0" dur="2.5s" repeatCount="indefinite" begin="0.3s" />
        <animate attributeName="opacity" values="0.6;0.2;0.6" dur="2.5s" repeatCount="indefinite" begin="0.3s" />
      </circle>
      <circle cx="10" cy="32" r="2" fill="hsl(var(--primary) / 0.2)" stroke="hsl(var(--primary))" strokeWidth="0.6">
        <animateTransform attributeName="transform" type="translate" values="0,0;2,-5;0,0" dur="2s" repeatCount="indefinite" begin="0.8s" />
        <animate attributeName="opacity" values="0.5;0.15;0.5" dur="2s" repeatCount="indefinite" begin="0.8s" />
      </circle>
    </svg>
  );
}

function CarIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10 shrink-0" aria-hidden="true">
      {/* Road lines scrolling underneath */}
      <line x1="5" y1="33" x2="35" y2="33" stroke="hsl(var(--muted-foreground) / 0.3)" strokeWidth="1" />
      <line x1="8" y1="36" x2="12" y2="36" stroke="hsl(var(--muted-foreground) / 0.3)" strokeWidth="1.5" strokeLinecap="round">
        <animateTransform attributeName="transform" type="translate" values="0,0;-20,0" dur="1s" repeatCount="indefinite" />
      </line>
      <line x1="18" y1="36" x2="22" y2="36" stroke="hsl(var(--muted-foreground) / 0.3)" strokeWidth="1.5" strokeLinecap="round">
        <animateTransform attributeName="transform" type="translate" values="0,0;-20,0" dur="1s" repeatCount="indefinite" />
      </line>
      <line x1="28" y1="36" x2="32" y2="36" stroke="hsl(var(--muted-foreground) / 0.3)" strokeWidth="1.5" strokeLinecap="round">
        <animateTransform attributeName="transform" type="translate" values="0,0;-20,0" dur="1s" repeatCount="indefinite" />
      </line>
      {/* Car body */}
      <g>
        <animateTransform attributeName="transform" type="translate" values="0,0;0,-0.8;0,0" dur="0.5s" repeatCount="indefinite" />
        {/* Body */}
        <path d="M4 24 L6 18 L12 12 L28 12 L34 18 L36 24 Q36 28 32 28 L8 28 Q4 28 4 24Z" fill="hsl(var(--primary) / 0.2)" stroke="hsl(var(--primary))" strokeWidth="1.3" />
        {/* Windows */}
        <path d="M12 12 L14 18 L20 18 L20 12Z" fill="hsl(var(--primary) / 0.1)" stroke="hsl(var(--primary))" strokeWidth="0.8" />
        <path d="M20 12 L20 18 L26 18 L28 12Z" fill="hsl(var(--primary) / 0.1)" stroke="hsl(var(--primary))" strokeWidth="0.8" />
        {/* Wheels */}
        <circle cx="12" cy="28" r="3.5" fill="hsl(var(--background))" stroke="hsl(var(--primary))" strokeWidth="1.3">
          <animateTransform attributeName="transform" type="rotate" values="0 12 28;360 12 28" dur="0.8s" repeatCount="indefinite" />
        </circle>
        <circle cx="28" cy="28" r="3.5" fill="hsl(var(--background))" stroke="hsl(var(--primary))" strokeWidth="1.3">
          <animateTransform attributeName="transform" type="rotate" values="0 28 28;360 28 28" dur="0.8s" repeatCount="indefinite" />
        </circle>
        {/* Wheel spokes */}
        <line x1="12" y1="25.5" x2="12" y2="30.5" stroke="hsl(var(--primary) / 0.5)" strokeWidth="0.6">
          <animateTransform attributeName="transform" type="rotate" values="0 12 28;360 12 28" dur="0.8s" repeatCount="indefinite" />
        </line>
        <line x1="9.5" y1="28" x2="14.5" y2="28" stroke="hsl(var(--primary) / 0.5)" strokeWidth="0.6">
          <animateTransform attributeName="transform" type="rotate" values="0 12 28;360 12 28" dur="0.8s" repeatCount="indefinite" />
        </line>
        <line x1="28" y1="25.5" x2="28" y2="30.5" stroke="hsl(var(--primary) / 0.5)" strokeWidth="0.6">
          <animateTransform attributeName="transform" type="rotate" values="0 28 28;360 28 28" dur="0.8s" repeatCount="indefinite" />
        </line>
        <line x1="25.5" y1="28" x2="30.5" y2="28" stroke="hsl(var(--primary) / 0.5)" strokeWidth="0.6">
          <animateTransform attributeName="transform" type="rotate" values="0 28 28;360 28 28" dur="0.8s" repeatCount="indefinite" />
        </line>
      </g>
    </svg>
  );
}

const featureIcons = [
  <VideoProfilesIcon key="video" />,
  <InstantMatchIcon key="match" />,
  <ChatIcon key="chat" />,
  <StarIcon key="star" />,
  <DollarIcon key="dollar" />,
  <CarIcon key="car" />,
];

export default function LandingScreen() {
  const { navigate } = useNav();

  return (
    <div className="h-full overflow-y-auto bg-background flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 px-4 py-3 flex items-center justify-between border-b border-border bg-background/90 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <InstallPrompt inline={true} />
        </div>
        <Button variant="ghost" size="sm" onClick={() => navigate("login")}>
          Log In
        </Button>
      </header>

      {/* Hero */}
      <section className="flex-shrink-0 px-5 pt-12 pb-10 text-center bg-gradient-to-b from-primary/10 via-primary/5 to-transparent">
        <img src="/dayshift-logo.png" alt="Day Shift" className="w-20 h-20 mx-auto mb-4" />
        <h1 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight leading-tight">
          Find Your Next<br /><span className="text-primary">Culinary Shift</span>
        </h1>
        <p className="text-muted-foreground mt-3 text-base leading-relaxed max-w-md mx-auto">
          The video-first marketplace connecting culinary workers with kitchens. Post shifts, find crew, and get matched today!
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center mt-6">
          <Button size="lg" onClick={() => navigate("register")} className="gap-2">
            Get Started <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </section>

      {/* Features — grid of cards */}
      <section className="flex-1 px-5 py-10">
        <h2 className="text-xl font-bold text-foreground text-center mb-6" style={{ fontFamily: "'Bebas Neue', sans-serif" }}>
          What Day Shift Does For You
        </h2>

        <div className="grid grid-cols-2 gap-3 max-w-lg mx-auto">
          {features.map((f, i) => (
            <div key={f.title} className="bg-card border border-border rounded-xl px-3 py-4 flex flex-col items-center text-center gap-2 hover:border-primary/30 transition-colors">
              {featureIcons[i]}
              <h3 className="font-semibold text-foreground text-sm leading-tight">{f.title}</h3>
              <p className="text-muted-foreground text-xs leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="px-5 py-6 border-t border-border text-center">
        <p className="text-xs text-muted-foreground mb-3">© 2026 Day Shift. All rights reserved.</p>
        <div className="flex justify-center gap-4 text-xs">
          <button onClick={() => navigate("advertise")} className="text-primary font-semibold hover:text-primary/80 transition-colors">
            Advertise with Us
          </button>
          <a href="mailto:contact@dayshiftnow.me" className="text-muted-foreground hover:text-foreground transition-colors">
            Email Us
          </a>
        </div>
      </footer>
    </div>
  );
}
