import { useState, useEffect } from "react";

interface TickerQuote {
  photo: string;
  author: string;
  text: string;
  scope: string;
}

export default function TickerTape() {
  const [quotes, setQuotes] = useState<TickerQuote[]>([]);
  const [visibleIdx, setVisibleIdx] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    fetch("/api/ticker")
      .then((r) => (r.ok ? r.json() : { stats: [] }))
      .then((d) => {
        if (d.stats?.length) setQuotes(d.stats);
      })
      .catch(() => {});
  }, []);

  // Rotate through quotes every 10 seconds (pause on hover)
  useEffect(() => {
    if (quotes.length <= 1 || paused) return;
    const interval = setInterval(() => {
      setVisibleIdx((prev) => (prev + 1) % quotes.length);
    }, 10000);
    return () => clearInterval(interval);
  }, [quotes.length, paused]);

  if (quotes.length === 0) return null;

  const current = quotes[visibleIdx];

  return (
    <div
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      className="w-full h-full border-y border-amber-500/25 overflow-hidden flex items-center relative"
    >
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-amber-500/20 via-orange-500/10 to-amber-600/20" />

      {/* Background portrait — large, blurred, low opacity */}
      {current.photo && (
        <img
          key={`bg-${visibleIdx}`}
          src={current.photo}
          alt=""
          className="absolute inset-0 w-full h-full object-cover opacity-[0.12] scale-110 blur-sm"
        />
      )}

      {/* Diagonal shimmer lines */}
      <div className="absolute inset-0 pointer-events-none" style={{
        backgroundImage: `repeating-linear-gradient(
          -45deg,
          transparent,
          transparent 40px,
          rgba(251, 191, 36, 0.04) 40px,
          rgba(251, 191, 36, 0.04) 42px
        )`
      }} />

      {/* Dark overlay for contrast */}
      <div className="absolute inset-0 bg-black/20" />

      {/* Content */}
      <div
        key={visibleIdx}
        className="flex items-center gap-4 px-4 py-4 animate-ticker-fade w-full relative z-10"
      >
        {/* Author photo */}
        <div className="shrink-0 w-14 h-14 rounded-full overflow-hidden ring-2 ring-amber-500/40 shadow-lg">
          {current.photo ? (
            <img src={current.photo} alt={current.author} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-amber-500/20 flex items-center justify-center text-amber-400 text-lg font-bold">
              {current.author?.[0]?.toUpperCase() || "?"}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground/90 leading-relaxed italic">
            {current.text}
          </p>
          <p className="text-xs text-amber-400/80 font-semibold mt-1">
            — {current.author}
          </p>
        </div>
        {quotes.length > 1 && (
          <div className="shrink-0 flex flex-col items-end gap-1.5">
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {visibleIdx + 1}/{quotes.length}
            </span>
            <div className="flex gap-0.5">
              {quotes.slice(0, Math.min(quotes.length, 8)).map((_, i) => (
                <div
                  key={i}
                  className={`w-1.5 h-1.5 rounded-full transition-colors ${
                    i === visibleIdx ? "bg-amber-500" : "bg-muted-foreground/20"
                  }`}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
