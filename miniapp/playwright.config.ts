import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 30000,
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
    },
  },
  use: {
    headless: true,
    viewport: { width: 1080, height: 1920 },
  },
  projects: [
    {
      name: "share-canvas",
      testDir: "./tests/share-canvas",
    },
  ],
});
