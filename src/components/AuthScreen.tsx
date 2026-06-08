import { useRef, useState, useEffect } from "react";
import { useAuth, useNav } from "../App";
import type { User } from "../types";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TermsContent, PrivacyContent } from "./LegalContent";
import { Camera, Building2, X, Eye, EyeOff, HardHat } from "lucide-react";
import { trackEvent } from "../lib/analytics";

export default function AuthScreen({
  mode,
  tokenParam,
}: {
  mode: "login" | "register" | "forgot" | "reset" | "verify-email";
  tokenParam?: string;
}) {
  const { login } = useAuth();
  const { navigate } = useNav();

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "worker" as "worker" | "employer",
  });

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Signup gate
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [legalDialog, setLegalDialog] = useState<"terms" | "privacy" | null>(null);

  // ── Email verification: auto-verify on mount ──
  const [verifyState, setVerifyState] = useState<"verifying" | "success" | "error">("verifying");
  const [resendEmail, setResendEmail] = useState("");

  useEffect(() => {
    if (mode !== "verify-email" || !tokenParam) return;
    const doVerify = async () => {
      try {
        const res = await fetch("/api/auth/verify-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: tokenParam }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Verification failed");
        // Auto-login on success
        if (data.token && data.user) {
          login(data.token, data.user as User);
          trackEvent("email_verified", { role: data.user.role });
        }
        setVerifyState("success");
        // Redirect to feed after a brief success message
        setTimeout(() => navigate("feed"), 2000);
      } catch {
        setVerifyState("error");
      }
    };
    doVerify();
  }, [mode, tokenParam]);

  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const isWorker = form.role === "worker";
  const imageLabel = isWorker ? "Profile Photo" : "Company Logo or Profile Photo";
  const imageHint = isWorker
    ? "A clear photo of your face — helps spots recognize you"
    : "Your restaurant logo or a clear photo of your face — builds trust with crew";

  function handleImageChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  }

  function clearImage() {
    setImageFile(null);
    setImagePreview("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccessMsg("");

    try {
      if (mode === "forgot") {
        const res = await fetch("/api/auth/forgot-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: form.email }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Something went wrong");
        setSuccessMsg(data.message);
        return;
      }

      if (mode === "reset") {
        const res = await fetch("/api/auth/reset-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: tokenParam, new_password: form.password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Something went wrong");
        navigate("login");
        return;
      }

      if (mode === "login") {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: form.email, password: form.password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Something went wrong");
        const u: User = data.user;
        login(data.token, u);
        trackEvent("user_login", { role: u.role, method: "email" });
        navigate("feed");
        return;
      }

      // Register
      if (!imageFile) {
        setError(`${imageLabel} is required`);
        return;
      }

      if (!termsAccepted || !privacyAccepted) {
        setError("Please accept Terms of Use and Privacy Policy.");
        return;
      }

      const fd = new FormData();
      fd.append("name", form.name);
      fd.append("email", form.email);
      fd.append("password", form.password);
      fd.append("role", form.role);
      fd.append("image", imageFile);
      fd.append("terms_accepted", String(termsAccepted));
      fd.append("privacy_accepted", String(privacyAccepted));

      const res = await fetch("/api/auth/register", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Something went wrong");

      const u: User = data.user;
      login(data.token, u);
      trackEvent("user_registered", { role: u.role, method: "email" });
      // If email verification is pending, show message instead of going to feed
      if (!u.email_verified) {
        setSuccessMsg("Account created! Check your email to verify your account before posting.");
        return;
      }
      navigate("feed");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const canSubmitRegister =
    !!imageFile && termsAccepted && privacyAccepted;

  // Password strength for register form
  const pwStrength = (() => {
    const p = form.password;
    if (!p) return { score: 0, label: "", color: "" };
    let score = 0;
    if (p.length >= 8) score++;
    if (p.length >= 12) score++;
    if (/[a-zA-Z]/.test(p)) score++;
    if (/[0-9]/.test(p)) score++;
    if (/[^a-zA-Z0-9]/.test(p)) score++;
    if (score <= 2) return { score, label: "Weak", color: "bg-red-500" };
    if (score <= 3) return { score, label: "Fair", color: "bg-amber-500" };
    return { score, label: "Strong", color: "bg-green-500" };
  })();

  return (
    <div className="h-full flex flex-col bg-background overflow-y-auto [overflow-y:scroll] [-webkit-overflow-scrolling:touch]">
      {/* ── Verify Email Screen ── */}
      {mode === "verify-email" ? (
        <div className="flex-1 flex flex-col items-center justify-center px-6 max-w-sm mx-auto w-full">
          <img
            src="/dayshift-logo.png"
            alt="Day Shift"
            className="h-16 w-auto mb-6"
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
          />
          {verifyState === "verifying" && (
            <>
              <div className="w-10 h-10 border-3 border-primary border-t-transparent rounded-full animate-spin mb-4" />
              <h2 className="text-xl font-bold text-foreground mb-2">Verifying your email…</h2>
              <p className="text-muted-foreground text-sm text-center">Hang tight, we're confirming your account.</p>
            </>
          )}
          {verifyState === "success" && (
            <>
              <div className="w-14 h-14 rounded-full bg-green-500/15 flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
              </div>
              <h2 className="text-xl font-bold text-foreground mb-2">Email Verified!</h2>
              <p className="text-muted-foreground text-sm text-center">You're all set. Redirecting to your feed…</p>
            </>
          )}
          {verifyState === "error" && (
            <>
              <div className="w-14 h-14 rounded-full bg-destructive/15 flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </div>
              <h2 className="text-xl font-bold text-foreground mb-2">Verification Failed</h2>
              <p className="text-muted-foreground text-sm text-center mb-6">This link may have expired or already been used. Enter your email to get a new one.</p>
              <div className="w-full space-y-3">
                <Input
                  type="email"
                  placeholder="Your email address"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  className="bg-secondary border-border h-11"
                />
                <Button
                  className="w-full h-11 bg-primary text-primary-foreground hover:bg-primary/90 ember-glow"
                  disabled={!resendEmail || loading}
                  onClick={async () => {
                    setLoading(true);
                    setError("");
                    setSuccessMsg("");
                    try {
                      const res = await fetch("/api/auth/resend-verification", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email: resendEmail }),
                      });
                      const data = await res.json();
                      if (!res.ok) throw new Error(data.detail || "Failed to resend");
                      setSuccessMsg(data.message);
                    } catch (err: unknown) {
                      setError(err instanceof Error ? err.message : "Something went wrong");
                    } finally {
                      setLoading(false);
                    }
                  }}
                >
                  {loading ? <div className="w-5 h-5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" /> : "Resend Verification"}
                </Button>
                {successMsg && <p className="text-green-500 text-sm text-center bg-green-500/10 rounded-lg py-2 px-3">{successMsg}</p>}
                {error && <p className="text-destructive text-sm text-center bg-destructive/10 rounded-lg py-2 px-3">{error}</p>}
              </div>
              <button
                type="button"
                onClick={() => navigate("login")}
                className="text-primary font-medium hover:underline text-sm mt-4"
              >
                Back to Sign In
              </button>
            </>
          )}
        </div>
      ) : mode === "login" ? (
        <form onSubmit={handleSubmit} className="flex flex-col h-full w-full max-w-sm mx-auto">
          {/* Top: Logo + Slogan — front and center */}
          <div className="flex-1 flex flex-col items-center justify-center px-4 min-h-[200px] pb-4">
            <img
              src="/dayshift-logo.png"
              alt="Day Shift"
              className="h-20 sm:h-28 md:h-36 w-auto mx-auto mb-2"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = "none";
              }}
            />
            <p className="text-muted-foreground text-[10px] sm:text-xs tracking-[0.2em] uppercase font-semibold text-center px-2">
              Built for Culinarians That Move Fast
            </p>
            <p className="text-muted-foreground text-xs text-center px-4 mt-1">
              Match with your next shift — workers and kitchens, one feed.
            </p>
          </div>

          {/* Bottom: Form + Sign In */}
          <div className="px-4 pb-4 sm:pb-8 space-y-4 shrink-0">
            {/* Honeypot fields — trick browser into not showing password manager UI on real fields */}
            <input type="text" name="username" style={{display:"none"}} readOnly tabIndex={-1} aria-hidden="true" />
            <input type="password" name="password" style={{display:"none"}} readOnly tabIndex={-1} aria-hidden="true" />
            <div className="flex flex-col gap-1.5">
              <Input
                id="ds-email"
                name="ds-email"
                type="text"
                inputMode="email"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                data-1p-ignore
                data-lpignore="true"
                data-form-type="other"
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
                placeholder="Email"
                required
                className="bg-secondary border-border h-11"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <div className="relative">
                <Input
                  id="ds-pass"
                  name="ds-pass"
                  type={showPassword ? "text" : "password"}
                  autoComplete="off"
                  data-1p-ignore
                  data-lpignore="true"
                  data-form-type="other"
                  value={form.password}
                  onChange={(e) => set("password", e.target.value)}
                  placeholder="Password"
                  required
                  minLength={8}
                  className="bg-secondary border-border h-11 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {form.password && mode === "register" && (
                <div className="space-y-1 mt-1">
                  <div className="flex gap-1">
                    {[1,2,3,4,5].map(i => (
                      <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${i <= pwStrength.score ? pwStrength.color : "bg-muted"}`} />
                    ))}
                  </div>
                  <p className={`text-xs ${pwStrength.score <= 2 ? "text-red-500" : pwStrength.score <= 3 ? "text-amber-500" : "text-green-500"}`}>
                    {pwStrength.label} — 8+ chars, a letter, a number
                  </p>
                </div>
              )}
              <div className="flex justify-between items-center">
                <button
                  type="button"
                  onClick={() => {
                    setResendEmail(form.email);
                    setVerifyState("error"); // reuse the resend UI from verify-email screen
                    navigate("verify-email");
                  }}
                  className="text-xs text-muted-foreground hover:text-primary transition-colors"
                >
                  Resend verification
                </button>
                <button
                  type="button"
                  onClick={() => navigate("forgot")}
                  className="text-xs text-primary hover:underline"
                >
                  Forgot password?
                </button>
              </div>
            </div>

            {error && (
              <div className="text-destructive text-sm text-center bg-destructive/10 rounded-lg py-2 px-3">
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-11 text-sm font-medium bg-secondary text-foreground hover:bg-secondary/80 border border-border disabled:opacity-50"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
              ) : (
                "Sign In"
              )}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              New here?{" "}
              <button
                type="button"
                onClick={() => navigate("register")}
                className="text-primary font-medium hover:underline"
              >
                Create account
              </button>
            </p>
          </div>
        </form>
      ) : (
      <form onSubmit={handleSubmit} className="w-full max-w-sm mx-auto flex flex-col gap-5 px-4 py-8">
        <div className="flex flex-col items-center gap-1 mb-2">
          <img
            src="/dayshift-logo.png"
            alt="Day Shift"
            className="h-32 w-auto mx-auto mb-2"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
        </div>

        <h1 className="text-xl font-bold text-center text-foreground">
          {mode === "forgot"
            ? "Reset your password"
            : mode === "reset"
            ? "Choose a new password"
            : "Create your account"}
        </h1>

        {mode === "register" && (
          <div className="grid grid-cols-2 gap-2">
            {(["worker", "employer"] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => set("role", r)}
                className={`rounded-xl py-3 text-sm font-semibold border transition-all flex items-center justify-center gap-1 ${
                  form.role === r
                    ? "bg-primary text-primary-foreground border-primary ember-glow"
                    : "bg-secondary text-muted-foreground border-border hover:border-primary/50"
                }`}
              >
                {r === "worker" ? (
                  <><HardHat size={14} /> Crew</>
                ) : (
                  <><Building2 size={14} /> Kitchen</>
                )}
              </button>
            ))}
          </div>
        )}

        {mode === "register" && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="name">Full Name</Label>
            <Input
              id="name"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="Your name"
              required
              className="bg-secondary border-border"
            />
          </div>
        )}

        {mode === "register" && (
          <div className="flex flex-col gap-1.5">
            <Label>
              {imageLabel}
              <span className="text-destructive ml-1">*</span>
            </Label>
            <p className="text-xs text-muted-foreground -mt-1">{imageHint}</p>

            {imagePreview ? (
              <div className="relative self-start">
                <div
                  className={`overflow-hidden border-2 border-primary ${
                    isWorker ? "w-24 h-24 rounded-full" : "w-28 h-28 rounded-xl"
                  }`}
                >
                  <img src={imagePreview} alt="Preview" className="w-full h-full object-cover" />
                </div>
                <button
                  type="button"
                  onClick={clearImage}
                  className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground rounded-full w-6 h-6 flex items-center justify-center shadow"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center gap-2 border-2 border-dashed border-border rounded-xl p-6 text-muted-foreground hover:border-primary/60 hover:text-primary transition-all bg-secondary`}
              >
                {isWorker ? <Camera className="w-8 h-8" /> : <Building2 className="w-8 h-8" />}
                <span className="text-sm font-medium">Tap to upload {imageLabel.toLowerCase()}</span>
                <span className="text-xs opacity-60">JPG, PNG, WebP — max 10 MB</span>
              </button>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              className="hidden"
              onChange={handleImageChange}
            />
          </div>
        )}

        {mode === "register" && (
          <div className="flex flex-col gap-3">
            <div className="space-y-2">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="mt-1"
                />
                <span className="text-sm text-foreground">
                  I agree to the <button type="button" onClick={() => setLegalDialog("terms")} className="text-primary underline">Terms of Use</button> (required)
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
                  I agree to the <button type="button" onClick={() => setLegalDialog("privacy")} className="text-primary underline">Privacy Policy</button> (required)
                </span>
              </label>
            </div>
          </div>
        )}

        {mode !== "reset" && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="off"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              placeholder="you@example.com"
              required
              className="bg-secondary border-border"
            />
          </div>
        )}

        {(mode === "login" || mode === "register" || mode === "reset") && (
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center">
              <Label htmlFor="password">Password</Label>
              {mode === "login" && (
                <button
                  type="button"
                  onClick={() => navigate("forgot")}
                  className="text-xs text-primary hover:underline"
                >
                  Forgot password?
                </button>
              )}
            </div>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                value={form.password}
                onChange={(e) => set("password", e.target.value)}
                placeholder="••••••••"
                required
                minLength={6}
                className="bg-secondary border-border pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        )}

        {successMsg && (
          <div className="text-green-500 text-sm text-center bg-green-500/10 rounded-lg py-3 px-3">
            {successMsg}
            {successMsg.includes("verify") && (
              <button
                type="button"
                onClick={() => navigate("feed")}
                className="block mx-auto mt-2 text-primary font-semibold hover:underline text-sm"
              >
                Continue to Feed →
              </button>
            )}
          </div>
        )}

        {error && (
          <div className="text-destructive text-sm text-center bg-destructive/10 rounded-lg py-2 px-3">
            {error}
          </div>
        )}

        <Button
          type="submit"
          disabled={
            loading ||
            (mode === "register" ? !canSubmitRegister : false)
          }
          className="w-full h-12 text-base font-semibold bg-primary text-primary-foreground hover:bg-primary/90 ember-glow disabled:opacity-50"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
          ) : mode === "login" ? (
            "Sign In"
          ) : mode === "forgot" ? (
            "Send Reset Link"
          ) : mode === "reset" ? (
            "Reset Password"
          ) : (
            "Create Account"
          )}
        </Button>

        {mode !== "reset" && (
          <p className="text-center text-sm text-muted-foreground">
            {mode === "login" ? "New here?" : mode === "forgot" ? "Remember your password?" : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() =>
                navigate(
                  mode === "forgot" ? "login" : "login"
                )
              }
              className="text-primary font-medium hover:underline"
            >
              Sign in
            </button>
          </p>
        )}
      </form>
      )}
      <Dialog open={!!legalDialog} onOpenChange={(v) => { if (!v) setLegalDialog(null); }}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {legalDialog === "terms" ? "Terms of Service" : "Privacy Policy"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {legalDialog === "terms" ? <TermsContent /> : <PrivacyContent />}
          </div>
          <p className="text-xs text-muted-foreground text-center pt-2">
            Last updated: June 1, 2026
          </p>
        </DialogContent>
      </Dialog>
    </div>
  );
}
