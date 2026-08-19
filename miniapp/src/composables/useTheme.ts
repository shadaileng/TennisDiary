import { computed } from "vue";

import { useSettingsStore } from "@/stores";

/**
 * 生成 <page-meta> 的主题注入。
 *
 * 页面模板顶部使用：
 *   <page-meta :page-style="themeStyle" :background-color="themeBg" />
 *
 * 微信小程序将 CSS 变量写入 page 节点，沿组件树继承（含自定义组件）；
 * background-color 同步窗口背景色（下拉/回弹区域），避免与页面背景色差。
 */
export function useThemeStyle() {
  const settings = useSettingsStore();
  const themeStyle = computed(() => {
    const t = settings.themePalette;
    return `--color-accent:${t.accent};--color-accent-dark:${t.dark};`
      + `--color-accent-soft:${t.soft};--color-accent-rgb:${t.rgb};`
      + `--color-page-bg:${t.pageBg};--color-card:${t.card};--color-border:${t.border};`
      + `--color-hero-a:${t.heroA};--color-hero-b:${t.heroB}`;
  });
  /** 窗口背景色（page-meta background-color 需十六进制值） */
  const themeBg = computed(() => settings.themePalette.pageBg);
  return { themeStyle, themeBg };
}