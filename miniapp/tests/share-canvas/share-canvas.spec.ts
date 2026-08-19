import { test, expect } from "@playwright/test";
import { createCanvas, loadImage } from "@napi-rs/canvas";
import {
  renderShareCard,
  renderTechScoreZone,
  createMonthlyData,
  createTodayDiaryData,
  createTechScoreData,
  createEmptyData,
} from "./helpers";

const SCREENSHOT_OPTIONS = {
  animations: "disabled" as const,
  maxDiffPixelRatio: 0.02,
};

function countDarkPixels(img: Buffer, x: number, y: number, w: number, h: number): Promise<number> {
  return loadImage(img).then((image) => {
    const c = createCanvas(image.width, image.height);
    const ctx = c.getContext("2d");
    ctx.drawImage(image, 0, 0);
    const data = ctx.getImageData(x, y, w, h).data;
    let count = 0;
    for (let i = 0; i < data.length; i += 4) {
      const lum = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
      if (lum < 100) count++;
    }
    return count;
  });
}

test.describe("Share Canvas Layout Regression", () => {
  test("月度战报 - 5次训练", async ({ page }) => {
    const { image, height } = await renderShareCard("月度战报", createMonthlyData(5));
    expect(height).toBe(1400);
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await page.locator("img").waitFor({ state: "visible" });
    await expect(page.locator("img")).toHaveScreenshot("monthly-5diaries.png", SCREENSHOT_OPTIONS);
  });

  test("今日日记 - 有复盘内容", async ({ page }) => {
    const { image, height } = await renderShareCard("今日日记", createTodayDiaryData("今天练习了正手击球，感觉进步明显。重点练习了随挥收拍动作，教练说收拍轨迹完整但略显僵硬，需要放松。"));
    expect(height).toBe(1440);
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await page.locator("img").waitFor({ state: "visible" });
    await expect(page.locator("img")).toHaveScreenshot("today-with-review.png", SCREENSHOT_OPTIONS);
  });

  test("今日日记 - 空数据", async ({ page }) => {
    const { image, height } = await renderShareCard("今日日记", createTodayDiaryData(""));
    expect(height).toBe(1440);
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await page.locator("img").waitFor({ state: "visible" });
    await expect(page.locator("img")).toHaveScreenshot("today-empty.png", SCREENSHOT_OPTIONS);
  });

  test("技术评分 - 6维度雷达图", async ({ page }) => {
    const { image } = await renderShareCard("技术评分", createTechScoreData(6));
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await page.locator("img").waitFor({ state: "visible" });
    await expect(page.locator("img")).toHaveScreenshot("tech-score-radar.png", SCREENSHOT_OPTIONS);
  });

  test("技术评分 - 维度不足3个", async ({ page }) => {
    const { image } = await renderShareCard("技术评分", createTechScoreData(2));
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await page.locator("img").waitFor({ state: "visible" });
    await expect(page.locator("img")).toHaveScreenshot("tech-score-ball.png", SCREENSHOT_OPTIONS);
  });

  test("高度计算一致性 - 月度战报", async () => {
    const data = createMonthlyData(5);
    const { height } = await renderShareCard("月度战报", data);
    expect(height).toBe(1400);
  });

  test("高度计算一致性 - 今日日记", async () => {
    const data = createTodayDiaryData();
    const { height } = await renderShareCard("今日日记", data);
    expect(height).toBe(1440);
  });

  test("高度计算一致性 - 技术评分", async () => {
    const data = createTechScoreData(6);
    const { height } = await renderShareCard("技术评分", data);
    expect(height).toBeGreaterThan(800);
    expect(height).toBeLessThan(3000);
  });

  test("技术评分 - 雷达图区域", async ({ page }) => {
    const { image } = await renderTechScoreZone("radar", createTechScoreData(6));
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await page.locator("img").waitFor({ state: "visible" });
    await expect(page.locator("img")).toHaveScreenshot("tech-score-radar-zone.png", SCREENSHOT_OPTIONS);
  });

  test("技术评分 - 进度条区域", async ({ page }) => {
    const { image } = await renderTechScoreZone("progress", createTechScoreData(6));
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await page.locator("img").waitFor({ state: "visible" });
    await expect(page.locator("img")).toHaveScreenshot("tech-score-progress-zone.png", SCREENSHOT_OPTIONS);
  });

  test("技术评分 - 总结区域", async ({ page }) => {
    const { image } = await renderTechScoreZone("summary", createTechScoreData(6));
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await page.locator("img").waitFor({ state: "visible" });
    await expect(page.locator("img")).toHaveScreenshot("tech-score-summary-zone.png", SCREENSHOT_OPTIONS);
  });

  test("技术评分 - 三区域完整渲染", async ({ page }) => {
    const { image } = await renderShareCard("技术评分", createTechScoreData(6));
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await page.locator("img").waitFor({ state: "visible" });
    await expect(page.locator("img")).toHaveScreenshot("tech-score-full.png", SCREENSHOT_OPTIONS);
  });

  test("二维码绘制在底部右下角", async () => {
    const { image, height } = await renderShareCard("技术评分", createTechScoreData(6));
    const count = await countDarkPixels(image, 1080 - 70 - 160, height - 200, 160, 160);
    expect(count).toBeGreaterThan(500);
  });
});
