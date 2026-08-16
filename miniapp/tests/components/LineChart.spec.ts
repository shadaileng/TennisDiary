import { test, expect } from "@playwright/test";
import { renderLineChart } from "./helpers";
import type { LineData } from "./helpers";

const SCREENSHOT_OPTIONS = {
  animations: "disabled" as const,
  maxDiffPixelRatio: 0.02,
};

test.describe("LineChart Visual Regression", () => {
  test("正常折线 - 5个数据点", async ({ page }) => {
    const data: LineData[] = [
      { label: "周一", value: 65 },
      { label: "周二", value: 72 },
      { label: "周三", value: 68 },
      { label: "周四", value: 80 },
      { label: "周五", value: 75 },
    ];
    const image = renderLineChart(data);
    await page.setContent(`
      <html>
        <body style="margin:0;padding:0;background:#f5f5f5">
          <img src="data:image/png;base64,${image.toString("base64")}" />
        </body>
      </html>
    `);
    await expect(page).toHaveScreenshot("line-5points.png", SCREENSHOT_OPTIONS);
  });

  test("单数据点", async ({ page }) => {
    const data: LineData[] = [{ label: "唯一", value: 85 }];
    const image = renderLineChart(data);
    await page.setContent(`
      <html>
        <body style="margin:0;padding:0;background:#f5f5f5">
          <img src="data:image/png;base64,${image.toString("base64")}" />
        </body>
      </html>
    `);
    await expect(page).toHaveScreenshot("line-single.png", SCREENSHOT_OPTIONS);
  });

  test("空数据显示占位", async ({ page }) => {
    const data: LineData[] = [];
    const image = renderLineChart(data);
    await page.setContent(`
      <html>
        <body style="margin:0;padding:0;background:#f5f5f5">
          <img src="data:image/png;base64,${image.toString("base64")}" />
        </body>
      </html>
    `);
    await expect(page).toHaveScreenshot("line-empty.png", SCREENSHOT_OPTIONS);
  });

  test("带单位的数值", async ({ page }) => {
    const data: LineData[] = [
      { label: "1月", value: 70.5 },
      { label: "2月", value: 68.2 },
      { label: "3月", value: 72.8 },
      { label: "4月", value: 69.1 },
    ];
    const image = renderLineChart(data, 320, 120, "#C8DA2B", "kg");
    await page.setContent(`
      <html>
        <body style="margin:0;padding:0;background:#f5f5f5">
          <img src="data:image/png;base64,${image.toString("base64")}" />
        </body>
      </html>
    `);
    await expect(page).toHaveScreenshot("line-with-unit.png", SCREENSHOT_OPTIONS);
  });
});
