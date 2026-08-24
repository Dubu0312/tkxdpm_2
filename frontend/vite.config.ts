/// <reference types="vitest/config" />
import { defineConfig } from "vite";

export default defineConfig({
  // Environment variables live in the project root .env (shared with the backend).
  // Only VITE_* prefixed vars are exposed to client code.
  envDir: "..",
  server: {
    port: 5173,
    strictPort: false,
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
  },
});
