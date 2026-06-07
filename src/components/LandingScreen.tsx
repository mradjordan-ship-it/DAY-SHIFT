import { useNav } from "../App";
import { Button } from "@/components/ui/button";
import { Video, Zap, MessageCircle, Star, CarFront, Briefcase, ArrowRight } from "lucide-react";

const features = [
  {
    icon: <Video className="w-6 h-6 text-primary" />,
    title: "Video Profiles",
    desc: "Create short videos to showcase your skills, personality, or kitchen. Stand out visually.",
  },
  {
    icon: <Zap className="w-6 h-6 text-primary" />,
    title: "Instant Matching",
    desc: "Swipe through crew and kitchens. Match instantly when both sides agree.",
  },
  {
    icon: <MessageCircle className="w-6 h-6 text-primary" />,
    title: "Built-In Chat",
    desc: "Message your matches directly. Discuss details, confirm shifts, coordinate in-app.",
  },
  {
    icon: <Star className="w-6 h-6 text-primary" />,
    title: "Reviews & Ratings",
    desc: "Build your reputation over time. The best connections find you first.",
  },
  {
    icon: <Briefcase className="w-6 h-6 text-primary" />,
    title: "For Sale & Events",
    desc: "Sell equipment, post positions, or promote events. A full community hub.",
  },
  {
    icon: <CarFront className="w-6 h-6 text-primary" />,
    title: "Ride Integration",
    desc: "One tap opens Uber or Lyft with the address pre-loaded. Get to shifts easily.",
  },
];

export default function LandingScreen() {
  const { navigate } = useNav();

  return (
    <div className="h-full overflow-y-auto bg-background flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 px-4 py-3 flex items-center justify-between border-b border-border bg-background/90 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <img src="/dayshift-logo.png" alt="Day Shift" className="h-8 w-auto" />
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
          The video-first marketplace connecting culinary workers with kitchens. Post shifts, find crew, and get matched — all in one app.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center mt-6">
          <Button size="lg" onClick={() => navigate("register")} className="gap-2">
            Get Started <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </section>

      {/* Features */}
      <section className="flex-1 px-5 py-10">
        <h2 className="text-xl font-bold text-foreground text-center mb-8">Built for the Culinary Industry</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-4xl mx-auto">
          {features.map((f, i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-5 hover:border-primary/30 transition-colors">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center mb-3">
                {f.icon}
              </div>
              <h3 className="font-semibold text-foreground mb-1">{f.title}</h3>
              <p className="text-sm text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="px-5 py-6 border-t border-border text-center">
        <p className="text-xs text-muted-foreground mb-3">© 2026 Day Shift. All rights reserved.</p>
        <div className="flex justify-center gap-4 text-xs">
          <button onClick={() => navigate("sponsor")} className="text-muted-foreground hover:text-foreground transition-colors">
            Support Us
          </button>
          <a href="mailto:support@dayshift.app" className="text-muted-foreground hover:text-foreground transition-colors">
            Contact
          </a>
        </div>
      </footer>
    </div>
  );
}
