import { defineConfig, devices } from "@playwright/test";

/**
 * The smoke test runs against a production build: `npm run build` (which rebuilds
 * engine.zip first) and then `vite preview`. Pyodide needs a real HTTP server for
 * its .wasm, so there is no file:// shortcut.
 */
const PORT = 4173;

export default defineConfig({
  testDir: "./tests",
  // *.test.ts under tests/unit/ belongs to Vitest (`npm run unit`); Playwright takes the specs.
  testMatch: "**/*.spec.ts",
  outputDir: "./test-results",
  reporter: [["list"], ["html", { open: "never", outputFolder: "./playwright-report" }]],
  timeout: 180_000,
  expect: { timeout: 120_000 },
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${PORT}/`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npm run build && npm run preview -- --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}/`,
    timeout: 300_000,
    reuseExistingServer: !process.env["CI"],
    stdout: "pipe",
  },
});
