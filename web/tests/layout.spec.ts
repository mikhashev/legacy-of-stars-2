/**
 * W5 acceptance: the layout is a fixed three-column grid at >= 1000px and stacks - map first,
 * then status/actions, then the journal - below it, and nothing ever forces the page to scroll
 * sideways. Also covers the collapsible panels' remembered state (localStorage).
 *
 * Seed 1, same pattern as map.spec.ts/play.spec.ts: nothing here depends on a random outcome.
 */
import { join } from "node:path";
import { expect, type Page, test } from "@playwright/test";

const FIXTURES_DIR = join(import.meta.dirname, "fixtures");

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

/** `document.documentElement.scrollWidth <= innerWidth`: nothing forces horizontal scrolling. */
async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(overflow.scrollWidth, `scrollWidth ${overflow.scrollWidth} > innerWidth ${overflow.innerWidth}`).toBeLessThanOrEqual(
    overflow.innerWidth,
  );
}

test("1280x800: three columns, no overflow", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await startGame(page);

  const columns = page.locator(".main-layout > .main-column");
  await expect(columns).toHaveCount(3);
  // Three columns side by side: the left column's box sits to the left of the centre one's.
  const left = await page.locator(".main-column-left").boundingBox();
  const center = await page.locator(".main-column-center").boundingBox();
  const right = await page.locator(".main-column-right").boundingBox();
  expect(left!.x).toBeLessThan(center!.x);
  expect(center!.x).toBeLessThan(right!.x);
  // Roughly the same row: not stacked.
  expect(Math.abs(left!.y - center!.y)).toBeLessThan(20);

  await expectNoHorizontalOverflow(page);
  await page.screenshot({ path: "test-results/layout-1280.png", fullPage: true });
});

test("1024x700: still three columns, no overflow", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 700 });
  await startGame(page);

  const left = await page.locator(".main-column-left").boundingBox();
  const center = await page.locator(".main-column-center").boundingBox();
  const right = await page.locator(".main-column-right").boundingBox();
  expect(left!.x).toBeLessThan(center!.x);
  expect(center!.x).toBeLessThan(right!.x);
  expect(Math.abs(left!.y - center!.y)).toBeLessThan(20);

  await expectNoHorizontalOverflow(page);
  await page.screenshot({ path: "test-results/layout-1024.png", fullPage: true });
});

test("800x1000: stacked, map first, collapsible panels, no overflow", async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 1000 });
  await startGame(page);

  // The map is first on screen, then status/actions, then the journal - `order` in CSS, the
  // DOM itself stays in its original (left, centre, right) sequence.
  const left = await page.locator(".main-column-left").boundingBox();
  const center = await page.locator(".main-column-center").boundingBox();
  const right = await page.locator(".main-column-right").boundingBox();
  expect(center!.y).toBeLessThan(left!.y);
  expect(left!.y).toBeLessThan(right!.y);

  // The map keeps a sane ~4:3 block, at least 320px tall, instead of collapsing to nothing.
  const viewport = page.locator(".star-map-viewport");
  const box = await viewport.boundingBox();
  expect(box!.height).toBeGreaterThanOrEqual(320);
  expect(box!.width / box!.height).toBeGreaterThan(1.0); // wider than tall, not a sliver

  await expectNoHorizontalOverflow(page);
  await page.screenshot({ path: "test-results/layout-800.png", fullPage: true });

  // Collapsible panels: toggling one closes its body and remembers that in localStorage
  // (docs/plans/web_version_plan.md W5: "panels collapsible with remembered state").
  const statusHead = page.locator(".status-panel .collapsible-head");
  const statusBody = page.locator(".status-panel .collapsible-body");
  await expect(statusBody).toBeVisible();
  await statusHead.click();
  await expect(statusBody).toHaveCount(0);
  await expect(page.locator(".status-panel")).toHaveAttribute("data-open", "false");
  expect(await page.evaluate(() => localStorage.getItem("los.panelOpen.status"))).toBe("0");

  // A fresh mount (a reload always lands back on the start screen - there is no autosave yet
  // in this test - so start a second game) reads the same key back and stays collapsed.
  await page.reload();
  await startGame(page);
  await expect(page.locator(".status-panel")).toHaveAttribute("data-open", "false");
  await expect(page.locator(".status-panel .collapsible-body")).toHaveCount(0);

  await expectNoHorizontalOverflow(page);
});

/**
 * `skychange.json` (`scripts/make_web_fixtures.py`) is an idle-generations save: advancing one
 * generation from it raises the mission analyst's briefing - a fixed-width, multi-line report
 * with "====" rulers - in the journal (see tests/timelines.spec.ts for the same fixture's other
 * acceptance). That is exactly the long unbroken text that used to overflow the journal column.
 */
async function loadSkychangeAndAdvance(page: Page): Promise<void> {
  await page.goto("/?debug=1");
  const app = page.locator("#app");
  await expect(app).toHaveAttribute("data-ready", "true", { timeout: 120_000 });
  await expect(app).toHaveAttribute("data-phase", "start");

  await page.locator('input[type="file"]').setInputFiles(join(FIXTURES_DIR, "skychange.json"));
  await expect(app).toHaveAttribute("data-phase", "main", { timeout: 30_000 });

  // Answer whatever dialog/modal the advance raises, same pattern as timelines.spec.ts.
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
    const advanceConfirm = page.locator(".dialog-modal").getByRole("button", { name: "Advance", exact: true });
    if (await advanceConfirm.isVisible().catch(() => false)) {
      await advanceConfirm.click();
      await page.waitForTimeout(300);
      continue;
    }
    if ((await header.innerText()) !== before) break;
    // Scoped to the actions panel: the generation panel (W6) has its own same-named button.
    await page.locator(".actions-panel").getByRole("button", { name: "Advance to Next Generation" }).click();
    await page.waitForTimeout(300);
  }
  await expect(header).not.toHaveText(before);

  // The briefing is worth waiting for explicitly: it is what actually exercises the wrap fix.
  await expect(page.locator(".event-row.event-briefing").first()).toBeVisible({ timeout: 10_000 });
}

for (const [label, size] of [
  ["1280x800", { width: 1280, height: 800 }],
  ["1024x700", { width: 1024, height: 700 }],
] as const) {
  test(`${label}: the briefing's long lines do not overflow the journal`, async ({ page }) => {
    await page.setViewportSize(size);
    await loadSkychangeAndAdvance(page);

    const journal = page.locator(".event-log");
    await expect(journal).toBeVisible();
    const overflow = await journal.evaluate((el) => el.scrollWidth - el.clientWidth);
    expect(overflow, `journal scrollWidth exceeds clientWidth by ${overflow}px`).toBeLessThanOrEqual(0);

    await expectNoHorizontalOverflow(page);
  });
}
