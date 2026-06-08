import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  define: {
    "import.meta.env.VITE_POSTHOG_KEY": JSON.stringify(process.env.VITE_POSTHOG_KEY || ""),
    "import.meta.env.VITE_POSTHOG_HOST": JSON.stringify(process.env.VITE_POSTHOG_HOST || ""),
    "import.meta.env.VITE_SENTRY_DSN": JSON.stringify(process.env.VITE_SENTRY_DSN || ""),
    "import.meta.env.VITE_SENTRY_ENV": JSON.stringify(process.env.VITE_SENTRY_ENV || "production"),
    "import.meta.env.VITE_SENTRY_RELEASE": JSON.stringify(process.env.VITE_SENTRY_RELEASE || "1.0.0"),
    "import.meta.env.VITE_RECAPTCHA_SITE_KEY": JSON.stringify(process.env.RECAPTCHA_SITE_KEY || ""),
  },
  server: {
    strictPort: true,
    allowedHosts: true,
    proxy: {
      "/api": `http://localhost:${process.env.VITE_BACKEND_PORT || 3101}`,
    },
    headers: {
      "Cache-Control": "no-cache, no-store, must-revalidate",
      "Pragma": "no-cache",
    },
    watch: {
      ignored: [
        "**/node_modules/**",
        "**/.venv/**",
        "**/.git/**",
        "**/dist/**",
        "**/__pycache__/**",
      ],
    },
  },
});
