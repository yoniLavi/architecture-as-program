import { defineConfig } from "@playwright/test";

// End-to-end checks for the paper-facing claims (see e2e/inspector.spec.ts),
// and the source of the committed screenshots/ figures. Opt-in: `npm run e2e`
// (or `make ui-e2e` from the repository root). Starts both servers itself.

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  workers: 1, // tests share one API server; runs are cheap but stateful-free
  use: {
    baseURL: "http://localhost:3111",
    viewport: { width: 1600, height: 1000 },
  },
  webServer: [
    {
      command: "uv run --group poc python -m poc.inspector_api --port 8123",
      cwd: "..",
      url: "http://127.0.0.1:8123/api/meta",
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      // A production build: what the screenshots committed as paper figures
      // show, free of dev-overlay chrome.
      command: "npx next build && npx next start -p 3111",
      url: "http://localhost:3111",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
