// usePushNotifications.ts — Web Push subscription management
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../App";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

export function usePushNotifications() {
  const { user, token } = useAuth();
  const [permission, setPermission] = useState<NotificationPermission>("default");
  const [subscribed, setSubscribed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [applicationServerKey, setApplicationServerKey] = useState<string>("");

  // Check current permission on mount
  useEffect(() => {
    if ("Notification" in window) {
      setPermission(Notification.permission);
    }
  }, []);

  // Fetch VAPID public key
  useEffect(() => {
    fetch("/api/push/vapid-key")
      .then((r) => r.json())
      .then((data) => {
        if (data.key) setApplicationServerKey(data.key);
      })
      .catch(() => {});
  }, []);

  // Check if we already have a subscription
  useEffect(() => {
    if (!applicationServerKey || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.ready.then((reg) => {
      reg.pushManager.getSubscription().then((sub) => {
        setSubscribed(!!sub);
      });
    });
  }, [applicationServerKey]);

  const subscribe = useCallback(async () => {
    if (!applicationServerKey || !token || !("serviceWorker" in navigator)) return;
    setLoading(true);
    try {
      // Request permission
      const perm = await Notification.requestPermission();
      setPermission(perm);
      if (perm !== "granted") {
        setLoading(false);
        return;
      }

      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(applicationServerKey),
      });

      // Send subscription to backend
      const res = await fetch("/api/push/subscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(subscription.toJSON()),
      });

      if (res.ok) {
        setSubscribed(true);
      }
    } catch (err) {
      console.error("[Push] Subscribe failed:", err);
    } finally {
      setLoading(false);
    }
  }, [applicationServerKey, token]);

  const unsubscribe = useCallback(async () => {
    if (!("serviceWorker" in navigator)) return;
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        // Tell backend to remove it
        await fetch("/api/push/unsubscribe", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ endpoint: subscription.endpoint }),
        });
        await subscription.unsubscribe();
        setSubscribed(false);
      }
    } catch (err) {
      console.error("[Push] Unsubscribe failed:", err);
    }
  }, [token]);

  return { permission, subscribed, loading, subscribe, unsubscribe };
}
