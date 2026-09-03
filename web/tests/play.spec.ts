/**
 * W2 acceptance: a full playable slice, mirroring the plan's manual test script -
 * new game, WOW! decision, a couple of actions, advancing a generation (answering
 * whatever event/doctrine dialog the engine happens to raise), save, reload, load.
 *
 * Seed 1 is used throughout, but nothing here asserts a specific random outcome -
 * philosophical events and doctrines are answered generically ("pick the first
 * option") so the test does not become flaky if the content bank changes.
 */
import { expect, type Page, test } from "@playwright/test";

/**
 * Clicks Advance to Next Generation, answering any event/doctrine dialog that appears
 * along the way. Every iteration first resolves whatever is currently blocking (a
 * doctrine choice, a philosophical-event dialog or modal, or a plain "big event" modal)
 * before checking whether the generation already moved on.
 */
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
    const modalContinue = page.locator(".event-modal .primary");
    if (await modalContinue.isVisible().catch(() => false)) {
      await modalContinue.click();
      await page.waitForTimeout(200);
      continue;
    }

    // Since W5 the Advance button opens the end-of-generation confirmation first.
    const advanceConfirm = page.locator(".dialog-modal").getByRole("button", { name: "Advance", exact: true });
    if (await advanceConfirm.isVisible().catch(() => false)) {
      await advanceConfirm.click();
      await page.waitForTimeout(300);
      continue;
    }
    const after = await header.innerText();
    if (after !== before) return;

    await page.getByRole("button", { name: "Advance to Next Generation" }).click();
    await page.waitForTimeout(300);
  }
  throw new Error("generation did not advance after answering the dialogs the engine raised");
}

test("a full slice: new game, WOW! decision, actions, advance, save, reload, load", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message}`));

  await page.goto("/");
  const app = page.locator("#app");
  await expect(app).toHaveAttribute("data-ready", "true", { timeout: 120_000 });

  // Start screen: new game with a fixed seed.
  await page.getByPlaceholder("random").fill("1");
  await page.getByRole("button", { name: "Start" }).click();
  await expect(app).toHaveAttribute("data-phase", "opening", { timeout: 60_000 });
  await page.screenshot({ path: "test-results/opening.png", fullPage: true });

  // Reply to the WOW! signal with the standard message.
  await page.getByRole("button", { name: "Reply", exact: true }).click();
  await expect(page.getByText("Compose Earth's First Interstellar Message")).toBeVisible();
  await page.getByRole("button", { name: "3. Use Standard Format (Default)" }).click();
  await expect(page.getByRole("heading", { name: "Reply Transmitted" })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Begin your mission" }).click();

  // Main screen: Generation 1, Year 1977.
  await expect(app).toHaveAttribute("data-phase", "main", { timeout: 30_000 });
  await expect(page.locator(".header-gen")).toContainText("Generation 1");
  await expect(page.locator(".header-gen")).toContainText("1977");
  await page.screenshot({ path: "test-results/main.png", fullPage: true });

  // The generation starts with a clean sheet and nothing to undo.
  const generationPanel = page.locator(".generation-panel");
  await expect(generationPanel.locator(".generation-empty")).toBeVisible();
  await expect(generationPanel.getByRole("button", { name: "Undo last" })).toBeDisabled();
  const apBefore = await page.locator(".generation-ap").innerText();

  // focus_research on the first system: opens the system-picker dialog.
  await page.getByRole("button", { name: "Focus Research on Star System" }).click();
  await expect(page.getByText("choose a system")).toBeVisible();
  await page.screenshot({ path: "test-results/dialog-system-picker.png", fullPage: true });
  await page.locator(".picker-list .picker-row").first().click();
  await expect(page.locator(".dialog-modal")).toHaveCount(0);

  // ... and "This generation" now lists it, with what it cost.
  const logRows = generationPanel.locator(".generation-log-row");
  await expect(logRows).toHaveCount(1);
  await expect(logRows.first()).toHaveAttribute("data-action", "focus_research");
  await expect(logRows.first()).toContainText("Focused research on");
  await expect(logRows.first()).toContainText("1 AP");
  await expect(page.locator(".generation-ap")).not.toHaveText(apBefore);
  await page.screenshot({ path: "test-results/generation-panel.png", fullPage: true });

  // Undo: the action point comes back and the sheet is clean again.
  await generationPanel.getByRole("button", { name: "Undo last" }).click();
  await expect(generationPanel.locator(".generation-empty")).toBeVisible({ timeout: 15_000 });
  await expect(logRows).toHaveCount(0);
  await expect(page.locator(".generation-ap")).toHaveText(apBefore);
  await expect(generationPanel.getByRole("button", { name: "Undo last" })).toBeDisabled();

  // Do it again (undo is a change of mind, not a way out of spending the point) and add one
  // more action, so the confirmation below has something to list.
  await page.getByRole("button", { name: "Focus Research on Star System" }).click();
  await page.locator(".picker-list .picker-row").first().click();
  await expect(page.locator(".dialog-modal")).toHaveCount(0);

  // public_outreach: no parameters, runs immediately.
  await page.getByRole("button", { name: "Conduct Public Outreach Campaign" }).click();
  await expect(logRows).toHaveCount(2);

  // The Advance button asks first, listing exactly what the generation was spent on.
  await page.getByRole("button", { name: "Advance to Next Generation" }).click();
  const advanceDialog = page.locator(".dialog-modal");
  await expect(advanceDialog.getByRole("heading", { name: "End of Generation 1" })).toBeVisible();
  await expect(advanceDialog.locator(".advance-log li")).toHaveCount(2);
  await expect(advanceDialog.locator(".advance-log li").first()).toHaveAttribute("data-action", "focus_research");
  await expect(advanceDialog.locator(".advance-log li").nth(1)).toHaveAttribute("data-action", "public_outreach");
  await expect(advanceDialog.locator(".advance-unspent")).toBeVisible();
  await page.screenshot({ path: "test-results/advance-confirm.png", fullPage: true });

  // "Back" leaves the generation exactly where it was; the log is still there.
  await advanceDialog.getByRole("button", { name: "Back", exact: true }).click();
  await expect(page.locator(".dialog-modal")).toHaveCount(0);
  await expect(page.locator(".header-gen")).toContainText("Generation 1");
  await expect(logRows).toHaveCount(2);

  // Advance one generation, answering whatever dialog the engine raises.
  await advanceOneGeneration(page);
  // A new generation is a clean sheet: last generation's actions are gone from the panel.
  // (Answering a philosophical crisis raised *by* the advance can already have written a row
  // of its own, so this checks the old rows are gone rather than that the list is empty.)
  await expect(generationPanel.locator('.generation-log-row[data-action="focus_research"]')).toHaveCount(0);
  await expect(generationPanel.locator('.generation-log-row[data-action="public_outreach"]')).toHaveCount(0);
  const generationAfterAdvance = await page.locator(".header-gen").innerText();

  // Manual save via the menu.
  await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.getByRole("heading", { name: "Menu" })).toBeVisible();
  await page.locator(".menu-save-row input[type=text]").fill("e2e");
  await page.locator(".menu-save-row").getByRole("button", { name: "Save" }).click();
  await expect(page.locator(".toast")).toContainText("Saved as", { timeout: 10_000 });
  await page.locator(".modal-close").first().click();

  // Reload the page: the engine restarts, the start screen must list the save.
  await page.reload();
  await expect(app).toHaveAttribute("data-ready", "true", { timeout: 120_000 });
  await expect(app).toHaveAttribute("data-phase", "start");
  const saveRow = page.locator(".save-row-button", { hasText: "e2e" });
  await expect(saveRow).toBeVisible({ timeout: 10_000 });
  await saveRow.click();

  await expect(app).toHaveAttribute("data-phase", "main", { timeout: 30_000 });
  await expect(page.locator(".header-gen")).toContainText(generationAfterAdvance.trim());

  expect(consoleErrors, `console errors: ${consoleErrors.join(" | ")}`).toEqual([]);
});
