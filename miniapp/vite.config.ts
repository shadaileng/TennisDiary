import fs from "node:fs";
import path from "node:path";
import { defineConfig, loadEnv, type Plugin } from "vite";
import uni from "@dcloudio/vite-plugin-uni";
import { WeappTailwindcss } from "weapp-tailwindcss/vite";

/**
 * 构建期注入微信小程序配置（参照 shadaileng/tarot）：
 * - 读取环境变量 TD_APPID / TD_URL_CHECK（非 VITE_ 前缀，不进入打包产物）
 * - 写入构建产物 project.config.json 的 appid 与 setting.urlCheck
 * - 不改动 src/manifest.json，避免 git 污染；H5 构建无该文件自动跳过
 */
function injectWeixinConfigPlugin(): Plugin {
  return {
    name: "vite-plugin-inject-weixin-config",
    closeBundle() {
      const env = loadEnv(process.env.NODE_ENV || "development", process.cwd(), "");
      const appid = env.TD_APPID;
      if (!appid) return;

      const urlCheck = env.TD_URL_CHECK === undefined ? false : env.TD_URL_CHECK === "true";
      const isProd = process.env.NODE_ENV === "production";
      const dir = isProd ? "dist/build/mp-weixin" : "dist/dev/mp-weixin";
      const configPath = path.resolve(__dirname, dir, "project.config.json");

      try {
        if (!fs.existsSync(configPath)) return;
        const config = JSON.parse(fs.readFileSync(configPath, "utf-8"));
        let changed = false;
        if (config.appid !== appid) {
          config.appid = appid;
          changed = true;
        }
        if (!config.setting) config.setting = {};
        if (config.setting.urlCheck !== urlCheck) {
          config.setting.urlCheck = urlCheck;
          changed = true;
        }
        if (changed) {
          fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
        }
      } catch {
        // 产物缺失或解析失败时静默跳过，不影响构建结果
      }
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig({
  css: {
    preprocessorOptions: {
      scss: {
        silenceDeprecations: ["legacy-js-api"],
        additionalData: `@use "@/styles/tokens.scss" as *;`,
      },
    },
  },
  plugins: [
    uni(),
    WeappTailwindcss({
      rem2rpx: true,
      tailwindcssBasedir: __dirname,
      cssEntries: [path.resolve(__dirname, "src/app.css")],
    }),
    injectWeixinConfigPlugin(),
  ],
});
