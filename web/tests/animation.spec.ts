/**
 * W4 acceptance: the map animates off scene time and the event stream, and the physics it
 * draws is the game's.
 *
 * The scenario is the plan's own W4 check ("a message to Proxima - the sphere arrives in one
 * generation"): seed 1, reply to the WOW! signal, send a transmission to Proxima Centauri,
 * advance one generation and watch the light sphere leave Earth.
 *
 * Everything is read through `window.__losMap`, the debug hook `StarMap` publishes when the
 * URL carries `?debug=1` - Playwright runs against `vite preview`, i.e. a production build, so
 * the flag has to be in the URL rather than in `import.meta.env`.
 */
import { expect, type Page, test } from "@playwright/test";

/** Start screen -> seed 1 -> reply to the WOW! signal -> the main screen, with the debug hook. */
async function startGame(page: Page): Promise<void> {
  await page.goto("/?debug=1");
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

/**
 * Clicks Advance once, answering whatever dialog the engine raises, exactly like
 * `play.spec.ts` does - the point here is that the scene survives several generations of real
 * events (discoveries, crises, doctrines) without a console error, not any specific outcome.
 */
async function advanceOneGeneration(page: Page): Promise<void> {
  const header = page.locator(".header-gen");
  const before = await header.innerText();
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await dismissBlockingUi(page);
    const eventDialogRow = page.locator(".dialog-modal .picker-row").first();
    if (await eventDialogRow.isVisible().catch(() => false)) {
      await eventDialogRow.click();
      await page.waitForTimeout(200);
      continue;
    }
    const respondNow = page.getByRole("button", { name: "Respond now" });
    if (await respondNow.isVisible().catch(() => false)) {
      await respondNow.click();
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
    if ((await header.innerText()) !== before) return;
    await page.getByRole("button", { name: "Advance to Next Generation" }).click();
    await page.waitForTimeout(300);
  }
  throw new Error("generation did not advance after answering the dialogs the engine raised");
}

/** Clears whatever modal the generation's events raised, so the map is visible again. */
async function dismissBlockingUi(page: Page): Promise<void> {
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
    return;
  }
}

test.use({ viewport: { width: 1280, height: 800 } });

test("scene time animates a message sphere from Earth to Proxima Centauri", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message}`));

  await startGame(page);

  // The debug hook is published, and scene time is seated on the current generation without
  // an animation: opening the map is not a generation advance.
  await page.waitForFunction(() => window.__losMap !== undefined, undefined, { timeout: 30_000 });
  const atRest = await page.evaluate(() => ({
    t: window.__losMap!.sceneTime(),
    animating: window.__losMap!.animating(),
    reduced: window.__losMap!.reduced(),
  }));
  expect(atRest.t).toBe(1);
  expect(atRest.animating).toBe(false);
  expect(atRest.reduced).toBe(false);

  // Send a message to Proxima Centauri straight from the map card.
  await page.locator('.star-label-system[data-star="Proxima Centauri"]').click();
  await expect(page.locator(".map-card-name")).toHaveText("Proxima Centauri");
  await page.locator(".map-card-action", { hasText: "Send message" }).click();
  await expect(page.getByRole("heading", { name: "Message to Proxima Centauri" })).toBeVisible();
  await page.locator(".message-textarea").fill("We hear you.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".dialog-modal")).toHaveCount(0);

  // The transmission is now a sphere in the scene, sent in generation 1 and not yet expanded.
  await page.waitForFunction(
    () => (window.__losMap?.spheres() ?? []).some((s) => s.system === "Proxima Centauri" && s.kind === "outgoing"),
    undefined,
    { timeout: 30_000 },
  );
  const beforeAdvance = await page.evaluate(() =>
    window.__losMap!.spheres().filter((s) => s.system === "Proxima Centauri"),
  );
  expect(beforeAdvance.length).toBeGreaterThan(0);
  expect(beforeAdvance[0]!.launchGen).toBe(1);
  expect(beforeAdvance[0]!.radiusLy).toBe(0);

  // W5: the message is readable at map zoom, not only as an expanding shell - a dotted route
  // from Earth to Proxima, a pulse on it, and a label saying when it lands. Proxima is 4.2 LY
  // away, so the engine lands the transmission in Generation 2.
  await page.waitForFunction(
    () => (window.__losMap?.messageLines() ?? []).some((l) => l.system === "Proxima Centauri"),
    undefined,
    { timeout: 30_000 },
  );
  const inFlight = await page.evaluate(() =>
    window.__losMap!.messageLines().filter((l) => l.system === "Proxima Centauri"),
  );
  expect(inFlight.length).toBe(1);
  expect(inFlight[0]!.kind).toBe("outgoing");
  expect(inFlight[0]!.launchGen).toBe(1);
  expect(inFlight[0]!.arrivalGen).toBe(2);
  expect(inFlight[0]!.visible).toBe(true);
  // At rest in generation 1 the pulse is still at Earth: nothing has been travelling yet.
  expect(inFlight[0]!.progress).toBe(0);
  expect(inFlight[0]!.label).toBe("message · arrives Gen 2");
  // No ring yet - the light has not got there, and the ring means it has.
  expect(await page.evaluate(() => window.__losMap!.messageRings())).not.toContain("Proxima Centauri");
  // The label is really on the page, not just in the scene graph.
  await expect(page.locator('.message-label[data-system="Proxima Centauri"]')).toHaveText(
    "message · arrives Gen 2",
  );
  await page.screenshot({ path: "test-results/message-inflight.png", fullPage: true });

  // Advance one generation: nothing is pending yet at Generation 1, so this always applies.
  await page.getByRole("button", { name: "Advance to Next Generation" }).click();
  await page.locator(".dialog-modal").getByRole("button", { name: "Advance", exact: true }).click();

  // Mid-flight: scene time is strictly between the two generations, and Earth is wearing the
  // expanding shell of the transmission. The screenshot is taken as soon as that shell is
  // actually on screen rather than at the first animated frame, when it is still a point.
  await page.waitForFunction(() => window.__losMap?.animating() === true, undefined, {
    timeout: 60_000,
    polling: "raf",
  });
  await page.waitForFunction(
    () =>
      (window.__losMap?.spheres() ?? []).some(
        (s) => s.system === "Proxima Centauri" && s.radiusLy > 1 && s.opacity > 0.4,
      ),
    undefined,
    { timeout: 30_000, polling: "raf" },
  );
  const mid = await page.evaluate(() => ({
    t: window.__losMap!.sceneTime(),
    spheres: window.__losMap!.spheres(),
    leakageLy: window.__losMap!.leakageLy(),
    animating: window.__losMap!.animating(),
  }));
  expect(mid.t).toBeGreaterThan(1);
  expect(mid.t).toBeLessThanOrEqual(2);
  expect(mid.animating).toBe(true);
  await page.screenshot({ path: "test-results/animation.png", fullPage: true });

  // ... and the glide lands exactly on the new generation.
  await page.waitForFunction(() => window.__losMap?.animating() === false, undefined, {
    timeout: 30_000,
    polling: "raf",
  });
  const after = await page.evaluate(() => ({
    t: window.__losMap!.sceneTime(),
    target: window.__losMap!.targetGeneration(),
    samples: window.__losMap!.samples(),
    spheres: window.__losMap!.spheres(),
    leakageLy: window.__losMap!.leakageLy(),
    objects: window.__losMap!.objectCount(),
    frameMs: window.__losMap!.frameMs(),
  }));

  expect(after.target).toBe(2);
  expect(after.t).toBe(2);

  // The map really animated: several distinct scene times, in order, strictly inside (1, 2].
  expect(after.samples.length).toBeGreaterThanOrEqual(3);
  for (const sample of after.samples) {
    expect(sample).toBeGreaterThan(1);
    expect(sample).toBeLessThanOrEqual(2);
  }
  for (let i = 1; i < after.samples.length; i += 1) {
    expect(after.samples[i]!).toBeGreaterThanOrEqual(after.samples[i - 1]!);
  }
  expect(after.samples[after.samples.length - 1]!).toBeGreaterThan(after.samples[0]!);

  // Proxima is 4.2 LY away (the engine states distances to one decimal), so one generation of
  // light travel - 25 LY - overshoots it: the sphere is pinned to the star's distance and has
  // faded out by the time it gets there.
  const proxima = after.spheres.find((s) => s.system === "Proxima Centauri" && s.kind === "outgoing");
  expect(proxima, "the message sphere for Proxima Centauri is gone").toBeTruthy();
  expect(proxima!.radiusLy).toBeCloseTo(4.2, 6);
  expect(proxima!.opacity).toBe(0);

  // The transmission has landed: the route is off the map, and the star wears the permanent
  // cyan ring instead - "we have spoken to them".
  const arrived = await page.evaluate(() => ({
    lines: window.__losMap!.messageLines().filter((l) => l.system === "Proxima Centauri"),
    rings: window.__losMap!.messageRings(),
  }));
  expect(arrived.lines.filter((l) => l.visible)).toEqual([]);
  expect(arrived.rings).toContain("Proxima Centauri");
  // The CSS2D layer keeps the element around and hides it once its pulse stops being drawn.
  await expect(page.locator('.message-label[data-system="Proxima Centauri"]')).toBeHidden();
  await dismissBlockingUi(page);
  await page.screenshot({ path: "test-results/message-arrived.png", fullPage: true });

  // The leakage front grew with the generation, and the animated layer stayed within budget.
  expect(after.leakageLy).toBeGreaterThan(mid.leakageLy);
  expect(after.objects).toBeLessThanOrEqual(150);
  // Reported rather than asserted tightly: a headless GPU is not a performance measurement.
  test.info().annotations.push({ type: "frameMs", description: after.frameMs.toFixed(2) });
  expect(Number.isFinite(after.frameMs)).toBe(true);

  await dismissBlockingUi(page);
  await expect(page.locator(".header-gen")).toContainText("Generation 2");
  await page.screenshot({ path: "test-results/animation-end.png", fullPage: true });

  // The effects toggle survives, and turns the flashes and the nebula off.
  await page.getByRole("button", { name: "Effects: full" }).click();
  await expect(page.getByRole("button", { name: "Effects: reduced" })).toBeVisible();
  // The toolbar re-renders before Preact flushes the effect that reaches the scene, so wait
  // for the map itself rather than for the label.
  await page.waitForFunction(() => window.__losMap?.reduced() === true, undefined, { timeout: 10_000 });
  expect(await page.evaluate(() => window.__losMap!.flashes())).toEqual([]);
  await page.screenshot({ path: "test-results/animation-reduced.png", fullPage: true });
  await page.getByRole("button", { name: "Effects: reduced" }).click();
  await expect(page.getByRole("button", { name: "Effects: full" })).toBeVisible();
  await page.waitForFunction(() => window.__losMap?.reduced() === false, undefined, { timeout: 10_000 });

  // Six more generations of whatever seed 1 produces - discoveries, crises, a leakage front
  // that outgrows the rim and turns into the rim ring. Nothing is asserted about the outcome;
  // the point is that every one of those paths runs without an error and within budget.
  for (let i = 0; i < 6; i += 1) await advanceOneGeneration(page);
  await dismissBlockingUi(page);
  // Advances arrive faster than the 1.5 s glide, so each one restarts it from wherever scene
  // time had got to; it settles on the current generation once they stop.
  await page.waitForFunction(() => window.__losMap?.animating() === false, undefined, {
    timeout: 30_000,
    polling: "raf",
  });
  const late = await page.evaluate(() => ({
    t: window.__losMap!.sceneTime(),
    objects: window.__losMap!.objectCount(),
    leakageLy: window.__losMap!.leakageLy(),
    spheres: window.__losMap!.spheres().length,
  }));
  expect(late.t).toBe(8);
  expect(late.objects).toBeLessThanOrEqual(150);
  // 25 LY per generation of leakage, from generation 1: at generation 8 the front is past the
  // rim of the scene, which is the case the leakage sphere hands over to the rim ring.
  expect(late.leakageLy).toBeGreaterThan(150);
  await page.screenshot({ path: "test-results/animation-generation-8.png", fullPage: true });

  expect(consoleErrors, `console errors: ${consoleErrors.join(" | ")}`).toEqual([]);
});
