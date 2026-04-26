import { expect, type Locator, type Page, test } from "@playwright/test";

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(2);
}

async function expectSingleLine(locator: Locator) {
  const metrics = await locator.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return {
      height: rect.height,
      lineHeight: Number.parseFloat(style.lineHeight),
      scrollWidth: element.scrollWidth,
      clientWidth: element.clientWidth,
    };
  });

  expect(metrics.height).toBeLessThanOrEqual(metrics.lineHeight * 1.25);
  expect(metrics.scrollWidth - metrics.clientWidth).toBeLessThanOrEqual(1);
}

test("fight card hero keeps balanced fighter cards", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByText("Armwrestling Math")).toBeVisible();
  await expect(page.getByText("Ermes")).toBeVisible();
  await expect(page.getByText("Gasparini")).toBeVisible();
  await expect(page.getByText("Artyom")).toBeVisible();
  await expect(page.getByText("Morozov")).toBeVisible();

  await expectNoHorizontalOverflow(page);

  const ermesCard = page.locator(".fighter-card-left");
  const morozovCard = page.locator(".fighter-card-right");
  await expect(ermesCard).toBeVisible();
  await expect(morozovCard).toBeVisible();

  const ermesBox = await ermesCard.boundingBox();
  const morozovBox = await morozovCard.boundingBox();
  expect(ermesBox).not.toBeNull();
  expect(morozovBox).not.toBeNull();

  if (testInfo.project.name === "desktop") {
    expect(Math.abs(ermesBox!.width - morozovBox!.width)).toBeLessThanOrEqual(2);
  }

  for (const label of ["Gasparini", "Morozov"]) {
    const name = page.getByText(label, { exact: true });
    const box = await name.boundingBox();
    expect(box).not.toBeNull();
    await expectSingleLine(name);
    if (testInfo.project.name === "desktop") {
      expect(box!.height).toBeLessThan(90);
    } else {
      expect(box!.height).toBeLessThan(76);
    }
  }

  await page.screenshot({
    path: `test-results/${testInfo.project.name}-hero.png`,
    fullPage: false,
  });
});

test("expanded receipts stay usable on the target viewport", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByText("VIEW DATA").first().click();
  await expect(page.getByText("ALL CLAIMS")).toBeVisible();
  await expect(page.getByText("CLICK TIMESTAMP FOR ORIGINAL")).toBeVisible();

  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: `test-results/${testInfo.project.name}-receipts.png`,
    fullPage: false,
  });
});
