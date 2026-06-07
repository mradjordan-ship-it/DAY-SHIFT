import { useState } from "react";
import { useAuth, useNav } from "../App";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Star, ArrowLeft } from "lucide-react";

export default function ReviewScreen({
  matchId,
  revieweeId,
  revieweeName,
}: {
  matchId: number;
  revieweeId: number;
  revieweeName: string;
}) {
  const { token } = useAuth();
  const { navigate } = useNav();
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!rating) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(`/api/matches/${matchId}/review/${revieweeId}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ rating, feedback }),
      });
      if (res.ok) {
        setDone(true);
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to submit review");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const ratingLabels = ["", "Poor", "Below Average", "Good", "Great", "Excellent"];

  return (
    <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
      <div className="p-4">
        <button
          onClick={() => navigate("matches")}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6"
        >
          <ArrowLeft size={18} /> Back to Matches
        </button>
      </div>

      {done ? (
        <div className="flex flex-col items-center justify-center py-16 text-center px-6">
          <div className="text-6xl mb-4">⭐</div>
          <h2 className="text-3xl text-foreground mb-2" style={{ fontFamily: "'Bebas Neue'" }}>
            Review Submitted!
          </h2>
          <p className="text-muted-foreground text-sm mb-8">
            Your feedback helps build trust in the Day Shift community
          </p>
          <Button onClick={() => navigate("matches")} className="bg-primary text-primary-foreground ember-glow w-full max-w-xs">
            Back to Matches
          </Button>
        </div>
      ) : (
        <div className="px-5">
          <div className="mb-8 text-center">
            <h2 className="text-3xl text-foreground mb-1" style={{ fontFamily: "'Bebas Neue'" }}>
              Rate Your Experience
            </h2>
            <p className="text-muted-foreground text-sm">
              How was your shift with <span className="text-foreground font-medium">{revieweeName}</span>?
            </p>
          </div>

          {/* Star selector */}
          <div className="flex justify-center gap-3 mb-2">
            {[1, 2, 3, 4, 5].map((s) => (
              <button
                key={s}
                onMouseEnter={() => setHover(s)}
                onMouseLeave={() => setHover(0)}
                onClick={() => setRating(s)}
                className="transition-transform hover:scale-110 active:scale-90"
              >
                <Star
                  size={40}
                  className={`transition-colors ${
                    s <= (hover || rating)
                      ? "fill-primary text-primary"
                      : "text-border"
                  }`}
                />
              </button>
            ))}
          </div>

          {(hover || rating) > 0 && (
            <p className="text-center text-primary text-sm font-medium mb-6">
              {ratingLabels[hover || rating]}
            </p>
          )}

          <div className="space-y-3 mt-4">
            <Textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Share your experience (optional)..."
              rows={4}
              className="bg-secondary border-border resize-none"
            />

            {error && (
              <div className="text-destructive text-sm text-center bg-destructive/10 rounded-lg py-2 px-3">
                {error}
              </div>
            )}

            <Button
              onClick={handleSubmit}
              disabled={!rating || submitting}
              className="w-full bg-primary text-primary-foreground ember-glow h-12"
            >
              {submitting ? (
                <div className="w-5 h-5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
              ) : "Submit Review"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
