import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests in a real browser.
 *
 * The jsdom suite (`npm test`) covers what the rendering functions produce; it
 * cannot see what a browser adds on top — native form validation, layout at a
 * given width, focus behaviour. Both bugs fixed in Round 13 were invisible to
 * jsdom for exactly that reason, so they are pinned here instead.
 *
 * Two servers are started per run: the real backend on a throwaway SQLite file,
 * and Vite pointed at it. Nothing touches `data/app.db`.
 */
// Deliberately unusual ports: the Vite dev server (5173) and the app's own
// backend (8001) are often already running, and a test run must not fight them.
const BACKEND = 8917;
const FRONTEND = 5917;
const DB = new URL("./.e2e/app.db", import.meta.url).pathname;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `../.venv/bin/python -m uvicorn app.main:app --port ${BACKEND} --log-level warning`,
      cwd: "../backend",
      url: `http://127.0.0.1:${BACKEND}/health`,
      reuseExistingServer: false,
      env: {
        DATABASE_URL: `sqlite:///${DB}`,
        NOTIFICATIONS_ENABLED: "false",
        GOOGLE_CALENDAR_MODE: "disabled",
        CORS_ORIGINS: `http://127.0.0.1:${FRONTEND},http://localhost:${FRONTEND}`,
      },
    },
    {
      command: `npx vite --port ${FRONTEND} --strictPort`,
      url: `http://127.0.0.1:${FRONTEND}`,
      reuseExistingServer: false,
      env: { VITE_API_BASE_URL: `http://127.0.0.1:${BACKEND}` },
    },
  ],
});
