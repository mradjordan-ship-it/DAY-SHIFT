import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { initAnalytics } from "./lib/analytics";
import "./index.css";
import App from "./App.tsx";

// ── PostHog analytics ────────────────────────────────────────────────
initAnalytics();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);

// Register PWA service worker
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // SW registration failed — app still works fine
    });
  });
}
