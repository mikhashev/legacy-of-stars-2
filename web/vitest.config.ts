import { defineConfig } from "vitest/config";

/**
 * Unit tests only: the pure modules under `src/scene/` (coordinates, palette). Anything that
 * needs a browser, a WebGL context or the Pyodide engine is a Playwright test in `tests/*.spec.ts`
 * instead - hence the `include` below and the matching `testMatch` in playwright.config.ts, so
 * the two runners never pick up each other's files.
 *
 * Deliberately does not extend `vite.config.ts`: that config's plugin copies the Pyodide runtime
 * into `public/`, which has nothing to do with running these tests.
 */
export default defineConfig({
  test: {
    include: ["tests/unit/**/*.test.ts"],
    environment: "node",
    reporters: ["default"],
  },
});
