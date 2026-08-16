import { test, expect } from "@playwright/test";
import { renderRadarChart } from "./helpers";
import type { RadarData } from "./helpers";

const SCREENSHOT_OPTIONS = {
  animations: "disabled" as const,
  maxDiffPixelRatio: 0.02,
};

test.describe("RadarChart Visual Regression", () => {
  test("6维度雷达图 - 完整数据", async ({ page }) => {
    const data: RadarData[] = [
      { name: "正手", score: 85 },
      { name: "反手", score: 72 },
      { name: "发球", score: 90 },
      { name: "截击", score: 68 },
      { name: "移动", score: 78 },
      { name: "战术", score: 82 },
    ];
    const image = renderRadarChart(data);
    await page.setContent(`
      <html>
        <body style="margin:0;padding:0;background:#f5f5f5">
          <img src="data:image/png;base64,${image.toString("base64")}" />
        </body>
      </html>
    `);
    await expect(page).toHaveScreenshot("radar-6dim.png", SCREENSHOT_OPTIONS);
  });

  test("3维度雷达图 - 最小有效数据", async ({ page }) => {
    const data: RadarData[] = [
      { name: "正手", score: 80 },
      { name: "反手", score: 70 },
      { name: "发球", score: 90 },
    ];
    const image = renderRadarChart(data);
    await page.setContent(`
      <html>
        <body style="margin:0;padding:0;background:#f5f5f5">
          <img src="data:image/png;base64,${image.toString("base64")}" />
        </body>
      </html>
    `);
    await expect(page).toHaveScreenshot("radar-3dim.png", SCREENSHOT_OPTIONS);
  });

  test("维度不足3个 - 显示占位文本", async ({ page }) => {
    const data: RadarData[] = [
      { name: "正手", score: 80 },
      { name: "反手", score: 70 },
    ];
    const image = renderRadarChart(data);
    await page.setContent(`
      <html>
        <body style="margin:0;padding:0;background:#f5f5f5">
          <img src="data:image/png;base64,${image.toString("base64")}" />
        </body>
      </html>
    `);
    await expect(page).toHaveScreenshot("radar-placeholder.png", SCREENSHOT_OPTIONS);
  });

  test("空数据显示占位", async ({ page }) => {
    const data: RadarData[] = [];
    const image = renderRadarChart(data);
    await page.setContent(`
      <html>
        <body style="margin:0;padding:0;background:#f5f5f5">
          <img src="data:image/png;base64,${image.toString("base64")}" />
        </body>
      </html>
    `);
    await expect(page).toHaveScreenshot("radar-empty.png", SCREENSHOT_OPTIONS);
  });
});
