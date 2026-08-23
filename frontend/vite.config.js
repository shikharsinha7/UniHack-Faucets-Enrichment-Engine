import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Lets the dev frontend call /enrich without CORS headaches.
      // Point this at your deployed backend URL for production builds.
      "/enrich": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
