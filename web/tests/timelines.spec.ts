/**
 * T6 acceptance: civilization timelines on the web front-end (docs/plans/civilization_timelines_plan.md
 * §8) - a sky-change flash and journal entry, the dossier's observation history, and the three
 * classes of silence on a sent message.
 *
 * `scripts/make_web_fixtures.py` builds `skychange.json`: a studied (knowledge >= 20) nearby
 * system whose civilization dies on its own timeline, dated so the light of that death - and
 * the answer to a message already sent there - both arrive on the very next generation. This
 * test loads it through the real Load screen, advances one generation, and checks the sky
 * genuinely changed on screen.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, type Page, test } from "@playwright/test";

const FIXTURES_DIR = join(import.meta.dirname, "fixtures");
const SYSTEM = "Proxima Centauri";

/** Start screen (with the debug hook armed) -> import one fixture save -> the main screen. */
async function loadFixture(page: Page, name: string): Promise<void> {
  await page.goto("/?debug=1");
  const app = page.locator("#app");
  await expect(app).toHaveAttribute("data-ready", "true", { timeout: 120_000 });
  await expect(app).toHaveAttribute("data-phase", "start");

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
    const advanceConfirm = page.locator(".dialog-modal").getByRole("button", { name: "Advance", exact: true });
    if (await advanceConfirm.isVisible().catch(() => false)) {
      await advanceConfirm.click();
      await page.waitForTimeout(300);
      continue;
    }
    if ((await header.innerText()) !== before) return;
    await page.getByRole("button", { name: "Advance to Next Generation" }).click();
    await page.waitForTimeout(300);
  }
  throw new Error("generation did not advance after answering the dialogs the engine raised");
}

test.use({ viewport: { width: 1280, height: 800 } });

test("skychange.json: the sky-change flash, journal entry, dossier history and the three classes of silence", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));

  const fixture = JSON.parse(readFileSync(join(FIXTURES_DIR, "skychange.json"), "utf-8")) as {
    generation: number;
  };
  await loadFixture(page, "skychange.json");
  await expect(page.locator(".header-gen")).toContainText(`Generation ${fixture.generation}`);

  // Before the light of the death has arrived: the system still reads as inhabited, and the
  // message is a plain "in flight" - neither the death nor the silence's explanation may leak
  // early (docs/reference/web_contract.md 6).
  await expect(page.locator(`.star-label-system[data-star="${SYSTEM}"]`)).toHaveAttribute("data-mood", "inhabited");

  await advanceOneGeneration(page);
  await expect(page.locator(".header-gen")).toContainText(`Generation ${fixture.generation + 1}`);
  await page.waitForTimeout(400); // let the scene glide and the flash play out

  // 1. The sky-change event: a journal line (never a modal), naming the system.
  const skyChangeRow = page.locator(".event-row.event-sky_change").first();
  await expect(skyChangeRow).toBeVisible();
  await expect(skyChangeRow).toContainText(SYSTEM);
  await expect(skyChangeRow).toContainText("broadcasts have stopped");
  // No modal was raised for it - the only modal-shaped element on screen, if any, belongs to
  // something else entirely; sky_change itself never opens one (docs/reference/web_contract.md 5).
  await expect(page.locator(".event-modal-sky_change")).toHaveCount(0);

  // The halo now reads the system as extinct - the star's *static* colour, not just the flash.
  await expect(page.locator(`.star-label-system[data-star="${SYSTEM}"]`)).toHaveAttribute("data-mood", "extinct");

  // The map's brief "no reply" tag: the message just turned up unanswered.
  const tags = await page.evaluate(() => window.__losMap?.unansweredTags() ?? []);
  expect(tags, "no 'no reply' tag on the map for the newly-unanswered message").toContain(SYSTEM);

  await page.screenshot({ path: "test-results/skychange.png", fullPage: true });

  // 2. The dossier: an observation line, and the three classes of silence on the message.
  await page.locator(`.star-label-system[data-star="${SYSTEM}"]`).click();
  const card = page.locator(`.map-card[data-system="${SYSTEM}"]`);
  await expect(card).toBeVisible();
  // The selected-system card carries the same two things in miniature.
  await expect(card.locator(".map-card-change")).toContainText("2027");
  await expect(card.locator(".map-card-fate")).toHaveAttribute("data-fate", "unanswered");

  await card.getByRole("button", { name: "Dossier" }).click();
  const dossier = page.locator(".dossier-modal");
  await expect(dossier).toBeVisible();

  const observations = dossier.locator(".dossier-observations li");
  await expect(observations).toHaveCount(1);
  await expect(observations.first()).toContainText("2027");
  await expect(observations.first()).toContainText("light from 2014");
  await expect(observations.first()).toContainText("Silent for 0 years");

  // The three classes of silence: this message is now "unanswered", explained by the same
  // light that just reported the death - never shown before that light arrived.
  const fate = dossier.locator(".dossier-message-fate").first();
  await expect(fate).toHaveAttribute("data-fate", "unanswered");
  await expect(fate).toContainText("no reply by 2027");
  await expect(fate).toContainText("they chose silence, or they are no longer there");
  await expect(fate).toContainText("Explained by the light of 2027");

  await page.screenshot({ path: "test-results/dossier-observations.png", fullPage: true });

  expect(consoleErrors, `console errors: ${consoleErrors.join(" | ")}`).toEqual([]);
});
