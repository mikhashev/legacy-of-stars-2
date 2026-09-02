/**
 * W5 acceptance: the W4 animations (fleets, reply spheres, Genesis arks/colonies) that a plain
 * seed-1 game rarely reaches within the length of a test. `scripts/make_web_fixtures.py` builds
 * three saves already in those situations; this test loads each one through the real Load
 * screen ("Import JSON file"), same path a player would use, and checks the star map picked the
 * effect up - via `window.__losMap`, the debug hook `?debug=1` publishes (Playwright runs
 * against `vite preview`, a production build, so the flag has to be in the URL).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, type Page, test } from "@playwright/test";

const FIXTURES_DIR = join(import.meta.dirname, "fixtures");

/** Start screen (with the debug hook armed) -> import one fixture save -> the main screen. */
async function loadFixture(page: Page, name: string): Promise<void> {
  await page.goto("/?debug=1");
  const app = page.locator("#app");
  await expect(app).toHaveAttribute("data-ready", "true", { timeout: 120_000 });
  await expect(app).toHaveAttribute("data-phase", "start");

  // The input is hidden behind the "Import JSON file" button, but Playwright can still set
  // files on it directly - the same change event `StartScreen.importFile` listens for.
  await page.locator('input[type="file"]').setInputFiles(join(FIXTURES_DIR, name));
  await expect(app).toHaveAttribute("data-phase", "main", { timeout: 30_000 });
  await page.waitForFunction(() => window.__losMap !== undefined, undefined, { timeout: 30_000 });
}

/** Clicks Advance, answering whatever dialog/modal the generation's events raise. */
async function advanceOneGeneration(page: Page): Promise<void> {
  const header = page.locator(".header-gen");
  const before = await header.innerText();
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const doctrine = page.locator(".doctrine-modal .picker-row").first();
    if (await doctrine.isVisible().catch(() => false)) {
      await doctrine.click();
      await page.waitForTimeout(200);
      continue;
    }
    const modalContinue = page.locator(".event-modal .primary");
    if (await modalContinue.isVisible().catch(() => false)) {
      await modalContinue.click();
      await page.waitForTimeout(200);
      continue;
    }
    const respondNow = page.getByRole("button", { name: "Respond now" });
    if (await respondNow.isVisible().catch(() => false)) {
      await respondNow.click();
      await page.waitForTimeout(200);
      continue;
    }
    const eventDialogRow = page.locator(".dialog-modal .picker-row").first();
    if (await eventDialogRow.isVisible().catch(() => false)) {
      await eventDialogRow.click();
      await page.waitForTimeout(200);
      continue;
    }
    if ((await header.innerText()) !== before) return;
    await page.getByRole("button", { name: "Advance to Next Generation" }).click();
    await page.waitForTimeout(300);
  }
  throw new Error("generation did not advance after answering the dialogs the engine raised");
}

test.use({ viewport: { width: 1280, height: 800 } });

test("threat.json: a hostile fleet is on the map", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));

  const fixture = JSON.parse(readFileSync(join(FIXTURES_DIR, "threat.json"), "utf-8")) as { generation: number };
  await loadFixture(page, "threat.json");
  await expect(page.locator(".threats-panel")).toBeVisible();

  const fleets = await page.evaluate(() => window.__losMap?.fleets() ?? []);
  expect(fleets.length, "no fleet marker in the scene").toBeGreaterThan(0);
  expect(fleets[0]!.eta).toBeGreaterThanOrEqual(3);
  expect(fleets[0]!.progress).toBeGreaterThanOrEqual(0);
  expect(fleets[0]!.progress).toBeLessThan(1);

  await page.screenshot({ path: "test-results/showcase-threat.png", fullPage: true });

  await advanceOneGeneration(page);
  await expect(page.locator(".header-gen")).toContainText(`Generation ${fixture.generation + 1}`);
  // Mid-glide: scene time is still animating towards the new generation.
  await page.waitForTimeout(400);
  await page.screenshot({ path: "test-results/showcase-threat-generation.png", fullPage: true });

  expect(consoleErrors, `console errors: ${consoleErrors.join(" | ")}`).toEqual([]);
});

test("reply.json: a reply sphere is in flight", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));

  const fixture = JSON.parse(readFileSync(join(FIXTURES_DIR, "reply.json"), "utf-8")) as { generation: number };
  await loadFixture(page, "reply.json");

  const spheres = await page.evaluate(() => window.__losMap?.spheres() ?? []);
  const replies = spheres.filter((s) => s.kind === "reply");
  expect(replies.length, "no reply sphere in the scene").toBeGreaterThan(0);

  await page.screenshot({ path: "test-results/showcase-reply.png", fullPage: true });

  await advanceOneGeneration(page);
  await expect(page.locator(".header-gen")).toContainText(`Generation ${fixture.generation + 1}`);
  await page.waitForTimeout(400);
  await page.screenshot({ path: "test-results/showcase-reply-generation.png", fullPage: true });

  expect(consoleErrors, `console errors: ${consoleErrors.join(" | ")}`).toEqual([]);
});

test("genesis.json: a landed ark's colony glow is on the map", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));

  const fixture = JSON.parse(readFileSync(join(FIXTURES_DIR, "genesis.json"), "utf-8")) as { generation: number };
  await loadFixture(page, "genesis.json");

  const arks = await page.evaluate(() => window.__losMap?.arks() ?? []);
  expect(arks.length, "no ark in the scene").toBeGreaterThan(0);
  expect(arks.some((a) => a.landed), "no landed colony (stage >= 1) among the arks").toBe(true);

  await page.screenshot({ path: "test-results/showcase-genesis.png", fullPage: true });

  await advanceOneGeneration(page);
  await expect(page.locator(".header-gen")).toContainText(`Generation ${fixture.generation + 1}`);
  await page.waitForTimeout(400);
  await page.screenshot({ path: "test-results/showcase-genesis-generation.png", fullPage: true });

  expect(consoleErrors, `console errors: ${consoleErrors.join(" | ")}`).toEqual([]);
});
