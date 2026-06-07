import { useNav } from "../App";
import { TermsContent, PrivacyContent } from "./LegalContent";

export default function LegalScreen({ type }: { type: "terms" | "privacy" }) {
  const { navigate } = useNav();

  return (
    <div className="overflow-y-auto h-[calc(100vh-120px)] pb-6">
      <div className="px-4 pt-4 pb-3 border-b border-border flex items-center gap-3">
        <button
          onClick={() => navigate("feed")}
          className="text-muted-foreground hover:text-foreground transition-colors text-sm"
        >
          ← Back
        </button>
        <h1 className="text-lg font-bold text-foreground">
          {type === "terms" ? "Terms of Service" : "Privacy Policy"}
        </h1>
      </div>

      <div className="px-4 py-4 space-y-4">
        {type === "terms" ? <TermsContent /> : <PrivacyContent />}
      </div>

      <div className="px-4 pt-2 pb-4">
        <p className="text-xs text-muted-foreground text-center">
          Last updated: June 1, 2026
        </p>
      </div>
    </div>
  );
}
