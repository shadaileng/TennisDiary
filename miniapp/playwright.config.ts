import { defineConfig } from "@playwright/test";
import { resolve } from "path";
import { config } from "dotenv";

config({ path: resolve(__dirname, ".env.test") });

export default defineConfig({
  testDir: "./tests",
  timeout: 30000,
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
      threshold: 0.2,
    },
  },
  use: {
    headless: true,
    viewport: { width: 1080, height: 1920 },
    launchOptions: {
      executablePath: process.env.CHROME_PATH || undefined,
    },
  },
  projects: [
    {
      name: "share-canvas",
      testDir: "./tests/share-canvas",
    },
    {
      name: "components",
      testDir: "./tests/components",
    },
  ],
});
