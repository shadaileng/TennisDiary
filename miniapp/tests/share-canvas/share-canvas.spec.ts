import { test, expect } from "@playwright/test";
import {
  renderShareCard,
  createMonthlyData,
  createTodayDiaryData,
  createTechScoreData,
  createEmptyData,
} from "./helpers";

test.describe("Share Canvas Layout Regression", () => {
  test("月度战报 - 完整数据", async ({ page }) => {
    const { image, height } = await renderShareCard("月度战报", createMonthlyData(5));
    expect(height).toBe(1220); // 1120 + 100 footer
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await expect(page).toHaveScreenshot("monthly-full.png");
  });

  test("今日日记 - 有复盘内容", async ({ page }) => {
    const { image, height } = await renderShareCard("今日日记", createTodayDiaryData("今天练习了正手击球，感觉进步明显。"));
    expect(height).toBe(1280); // 1180 + 100 footer
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await expect(page).toHaveScreenshot("today-with-notes.png");
  });

  test("今日日记 - 空数据", async ({ page }) => {
    const { image, height } = await renderShareCard("今日日记", createEmptyData());
    expect(height).toBe(1280); // 1180 + 100 footer
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await expect(page).toHaveScreenshot("today-empty.png");
  });

  test("技术评分 - 6维度雷达图", async ({ page }) => {
    const { image } = await renderShareCard("技术评分", createTechScoreData(6));
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await expect(page).toHaveScreenshot("tech-score-radar.png");
  });

  test("技术评分 - 维度不足3个", async ({ page }) => {
    const { image } = await renderShareCard("技术评分", createTechScoreData(2));
    await page.setContent(`<html><body style="margin:0;padding:0;background:#f5f5f5"><img src="data:image/png;base64,${image.toString("base64")}" /></body></html>`);
    await expect(page).toHaveScreenshot("tech-score-ball.png");
  });

  test("高度计算一致性 - 月度战报", async () => {
    const data = createMonthlyData(5);
    const { height } = await renderShareCard("月度战报", data);
    expect(height).toBe(1220);
  });

  test("高度计算一致性 - 今日日记", async () => {
    const data = createTodayDiaryData();
    const { height } = await renderShareCard("今日日记", data);
    expect(height).toBe(1280);
  });

  test("高度计算一致性 - 技术评分", async () => {
    const data = createTechScoreData(6);
    const { height } = await renderShareCard("技术评分", data);
    expect(height).toBeGreaterThan(800);
    expect(height).toBeLessThan(2000);
  });
});
