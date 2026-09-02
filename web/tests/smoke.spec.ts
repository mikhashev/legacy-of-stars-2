/**
 * W2 smoke test: the Pyodide engine boots and the start screen renders.
 *
 * The full playable path (opening scene, actions, dialogs, save/load) is
 * tests/play.spec.ts; this one only proves the app reaches a usable state with no
 * console errors, and keeps a screenshot for a quick visual check.
 */
import { expect, test } from "@playwright/test";

test("the engine boots and the start screen appears with no console errors", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message}`));

  await page.goto("/");

  const app = page.locator("#app");
  await expect(app).toHaveAttribute("data-ready", "true", { timeout: 120_000 });
  await expect(app).toHaveAttribute("data-phase", "start");

  await expect(page.getByRole("heading", { name: "Legacy of Stars" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start" })).toBeVisible();

  await page.screenshot({ path: "test-results/smoke.png", fullPage: true });

  expect(consoleErrors, `console errors: ${consoleErrors.join(" | ")}`).toEqual([]);
});
