/**
 * W3 acceptance: the 3D star map is the main screen's centre column, it draws exactly the
 * systems the engine knows about, and clicking one selects it.
 *
 * Seed 1 again, and again nothing here depends on a random outcome: at Generation 1 the
 * engine's starting sky always contains Proxima Centauri (the nearest star in
 * `data/star_catalog.json`) plus the WOW! source once the 1977 decision is made.
 */
import { expect, type Page, test } from "@playwright/test";

/** Start screen -> seed 1 -> reply to the WOW! signal -> the main screen. */
async function startGame(page: Page): Promise<void> {
  await page.goto("/");
  const app = page.locator("#app");
  await expect(app).toHaveAttribute("data-ready", "true", { timeout: 120_000 });

  await page.getByPlaceholder("random").fill("1");
  await page.getByRole("button", { name: "Start" }).click();
  await expect(app).toHaveAttribute("data-phase", "opening", { timeout: 60_000 });

  await page.getByRole("button", { name: "Reply", exact: true }).click();
  await page.getByRole("button", { name: "3. Use Standard Format (Default)" }).click();
  await expect(page.getByRole("heading", { name: "Reply Transmitted" })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Begin your mission" }).click();
  await expect(app).toHaveAttribute("data-phase", "main", { timeout: 30_000 });
}

test.use({ viewport: { width: 1280, height: 800 } });

test("the star map renders every known system and selects the one you click", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message}`));

  await startGame(page);

  // The WebGL canvas exists and has been sized to the centre column.
  const canvas = page.locator(".star-map canvas.star-map-canvas");
  await expect(canvas).toBeVisible();
  const box = await canvas.boundingBox();
  expect(box, "the map canvas has no layout box").not.toBeNull();
  expect(box!.width).toBeGreaterThan(200);
  expect(box!.height).toBeGreaterThan(200);

  // Nothing was built that the map could not have started from: one label per system, plus
  // Earth's own label at the origin.
  const expectedSystems = Number(await page.locator("#app").getAttribute("data-systems"));
  expect(expectedSystems).toBeGreaterThan(0);
  const labels = page.locator(".star-label-system");
  await expect(labels).toHaveCount(expectedSystems);
  await expect(page.locator(".star-label-earth")).toHaveCount(1);

  // The 1,800 LY WOW! source is on the map, in its own direction, labelled with its distance.
  const wow = page.locator('.star-label-system[data-star^="Wow! source"]');
  await expect(wow).toHaveCount(1);
  await expect(wow.locator(".star-label-distance")).toHaveText("1,800 LY");

  await expect(canvas).toHaveAttribute("data-scale", "compressed");
  await page.screenshot({ path: "test-results/map.png", fullPage: true });

  // Click Proxima Centauri: the selection lands in the store and the card opens.
  await page.locator('.star-label-system[data-star="Proxima Centauri"]').click();
  const card = page.locator(".map-card");
  await expect(card).toBeVisible();
  await expect(card.locator(".map-card-name")).toHaveText("Proxima Centauri");
  await expect(page.locator(".star-map")).toHaveAttribute("data-selected", "Proxima Centauri");
  await expect(card.locator(".map-card-meta").first()).toContainText("4.2 LY");

  await page.screenshot({ path: "test-results/map-selected.png", fullPage: true });

  // The selection is the default for the next system-needing action, and still changeable.
  await page.getByRole("button", { name: "Focus Research on Star System" }).click();
  await expect(page.getByRole("button", { name: /Continue with Proxima Centauri/ })).toBeVisible();
  await expect(page.locator(".dialog-modal .picker-row")).not.toHaveCount(0);
  await page.locator(".modal-close").first().click();

  // Escape clears the selection; the card goes with it.
  await page.keyboard.press("Escape");
  await expect(card).toHaveCount(0);

  // The "true scale" toggle, and back.
  await page.getByRole("button", { name: "Scale: compressed" }).click();
  await expect(page.locator(".star-map")).toHaveAttribute("data-scale", "true");
  // The canvas stamps the scale it last drew, so the screenshot cannot beat the frame.
  await expect(canvas).toHaveAttribute("data-scale", "true");
  await page.screenshot({ path: "test-results/map-true-scale.png", fullPage: true });
  await page.getByRole("button", { name: "Scale: true" }).click();
  await expect(page.locator(".star-map")).toHaveAttribute("data-scale", "compressed");
  await expect(canvas).toHaveAttribute("data-scale", "compressed");

  // The list is still there, as an overlay, and selects the same way the map does.
  await page.getByRole("button", { name: "List" }).click();
  const rows = page.locator(".star-map-list .system-row");
  await expect(rows).toHaveCount(expectedSystems);
  await rows.first().click();
  await expect(rows.first()).toHaveClass(/is-selected/);
  await page.locator(".systems-close").click();
  await expect(page.locator(".map-card-name")).toHaveText("Proxima Centauri");

  // The plan's smaller target size: three columns, and the map still has room to read.
  await page.setViewportSize({ width: 1024, height: 700 });
  await expect(canvas).toBeVisible();
  const small = await canvas.boundingBox();
  expect(small!.width).toBeGreaterThan(380);
  expect(small!.height).toBeGreaterThan(380);
  await page.screenshot({ path: "test-results/map-1024x700.png", fullPage: true });

  expect(consoleErrors, `console errors: ${consoleErrors.join(" | ")}`).toEqual([]);
});
