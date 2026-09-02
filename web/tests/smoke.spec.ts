/**
 * W1 acceptance: the Python engine boots in a browser worker and plays ten generations.
 *
 * It also records what the phase has to report - startup time and download sizes - in the
 * test output and in test-results/smoke.png.
 */
import { expect, test } from "@playwright/test";

test("the engine boots in the browser and advances ten generations", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message}`));

  await page.goto("/");

  // Startup: the marker main.ts sets once the worker replied "ready".
  const app = page.locator("#app");
  await expect(app).toHaveAttribute("data-ready", "true", { timeout: 120_000 });

  const meta = await page.locator("#meta").innerText();
  const startupMs = Number(await app.getAttribute("data-startup-ms"));
  expect(startupMs).toBeGreaterThan(0);
  console.log(`[smoke] ${meta}`);

  // New game, seed 1: generation 1, year 1977.
  await page.getByRole("button", { name: "New game (seed 1)" }).click();
  const out = page.locator("#out");
  await expect(out).toContainText("generation      1", { timeout: 60_000 });
  await expect(out).toContainText("1977");
  await expect(app).toHaveAttribute("data-generation", "1");

  // Ten generations later: generation 11.
  await page.getByRole("button", { name: "Advance x10" }).click();
  await expect(app).toHaveAttribute("data-generation", "11", { timeout: 120_000 });
  await expect(out).toContainText("generation      11");

  // The save round trip goes through the same worker.
  await page.getByRole("button", { name: "Save to console" }).click();
  await expect(page.locator("#meta")).toContainText("save:");

  await page.screenshot({ path: "test-results/smoke.png", fullPage: true });

  expect(consoleErrors, `console errors: ${consoleErrors.join(" | ")}`).toEqual([]);
});
