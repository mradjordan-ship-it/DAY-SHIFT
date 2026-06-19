import { useState, useEffect, useCallback } from "react";

/**
 * Animated female chef character that tours through Day Shift features.
 *
 * Aesthetic: warm editorial illustration — bold silhouettes, amber/orange palette,
 * confident pose transitions, speech bubbles with punchy copy.
 * Each feature auto-advances every 4 s with a smooth character animation.
 */

const FEATURES = [
  {
    title: "Video Profiles",
    bubble: "Show 'em what you got! Post a 60-second video — your skills, your kitchen, your vibe. 💪",
    pose: "point-right" as const,
    emoji: "📹",
  },
  {
    title: "Instant Matching",
    bubble: "Swipe, match, done. No waiting for callbacks — when both sides say yes, you're connected. ⚡",
    pose: "fist-pump" as const,
    emoji: "🤝",
  },
  {
    title: "Built-In Chat",
    bubble: "Talk it out right here. Shift details, start times, whatever — no need to swap numbers. 💬",
    pose: "chat" as const,
    emoji: "💬",
  },
  {
    title: "Reviews & Ratings",
    bubble: "Your rep speaks for you. Leave reviews, earn stars — the best connections find you first. ⭐",
    pose: "star" as const,
    emoji: "⭐",
  },
  {
    title: "For Sale & Events",
    bubble: "Sell equipment, post gigs, promote events. This ain't just a job board — it's a community. 🏪",
    pose: "present" as const,
    emoji: "🏪",
  },
  {
    title: "Ride Integration",
    bubble: "One tap → Uber or Lyft pulls up with the kitchen's address. Never be late again. 🚗",
    pose: "cruiser" as const,
    emoji: "🚗",
  },
];

type Pose = "idle" | "point-right" | "fist-pump" | "chat" | "star" | "present" | "cruiser";

/* ── SVG Character ──────────────────────────────────────────────────────── */

function ChefSVG({ pose }: { pose: Pose }) {
  // Arm rotation offsets per pose
  const leftArm: Record<Pose, string> = {
    idle: "rotate(-5 55 170)",
    "point-right": "rotate(30 55 170)",
    "fist-pump": "rotate(-60 55 170)",
    chat: "rotate(-10 55 170)",
    star: "rotate(-40 55 170)",
    present: "rotate(15 55 170)",
    cruiser: "rotate(10 55 170)",
  };
  const rightArm: Record<Pose, string> = {
    idle: "rotate(5 145 170)",
    "point-right": "rotate(-40 145 170)",
    "fist-pump": "rotate(40 145 170)",
    chat: "rotate(20 145 170)",
    star: "rotate(60 145 170)",
    present: "rotate(-15 145 170)",
    cruiser: "rotate(-20 145 170)",
  };
  const headTilt: Record<Pose, string> = {
    idle: "rotate(0 100 70)",
    "point-right": "rotate(5 100 70)",
    "fist-pump": "rotate(-8 100 70)",
    chat: "rotate(-3 100 70)",
    star: "rotate(6 100 70)",
    present: "rotate(-5 100 70)",
    cruiser: "rotate(8 100 70)",
  };

  return (
    <svg viewBox="0 0 200 300" className="w-full h-full" aria-hidden="true">
      {/* Body group — gentle sway */}
      <g style={{ transformOrigin: "100px 150px", animation: "chef-sway 3s ease-in-out infinite" }}>
        {/* Chef hat */}
        <g style={{ transform: headTilt[pose], transformOrigin: "100px 70px", transition: "transform 0.6s cubic-bezier(.34,1.56,.64,1)" }}>
          {/* Hat base */}
          <rect x="68" y="28" width="64" height="16" rx="4" fill="#FEF3C7" />
          {/* Hat puff */}
          <ellipse cx="100" cy="24" rx="34" ry="20" fill="#FFFBEB" />
          <ellipse cx="86" cy="20" rx="18" ry="14" fill="#FEF3C7" />
          <ellipse cx="114" cy="20" rx="18" ry="14" fill="#FEF3C7" />
          <ellipse cx="100" cy="14" rx="20" ry="12" fill="white" />

          {/* Head */}
          <ellipse cx="100" cy="68" rx="28" ry="30" fill="#C68642" />

          {/* Hair — dark curls peaking from under hat */}
          <ellipse cx="74" cy="56" rx="10" ry="14" fill="#1C1917" />
          <ellipse cx="126" cy="56" rx="10" ry="14" fill="#1C1917" />
          <ellipse cx="72" cy="70" rx="8" ry="16" fill="#1C1917" />
          <ellipse cx="128" cy="70" rx="8" ry="16" fill="#1C1917" />

          {/* Face */}
          {/* Eyes */}
          <ellipse cx="90" cy="64" rx="3.5" ry="4" fill="#1C1917" />
          <ellipse cx="110" cy="64" rx="3.5" ry="4" fill="#1C1917" />
          {/* Eye shine */}
          <circle cx="91.5" cy="62.5" r="1.2" fill="white" />
          <circle cx="111.5" cy="62.5" r="1.2" fill="white" />
          {/* Eyebrows */}
          <path d="M85 57 Q90 54 95 57" stroke="#1C1917" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          <path d="M105 57 Q110 54 115 57" stroke="#1C1917" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          {/* Confident smile */}
          <path d="M93 77 Q100 84 107 77" stroke="#1C1917" strokeWidth="1.8" fill="none" strokeLinecap="round" />
          {/* Nose */}
          <path d="M100 68 Q102 72 100 74" stroke="#A0612B" strokeWidth="1.2" fill="none" strokeLinecap="round" />
        </g>

        {/* Neck */}
        <rect x="92" y="96" width="16" height="12" rx="4" fill="#C68642" />

        {/* Chef coat — body */}
        <rect x="68" y="106" width="64" height="80" rx="10" fill="white" />
        {/* Coat buttons */}
        <circle cx="100" cy="120" r="2.5" fill="#D4D4D8" />
        <circle cx="100" cy="134" r="2.5" fill="#D4D4D8" />
        <circle cx="100" cy="148" r="2.5" fill="#D4D4D8" />
        {/* Collar */}
        <path d="M82 108 L100 118 L118 108" stroke="#E5E7EB" strokeWidth="2" fill="none" />

        {/* Apron */}
        <path d="M78 140 L78 210 Q100 220 122 210 L122 140" fill="#F97316" opacity="0.85" />
        {/* Apron strings */}
        <path d="M78 140 Q70 138 68 130" stroke="#F97316" strokeWidth="2" fill="none" />
        <path d="M122 140 Q130 138 132 130" stroke="#F97316" strokeWidth="2" fill="none" />
        {/* Day Shift logo on apron — small flame */}
        <path d="M96 172 Q100 162 104 172 Q100 168 96 172Z" fill="#FFFBEB" opacity="0.9" />

        {/* Left arm */}
        <g style={{ transform: leftArm[pose], transformOrigin: "55px 170px", transition: "transform 0.6s cubic-bezier(.34,1.56,.64,1)" }}>
          <path d="M72 114 Q50 140 55 175" stroke="white" strokeWidth="16" strokeLinecap="round" fill="none" />
          <circle cx="55" cy="175" r="8" fill="#C68642" />
        </g>

        {/* Right arm */}
        <g style={{ transform: rightArm[pose], transformOrigin: "145px 170px", transition: "transform 0.6s cubic-bezier(.34,1.56,.64,1)" }}>
          <path d="M128 114 Q150 140 145 175" stroke="white" strokeWidth="16" strokeLinecap="round" fill="none" />
          <circle cx="145" cy="175" r="8" fill="#C68642" />
        </g>

        {/* Legs */}
        <rect x="80" y="186" width="16" height="60" rx="6" fill="#1C1917" />
        <rect x="104" y="186" width="16" height="60" rx="6" fill="#1C1917" />
        {/* Shoes */}
        <ellipse cx="88" cy="248" rx="12" ry="6" fill="#78350F" />
        <ellipse cx="112" cy="248" rx="12" ry="6" fill="#78350F" />
      </g>
    </svg>
  );
}

/* ── Speech Bubble ──────────────────────────────────────────────────────── */

function SpeechBubble({ text, visible }: { text: string; visible: boolean }) {
  return (
    <div
      className="relative bg-card border border-border rounded-2xl px-5 py-4 shadow-lg transition-all duration-500"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0) scale(1)" : "translateY(12px) scale(0.95)",
      }}
    >
      {/* Tail pointing left toward character */}
      <div className="absolute -left-3 top-6 w-0 h-0 border-t-8 border-t-transparent border-r-[12px] border-r-card border-b-8 border-b-transparent" />
      <div className="absolute -left-[14px] top-[22px] w-0 h-0 border-t-[7px] border-t-transparent border-r-[11px] border-r-border border-b-[7px] border-b-transparent opacity-30" />
      <p className="text-foreground text-sm md:text-base leading-relaxed font-medium">{text}</p>
    </div>
  );
}

/* ── Feature Tour Component ─────────────────────────────────────────────── */

export default function ChefCharacter() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [bubbleVisible, setBubbleVisible] = useState(true);

  const advance = useCallback(() => {
    setBubbleVisible(false);
    setTimeout(() => {
      setActiveIndex((i) => (i + 1) % FEATURES.length);
      setBubbleVisible(true);
    }, 400);
  }, []);

  useEffect(() => {
    const timer = setInterval(advance, 4000);
    return () => clearInterval(timer);
  }, [advance]);

  const feature = FEATURES[activeIndex];

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Feature title indicator */}
      <div className="flex items-center justify-center gap-2 mb-4">
        <span className="text-2xl">{feature.emoji}</span>
        <h3
          className="text-lg font-bold text-primary transition-all duration-300"
          style={{ fontFamily: "'Bebas Neue', sans-serif" }}
          key={feature.title}
        >
          {feature.title}
        </h3>
      </div>

      {/* Main layout: character left, speech bubble right */}
      <div className="flex items-start gap-4 md:gap-6">
        {/* Character */}
        <div className="w-28 md:w-36 shrink-0">
          <ChefSVG pose={feature.pose} />
        </div>

        {/* Speech bubble */}
        <div className="flex-1 min-w-0 pt-4">
          <SpeechBubble key={activeIndex} text={feature.bubble} visible={bubbleVisible} />
        </div>
      </div>

      {/* Progress dots */}
      <div className="flex justify-center gap-2 mt-5">
        {FEATURES.map((_, i) => (
          <button
            key={i}
            onClick={() => {
              setBubbleVisible(false);
              setTimeout(() => {
                setActiveIndex(i);
                setBubbleVisible(true);
              }, 300);
            }}
            className="transition-all duration-300 rounded-full"
            style={{
              width: i === activeIndex ? "24px" : "8px",
              height: "8px",
              backgroundColor: i === activeIndex ? "hsl(var(--primary))" : "hsl(var(--muted-foreground) / 0.3)",
            }}
            aria-label={`Go to feature: ${FEATURES[i].title}`}
          />
        ))}
      </div>
    </div>
  );
}
