/**
 * PostHog analytics wrapper.
 * Initializes only if VITE_POSTHOG_KEY is set — no-op otherwise.
 */
import posthog from "posthog-js";

let initialized = false;

export function initAnalytics() {
  const key = import.meta.env.VITE_POSTHOG_KEY as string;
  const host = import.meta.env.VITE_POSTHOG_HOST as string;
  if (key) {
    posthog.init(key, {
      api_host: host || "https://us.i.posthog.com",
      autocapture: true,
      capture_pageview: true,
      capture_pageleave: true,
      persistence: "localStorage",
    });
    initialized = true;
  }
}

export function identifyUser(userId: string | number, properties?: Record<string, string | number | boolean>) {
  if (!initialized) return;
  posthog.identify(String(userId), properties);
}

export function resetUser() {
  if (!initialized) return;
  posthog.reset();
}

export function trackEvent(event: string, properties?: Record<string, string | number | boolean>) {
  if (!initialized) return;
  posthog.capture(event, properties);
}

export function setAnalyticsConsent(granted: boolean) {
  if (!initialized) return;
  if (granted) {
    posthog.opt_in_capturing();
  } else {
    posthog.opt_out_capturing();
  }
}

export function hasAnalyticsConsent(): boolean {
  if (!initialized) return false;
  return posthog.has_opted_in_capturing();
}
