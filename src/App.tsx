import { useState, useEffect, createContext, useContext, useCallback, useRef, Suspense, lazy } from "react";
import type { User, Screen, Match } from "./types";
import { initAnalytics, identifyUser, resetUser, trackEvent } from "./lib/analytics";
import CookieConsent from "./components/CookieConsent";

// ─── Auth Context ─────────────────────────────────────────────────────────────
interface AuthCtx {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthCtx>({
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  refreshUser: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

// ─── Nav Context ──────────────────────────────────────────────────────────────
interface NavCtx {
  screen: Screen;
  navigate: (s: Screen, params?: Record<string, unknown>) => void;
  params: Record<string, unknown>;
  fullscreenActive: boolean;
  setFullscreenActive: (v: boolean) => void;
  navHidden: boolean;
  setNavHidden: (v: boolean) => void;
  showNav: () => void;
}

const NavContext = createContext<NavCtx>({
  screen: "feed",
  navigate: () => {},
  params: {},
  fullscreenActive: false,
  setFullscreenActive: () => {},
  navHidden: false,
  setNavHidden: () => {},
  showNav: () => {},
});

export function useNav() {
  return useContext(NavContext);
}

// ─── Lazy screen imports ──────────────────────────────────────────────────────
// Core screens used immediately — keep eager
import FeedScreen from "./components/FeedScreen";
import LandingScreen from "./components/LandingScreen";
import AuthScreen from "./components/AuthScreen";

// Secondary screens — lazy loaded on demand
const PostScreen = lazy(() => import("./components/PostScreen"));
const MatchesScreen = lazy(() => import("./components/MatchesScreen"));
const ChatScreen = lazy(() => import("./components/ChatScreen"));
const ProfileScreen = lazy(() => import("./components/ProfileScreen"));
const UserProfileScreen = lazy(() => import("./components/UserProfileScreen"));
const ReviewScreen = lazy(() => import("./components/ReviewScreen"));
const AdminScreen = lazy(() => import("./components/AdminScreen"));
const SupportScreen = lazy(() => import("./components/SupportScreen"));
const SponsorScreen = lazy(() => import("./components/SponsorScreen"));
const LegalScreen = lazy(() => import("./components/LegalScreen"));
const OnboardingModal = lazy(() => import("./components/OnboardingModal"));
const InstallPrompt = lazy(() => import("./components/InstallPrompt"));
const OfflineScreen = lazy(() => import("./components/OfflineScreen"));
const OnboardingScreen = lazy(() => import("./components/OnboardingScreen"));
const AboutScreen = lazy(() => import("./components/AboutScreen"));
const BoostScreen = lazy(() => import("./components/BoostScreen"));
const AnalyticsScreen = lazy(() => import("./components/AnalyticsScreen"));

// ─── Loading spinner for Suspense fallback ────────────────────────────────────
function ScreenLoader() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

// Icons (inline SVG to avoid lucide overhead in nav)
import {
  Play,
  Plus,
  MessageCircle,
  User as UserIcon,
  LogIn,
  Shield,
  Heart,
  Bell,
  HardHat,
  Building2,
} from "lucide-react";

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [screen, setScreen] = useState<Screen>("feed");
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [pendingMatches, setPendingMatches] = useState(0);
  const [fullscreenActive, setFullscreenActive] = useState(false);
  const [navHidden, setNavHidden] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [notifPermission, setNotifPermission] = useState<NotificationPermission>("default");
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  // Online/offline detection
  useEffect(() => {
    const goOffline = () => setIsOffline(true);
    const goOnline = () => setIsOffline(false);
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    return () => {
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, []);

  // Request notification permission
  const requestNotifs = async () => {
    if (!("Notification" in window)) return;
    const perm = await Notification.requestPermission();
    setNotifPermission(perm);
  };

  // Send a browser notification
  const sendNotification = (title: string, body: string) => {
    if (notifPermission !== "granted") return;
    try {
      new Notification(title, { body, icon: "/icons/icon-192x192.png", badge: "/icons/icon-72x72.png" });
    } catch {}
  };

  // Track previous match/message count to detect new ones
  const prevPendingRef = useRef(0);

  // Check notification support on mount
  useEffect(() => {
    if ("Notification" in window) {
      setNotifPermission(Notification.permission);
    }
  }, []);
  // Rehydrate from localStorage and handle deep links
  useEffect(() => {
    const stored = localStorage.getItem("ds_token");
    const storedUser = localStorage.getItem("ds_user");
    if (stored && storedUser) {
      setToken(stored);
      setUser(JSON.parse(storedUser));
    }
    
    const params = new URLSearchParams(window.location.search);
    const screenParam = params.get("screen");
    if (screenParam === "reset" && params.get("token")) {
      setScreen("reset");
      setParams({ token: params.get("token") });
      window.history.replaceState({}, document.title, "/");
    } else if (screenParam === "verify-email" && params.get("token")) {
      setScreen("verify-email");
      setParams({ token: params.get("token") });
      window.history.replaceState({}, document.title, "/");
    } else if (screenParam === "about") {
      setScreen("about");
      window.history.replaceState({}, document.title, "/");
    } else if (screenParam) {
      setScreen(screenParam as Screen);
      window.history.replaceState({}, document.title, "/");
    }
    
    setHydrated(true);
    initAnalytics();
  }, []);

  const login = useCallback((tok: string, u: User) => {
    setToken(tok);
    setUser(u);
    localStorage.setItem("ds_token", tok);
    localStorage.setItem("ds_user", JSON.stringify(u));
    identifyUser(u.id, { name: u.name, role: u.role, email: u.email });
    trackEvent("user_login", { role: u.role });
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("ds_token");
    localStorage.removeItem("ds_user");
    trackEvent("user_logout");
    resetUser();
    setScreen("feed");
  }, []);

  const refreshUser = useCallback(async () => {
    const tok = localStorage.getItem("ds_token");
    if (!tok) return;
    try {
      const res = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${tok}` },
      });
      if (res.ok) {
        const u = await res.json();
        setUser(u);
        localStorage.setItem("ds_user", JSON.stringify(u));
        identifyUser(u.id, { name: u.name, role: u.role, email: u.email });
      } else if (res.status === 403) {
        // Account suspended — force logout
        setToken(null);
        setUser(null);
        localStorage.removeItem("ds_token");
        localStorage.removeItem("ds_user");
      }
    } catch {}
  }, []);

  // Refresh user data from server after hydration (picks up is_admin, etc.)
  useEffect(() => {
    if (hydrated && token) refreshUser();
  }, [hydrated, token, refreshUser]);

  // Redirect to onboarding for new users who haven't completed it
  useEffect(() => {
    if (user && token && !user.onboarded && screen !== "onboarding") {
      setScreen("onboarding");
    }
  }, [user, token, screen]);

  // Navigation history stack for browser back button support
  const historyRef = useRef<Array<{ screen: Screen; params: Record<string, unknown> }>>([]);
  const screenRef = useRef(screen);
  const paramsRef = useRef(params);
  screenRef.current = screen;
  paramsRef.current = params;

  const navigate = useCallback((s: Screen, p: Record<string, unknown> = {}) => {
    // Save current screen to history before navigating away
    historyRef.current.push({ screen: screenRef.current, params: paramsRef.current });
    setScreen(s);
    setParams(p);
    setNavHidden(false); // Always show nav when navigating
    window.scrollTo(0, 0);
    // Push to browser history so phone back button works
    window.history.pushState({ screen: s, params: p }, "");
  }, []);

  // Intercept browser back button for in-app navigation
  useEffect(() => {
    // Seed initial history entry
    window.history.replaceState({ screen, params }, "");
    const handlePop = () => {
      // Pop from our history stack — go to previous screen
      const prev = historyRef.current.pop();
      if (prev) {
        setScreen(prev.screen);
        setParams(prev.params);
      } else {
        // No history left — go to feed
        setScreen("feed");
        setParams({});
      }
      window.scrollTo(0, 0);
    };
    window.addEventListener("popstate", handlePop);
    return () => window.removeEventListener("popstate", handlePop);
  }, []);

  // Poll pending matches count
  useEffect(() => {
    if (!token) return;
    const fetchPending = async () => {
      try {
        const res = await fetch("/api/matches", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data: Match[] = await res.json();
          const count = data.filter((m) => m.status === "pending" && m.initiated_by !== user?.id).length;
          setPendingMatches(count);
          // Notify on new match
          if (count > prevPendingRef.current && prevPendingRef.current > 0) {
            sendNotification("New Match!", `Someone wants to connect with you on Day Shift`);
          }
          prevPendingRef.current = count;
        }
      } catch {}
    };
    fetchPending();
    const id = setInterval(fetchPending, 30_000);
    return () => clearInterval(id);
  }, [token, screen]);

  const showNav = useCallback(() => setNavHidden(false), []);

  if (!hydrated) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const authCtx: AuthCtx = { user, token, login, logout, refreshUser };
  const navCtx: NavCtx = { screen, navigate, params, fullscreenActive, setFullscreenActive, navHidden, setNavHidden, showNav };

  return (
    <AuthContext.Provider value={authCtx}>
      <NavContext.Provider value={navCtx}>
        <div className="h-screen overflow-hidden bg-background flex flex-col max-w-[430px] md:max-w-[768px] mx-auto relative shadow-2xl md:shadow-none border-x border-border/50">
          {/* Cookie consent banner */}
          <CookieConsent />

          {/* Onboarding for new users */}
          {user && (
            <Suspense fallback={null}>
              <OnboardingModal />
            </Suspense>
          )}

          {/* PWA install prompt */}
          <Suspense fallback={null}>
            <InstallPrompt />
          </Suspense>

          {/* Offline overlay */}
          {isOffline && (
            <Suspense fallback={null}>
              <OfflineScreen />
            </Suspense>
          )}
          {/* Header — hidden on about screen and landing page for non-logged users */}
          {screen !== "about" && screen !== "landing" && !(screen === "feed" && !user) && (
          <header className="flex-shrink-0 z-50 bg-background/90 backdrop-blur-md border-b border-border px-4 md:px-6 py-3 flex items-center justify-between">
            <button
              onClick={() => navigate("feed")}
              className="flex items-center gap-2"
            >
              <img src="/dayshift-logo.png" alt="Day Shift" className="h-8 w-auto md:h-10" />
            </button>

            {user ? (
              <div className="flex items-center gap-2">
                {user.is_admin && (
                  <button
                    onClick={() => navigate("admin")}
                    className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors ${screen === "admin" ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary hover:bg-primary/20"}`}
                    title="Admin Dashboard"
                  >
                    <Shield size={16} />
                  </button>
                )}
                {!user.is_admin && (
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    {user.role === "worker" ? <HardHat size={12} /> : <Building2 size={12} />} {user.name.split(" ")[0]}
                  </span>
                )}
                {/* Notification bell */}
                <button
                  onClick={notifPermission === "default" ? requestNotifs : () => navigate("matches")}
                  className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                    pendingMatches > 0
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary/50 text-muted-foreground hover:text-foreground"
                  }`}
                  title="Notifications"
                >
                  <Bell size={16} />
                  {pendingMatches > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 text-white rounded-full text-[8px] flex items-center justify-center font-bold">
                      {pendingMatches > 9 ? "9+" : pendingMatches}
                    </span>
                  )}
                </button>
                <button
                  onClick={() => navigate("profile")}
                  className="w-9 h-9 rounded-full bg-secondary border border-border overflow-hidden"
                >
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xs font-semibold text-primary">
                      {user.name[0]?.toUpperCase()}
                    </div>
                  )}
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate("sponsor")}
                  className="flex items-center gap-1 text-xs text-primary/80 font-medium hover:text-primary transition-colors"
                >
                  <Heart size={15} /> Support Us
                </button>
                <button
                  onClick={() => navigate("login")}
                  className="flex items-center gap-1.5 text-sm text-primary font-medium"
                >
                  <LogIn size={17} /> Sign In
                </button>
              </div>
            )}
          </header>
          )}

          {/* Screen content */}
          <main className={`flex-1 min-h-0 flex flex-col ${["login","register","forgot","reset","verify-email","about","landing"].includes(screen) ? "overflow-y-auto" : "overflow-hidden"}`}>
            <Suspense fallback={<ScreenLoader />}>
            {/* Landing page for non-logged-in users */}
            {!user && screen === "feed" && <LandingScreen />}
            {user && screen === "feed" && <FeedScreen />}
            {screen === "landing" && <LandingScreen />}
            {screen === "post" && <PostScreen />}
            {screen === "matches" && <MatchesScreen />}
            {screen === "chat" && <ChatScreen matchId={params.matchId as number} />}
            {screen === "profile" && <ProfileScreen />}
            {screen === "login" && <AuthScreen mode="login" />}
            {screen === "register" && <AuthScreen mode="register" />}
            {screen === "forgot" && <AuthScreen mode="forgot" />}
            {screen === "reset" && <AuthScreen mode="reset" tokenParam={params.token as string} />}
            {screen === "verify-email" && <AuthScreen mode="verify-email" tokenParam={params.token as string} />}
            {screen === "user-profile" && <UserProfileScreen userId={params.userId as number} />}
            {screen === "review" && (
              <ReviewScreen
                matchId={params.matchId as number}
                revieweeId={params.revieweeId as number}
                revieweeName={params.revieweeName as string}
              />
            )}
            {screen === "admin" && <AdminScreen />}
            {screen === "support" && <SupportScreen />}
            {screen === "sponsor" && <SponsorScreen />}
            {screen === "terms" && <LegalScreen type="terms" />}
            {screen === "privacy" && <LegalScreen type="privacy" />}
            {screen === "onboarding" && <OnboardingScreen />}
            {screen === "about" && <AboutScreen />}
            {screen === "boost" && <BoostScreen />}
            {screen === "analytics" && <AnalyticsScreen />}
            </Suspense>
            {screen === "boost" && <BoostScreen />}
            {screen === "analytics" && <AnalyticsScreen />}
          </main>

          {/* Bottom Nav — hidden on auth/about/landing screens and fullscreen */}
          {!["login", "register", "forgot", "reset", "verify-email", "about", "boost", "analytics", "landing"].includes(screen) && user && !fullscreenActive && (
          <>
            {/* Floating Post peek — visible when nav is hidden (mobile only) */}
            {navHidden && (
              <button
                onClick={showNav}
                className="fixed bottom-3 left-1/2 -translate-x-1/2 z-50 w-12 h-12 bg-primary rounded-full flex items-center justify-center shadow-lg ember-glow transition-all duration-300 hover:scale-110 active:scale-95 md:hidden"
                style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
              >
                <Plus size={22} className="text-primary-foreground" />
              </button>
            )}
            <nav className={`flex-shrink-0 z-50 bg-background/95 backdrop-blur-md border-t border-border transition-transform duration-300 ease-in-out md:translate-y-0 ${navHidden ? "translate-y-full" : "translate-y-0"}`}>
            <div className="flex items-stretch">
              <NavBtn
                icon={<Play size={20} />}
                label="Feed"
                active={screen === "feed"}
                onClick={() => navigate("feed")}
              />
              {user && (
                <NavBtn
                  icon={<Plus size={20} />}
                  label="Post"
                  active={screen === "post"}
                  highlight
                  onClick={() => navigate("post")}
                />
              )}
              <NavBtn
                icon={
                  <div className="relative">
                    <MessageCircle size={20} />
                    {pendingMatches > 0 && (
                      <span className="absolute -top-1 -right-1 w-4 h-4 bg-primary text-primary-foreground rounded-full text-[9px] flex items-center justify-center font-bold">
                        {pendingMatches}
                      </span>
                    )}
                  </div>
                }
                label="Matches"
                active={screen === "matches"}
                onClick={() => {
                  if (!user) navigate("login");
                  else navigate("matches");
                }}
              />
              <NavBtn
                icon={<UserIcon size={20} />}
                label={user ? "Profile" : "Login"}
                active={screen === "profile" || screen === "login" || screen === "register"}
                onClick={() => {
                  if (!user) navigate("login");
                  else navigate("profile");
                }}
              />
            </div>
          </nav>
          </>
          )}
        </div>
      </NavContext.Provider>
    </AuthContext.Provider>
  );
}

function NavBtn({
  icon,
  label,
  active,
  highlight,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  highlight?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors
        ${active ? "text-primary" : "text-muted-foreground"}
        ${highlight
          ? "relative"
          : ""
        }`}
    >
      {highlight ? (
        <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center ember-glow -mt-5 mb-0.5 shadow-lg">
          <span className="text-primary-foreground">{icon}</span>
        </div>
      ) : (
        icon
      )}
      <span className={`text-[10px] font-medium ${active && !highlight ? "nav-active" : ""}`}>
        {label}
      </span>
    </button>
  );
}
