import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    watch: {
      usePolling: true,
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 3000,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom"],
          leaflet: ["leaflet", "react-leaflet"],
        },
      },
    },
  },
});
