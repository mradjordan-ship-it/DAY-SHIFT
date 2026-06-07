import posthog from "posthog-js";

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY as string | undefined;
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST as string | undefined;

let initialized = false;

export function initAnalytics() {
  if (!POSTHOG_KEY) return; // No key = no analytics, graceful skip
  if (initialized) return;

  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST || "https://us.i.posthog.com",
    autocapture: false, // We track events manually for clarity
    capture_pageview: true,
    capture_pageleave: true,
    persistence: "localStorage",
    disable_session_recording: true, // Enable later if needed
  });
  initialized = true;
}

export function identifyUser(userId: number, properties?: Record<string, unknown>) {
  if (!initialized) return;
  posthog.identify(String(userId), properties);
}

export function resetUser() {
  if (!initialized) return;
  posthog.reset();
}

export function trackEvent(event: string, properties?: Record<string, unknown>) {
  if (!initialized) return;
  posthog.capture(event, properties);
}

export function isAnalyticsEnabled() {
  return initialized;
}
