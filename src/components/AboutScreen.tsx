import { useNav } from "../App";
import { Button } from "@/components/ui/button";
import { ChefHat, Video, MessageCircle, Star, CarFront, ShieldCheck, Zap, Users, Briefcase, Share2, ChefHat as CrewIcon, Store } from "lucide-react";

const features = [
  {
    icon: <Video className="w-6 h-6 text-primary" />,
    title: "Video Profiles",
    desc: "Create a short video to showcase your skills, personality, or kitchen. Posts get up to 60 seconds — stand out visually.",
  },
  {
    icon: <Zap className="w-6 h-6 text-primary" />,
    title: "Instant Matching",
    desc: "Swipe through crew and kitchens. When both sides match, you're connected instantly — no waiting for callbacks.",
  },
  {
    icon: <MessageCircle className="w-6 h-6 text-primary" />,
    title: "Built-In Chat",
    desc: "Message your matches directly. Discuss details, confirm shifts, and coordinate — all within the app.",
  },
  {
    icon: <Star className="w-6 h-6 text-primary" />,
    title: "Reviews & Ratings",
    desc: "Leave reviews after working together. Build your reputation over time so the best connections find you first.",
  },
  {
    icon: <CarFront className="w-6 h-6 text-primary" />,
    title: "Ride Links",
    desc: "Need a ride to your shift? One tap opens Uber or Lyft with the kitchen's address pre-loaded.",
  },
  {
    icon: <ShieldCheck className="w-6 h-6 text-primary" />,
    title: "Report & Block",
    desc: "Stay safe. Report inappropriate content or block users. We take every report seriously.",
  },
  {
    icon: <Briefcase className="w-6 h-6 text-primary" />,
    title: "For Sale & Events",
    desc: "Sell kitchen equipment, post open positions, or promote events. Beyond matching — a full community hub.",
  },
  {
    icon: <Users className="w-6 h-6 text-primary" />,
    title: "For Everyone",
    desc: "Whether you're a line cook, prep cook, dishwasher, sous chef, caterer, or restaurant owner — Day Shift is for you.",
  },
];

export default function AboutScreen() {
  const { navigate } = useNav();

  const shareAbout = async () => {
    const url = `${window.location.origin}/?screen=about`;
    if (navigator.share) {
      try {
        await navigator.share({ title: "Day Shift — Find Your Next Culinary Shift", text: "The video-first platform connecting crew with kitchens.", url });
      } catch { /* user cancelled */ }
    } else {
      await navigator.clipboard.writeText(url).catch(() => {});
    }
  };

  return (
    <div className="min-h-full bg-background flex flex-col">
      {/* Hero */}
      <div className="flex-shrink-0 px-5 pt-8 pb-6 text-center bg-gradient-to-b from-primary/10 to-transparent">
        <img src="/dayshift-logo.png" alt="Day Shift" className="w-16 h-16 mx-auto mb-3" />
        <h1 className="text-3xl font-bold text-foreground tracking-tight">Day Shift</h1>
        <p className="text-muted-foreground mt-1 text-sm leading-relaxed max-w-xs mx-auto">
          The video-first platform connecting culinary crew with kitchens. Short videos. Real matches. Less hassle.
        </p>
      </div>

      {/* How It Works */}
      <div className="flex-1 px-5 pb-8 space-y-6">
        <div className="space-y-3">
          <h2 className="text-lg font-bold text-foreground">How It Works</h2>

          <div className="space-y-4">
            {/* For Crew */}
            <div className="rounded-xl border border-border bg-card p-4 space-y-3">
              <div className="flex items-center gap-2">
                <CrewIcon className="w-5 h-5 text-orange-400" />
                <h3 className="font-bold text-foreground">For Crew</h3>
              </div>
              <ol className="space-y-2 text-sm text-muted-foreground">
                <li className="flex gap-2">
                  <span className="text-primary font-bold shrink-0">1.</span>
                  <span>Sign up and record a short video profile — show your personality, experience, and what you're looking for.</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-primary font-bold shrink-0">2.</span>
                  <span>Browse kitchen listings in your area. Swipe through video posts from restaurants, hotels, and catering companies.</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-primary font-bold shrink-0">3.</span>
                  <span>Like kitchens that interest you. When they like you back, it's a match — chat, confirm details, and show up for your shift.</span>
                </li>
              </ol>
            </div>

            {/* For Kitchens */}
            <div className="rounded-xl border border-border bg-card p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Store className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold text-foreground">For Kitchens</h3>
              </div>
              <ol className="space-y-2 text-sm text-muted-foreground">
                <li className="flex gap-2">
                  <span className="text-primary font-bold shrink-0">1.</span>
                  <span>Create a post about your kitchen — show the space, describe the role, set pay rate and hours.</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-primary font-bold shrink-0">2.</span>
                  <span>Browse crew profiles — see their videos, read reviews, check their experience and location.</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-primary font-bold shrink-0">3.</span>
                  <span>Match with crew members, message them directly, and fill your shift — no agencies, no fees, no middleman.</span>
                </li>
              </ol>
            </div>
          </div>
        </div>

        {/* Features Grid */}
        <div className="space-y-3">
          <h2 className="text-lg font-bold text-foreground">Features</h2>
          <div className="grid grid-cols-1 gap-3">
            {features.map((f) => (
              <div key={f.title} className="flex gap-3 p-3 rounded-xl border border-border bg-card">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  {f.icon}
                </div>
                <div className="min-w-0">
                  <h4 className="font-semibold text-foreground text-sm">{f.title}</h4>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center pt-4 space-y-3">
          <Button
            onClick={() => navigate("register")}
            className="w-full max-w-xs bg-primary text-primary-foreground hover:bg-primary/90 rounded-xl py-3 text-base font-bold"
          >
            Get Started — It's Free
          </Button>
          <p className="text-xs text-muted-foreground">
            Already have an account?{" "}
            <button onClick={() => navigate("login")} className="text-primary font-medium hover:underline">
              Sign in
            </button>
          </p>
          <button
            onClick={shareAbout}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mx-auto"
          >
            <Share2 size={12} /> Share Day Shift
          </button>
        </div>
      </div>
    </div>
  );
}
