import { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "me.dayshiftnow.app",
  appName: "Day Shift",
  webDir: "dist",
  server: {
    androidScheme: "https",
  },
  android: {
    allowMixedContent: true,
  },
};

export default config;
