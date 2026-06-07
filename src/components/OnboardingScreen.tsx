import { useState } from "react";
import { useAuth, useNav } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Check, HardHat, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

const CUISINES = [
  "American", "Italian", "Mexican", "Asian", "French", "Mediterranean",
  "Latin", "Caribbean", "Japanese", "Indian", "Middle Eastern", "Southern",
  "BBQ", "Seafood", "Vegan/Vegetarian", "Pastry/Baking", "Other",
];

const EXPERIENCES = [
  "Entry Level (0-1 years)",
  "Junior (1-3 years)",
  "Mid-Level (3-5 years)",
  "Senior (5-10 years)",
  "Executive (10+ years)",
];

const SHIFTS = [
  "Morning (6am-2pm)",
  "Afternoon (2pm-10pm)",
  "Night (10pm-6am)",
  "Flexible",
];

export default function OnboardingScreen() {
  const { user, token, refreshUser } = useAuth();
  const { navigate } = useNav();
  const [step, setStep] = useState(user?.role ? 1 : 0);
  const [role, setRole] = useState<"worker" | "employer">(user?.role || "worker");
  const [location, setLocation] = useState("");
  const [cuisines, setCuisines] = useState<string[]>([]);
  const [experience, setExperience] = useState("");
  const [shifts, setShifts] = useState<string[]>([]);
  const [bio, setBio] = useState("");
  const [saving, setSaving] = useState(false);

  const steps = [
    { title: "What's your role?", subtitle: "Choose how you'll use Day Shift" },
    { title: "Where are you based?", subtitle: "So we can match you with nearby opportunities" },
    { title: "Tell us about yourself", subtitle: "Help kitchens or crew find you" },
  ];

  const toggleCuisine = (c: string) => {
    setCuisines((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : prev.length < 5 ? [...prev, c] : prev
    );
  };

  const toggleShift = (s: string) => {
    setShifts((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/auth/onboard", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          role,
          location,
          cuisine_type: cuisines.join(", "),
          experience_level: experience,
          hours: shifts.join(", "),
          bio,
        }),
      });
      if (res.ok) {
        await refreshUser();
        navigate("feed");
      }
    } finally {
      setSaving(false);
    }
  };

  const canNext =
    step === 0 ? true :
    step === 1 ? location.trim().length > 0 :
    step === 2 ? true : true;

  const hasRole = !!user?.role;
  const visibleSteps = hasRole ? steps.slice(1) : steps;
  const canFinish = step === 2 && (cuisines.length > 0 || experience || bio.trim());

  return (
    <div className="h-full flex flex-col bg-background overflow-y-auto">
      {/* Header */}
      <div className="flex-shrink-0 px-5 pt-5 pb-3">
        <h1 className="text-2xl text-foreground font-bold" style={{ fontFamily: "'Bebas Neue'" }}>
          {steps[step].title}
        </h1>
        <p className="text-muted-foreground text-xs">{steps[step].subtitle}</p>
        {/* Progress dots */}
        <div className="flex gap-2 mt-3">
          {visibleSteps.map((_, i) => (
            <div
              key={i}
              className={cn(
                "h-1 flex-1 rounded-full transition-colors",
                i <= (step - (hasRole ? 1 : 0)) ? "bg-primary" : "bg-secondary"
              )}
            />
          ))}
        </div>
      </div>

      {/* Step content */}
      <div className="flex-1 px-5 pb-5">
        {/* Step 0: Role */}
        {step === 0 && (
          <div className="space-y-4 pt-2">
            <button
              onClick={() => setRole("worker")}
              className={cn(
                "w-full p-5 rounded-2xl border-2 text-left transition-all",
                role === "worker"
                  ? "border-primary bg-primary/5"
                  : "border-border bg-card hover:border-primary/30"
              )}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-orange-500/20 flex items-center justify-center">
                  <HardHat className="w-6 h-6 text-orange-400" />
                </div>
                <div className="flex-1">
                  <p className="text-foreground font-semibold">I'm a Worker</p>
                  <p className="text-muted-foreground text-xs mt-0.5">Looking for shifts, gigs, and opportunities</p>
                </div>
                {role === "worker" && (
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                    <Check size={14} className="text-primary-foreground" />
                  </div>
                )}
              </div>
            </button>

            <button
              onClick={() => setRole("employer")}
              className={cn(
                "w-full p-5 rounded-2xl border-2 text-left transition-all",
                role === "employer"
                  ? "border-primary bg-primary/5"
                  : "border-border bg-card hover:border-primary/30"
              )}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                  <Building2 className="w-6 h-6 text-blue-400" />
                </div>
                <div className="flex-1">
                  <p className="text-foreground font-semibold">I'm a Kitchen</p>
                  <p className="text-muted-foreground text-xs mt-0.5">Hiring crew, posting shifts, building a team</p>
                </div>
                {role === "employer" && (
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                    <Check size={14} className="text-primary-foreground" />
                  </div>
                )}
              </div>
            </button>
          </div>
        )}

        {/* Step 1: Location */}
        {step === 1 && (
          <div className="space-y-4 pt-2">
            <Input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="City, state, or 'Willing to travel'"
              className="bg-secondary border-border text-base"
            />
            <div className="flex flex-wrap gap-2">
              {["New York", "Los Angeles", "Miami", "Chicago", "Atlanta", "Remote / Travel"].map((loc) => (
                <button
                  key={loc}
                  onClick={() => setLocation(loc)}
                  className={cn(
                    "px-3 py-1.5 rounded-full text-xs font-medium transition-colors",
                    location === loc
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground hover:text-foreground"
                  )}
                >
                  {loc}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Details */}
        {step === 2 && (
          <div className="space-y-5 pt-2">
            {/* Cuisines (worker) */}
            {role === "worker" && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-foreground uppercase tracking-wider">
                  Cuisines <span className="text-muted-foreground normal-case">(up to 5)</span>
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {CUISINES.map((c) => (
                    <button
                      key={c}
                      onClick={() => toggleCuisine(c)}
                      className={cn(
                        "px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors",
                        cuisines.includes(c)
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Experience */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-foreground uppercase tracking-wider">
                {role === "worker" ? "Experience Level" : "What are you looking for?"}
              </p>
              {role === "worker" ? (
                <div className="space-y-1.5">
                  {EXPERIENCES.map((exp) => (
                    <button
                      key={exp}
                      onClick={() => setExperience(exp)}
                      className={cn(
                        "w-full px-3 py-2.5 rounded-lg text-xs text-left transition-colors",
                        experience === exp
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {exp}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {["Line Cook", "Sous Chef", "Prep Cook", "Dishwasher", "Server", "Pastry", "Chef de Partie", "Executive Chef"].map((pos) => (
                    <button
                      key={pos}
                      onClick={() => setExperience(pos)}
                      className={cn(
                        "px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors",
                        experience === pos
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {pos}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Availability (shifts) */}
            {role === "worker" && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-foreground uppercase tracking-wider">Availability</p>
                <div className="flex flex-wrap gap-1.5">
                  {SHIFTS.map((s) => (
                    <button
                      key={s}
                      onClick={() => toggleShift(s)}
                      className={cn(
                        "px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors",
                        shifts.includes(s)
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Bio */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-foreground uppercase tracking-wider">Short bio (optional)</p>
              <textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder={role === "worker"
                  ? "Passionate line cook with 5 years of experience..."
                  : "Fine dining restaurant looking for talented crew..."}
                rows={3}
                className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground resize-none"
              />
            </div>
          </div>
        )}
      </div>

      {/* Footer buttons */}
      <div className="flex-shrink-0 px-5 pb-5 pt-2 border-t border-border bg-background">
        <div className="flex gap-3">
          {step > 0 && (
            <Button
              onClick={() => setStep(step - 1)}
              variant="outline"
              className="flex-none border-border text-muted-foreground"
            >
              Back
            </Button>
          )}
          {step < 2 ? (
            <Button
              onClick={() => setStep(step + 1)}
              disabled={!canNext}
              className="flex-1 bg-primary text-primary-foreground ember-glow"
            >
              Continue
            </Button>
          ) : (
            <Button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 bg-primary text-primary-foreground ember-glow"
            >
              {saving ? "Saving..." : "Get Started"}
            </Button>
          )}
        </div>
        {step < 2 && (
          <button
            onClick={handleSave}
            className="w-full text-center text-muted-foreground text-[11px] mt-3 hover:text-foreground transition-colors"
          >
            Skip for now
          </button>
        )}
      </div>
    </div>
  );
}
