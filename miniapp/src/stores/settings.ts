import { defineStore } from "pinia";

import { STORAGE_KEYS } from "@/constants/storage";

/** storage 键名统一从常量读取 */
const SETTINGS_KEY = STORAGE_KEYS.settings;

/** 球场主题标识 */
export type ThemeKey = "lime" | "ao" | "french" | "wimbledon";

/** 主题色板 */
export interface ThemePalette {
  /** 主题标识 */
  key: ThemeKey
  /** 主题名称 */
  name: string
  /** 主题描述 */
  desc: string
  /** 主强调色（「网球」品牌色，所有主题恒定青柠） */
  accent: string
  /** 深强调色 */
  dark: string
  /** 浅强调色 */
  soft: string
  /** RGB 三元组（用于 rgba(var(--color-accent-rgb), α)） */
  rgb: string
  /** 页面背景 / 次级表面（「球场」） */
  pageBg: string
  /** 卡片表面（「球场」上的浅色卡面） */
  card: string
  /** 分隔线 / 边框 */
  border: string
  /** 深色大卡渐变起 */
  heroA: string
  /** 深色大卡渐变止 */
  heroB: string
}

/**
 * 大满贯球场主题注册表（唯一数据源，store 与「我的」页选择 UI 共用）。
 *
 * 设计隐喻：**网球恒青柠**（按钮/标签/图表等强调元素不随主题漂移，保持品牌识别），
 * **球场随主题**（页面背景/卡片/分隔线按球场取色，营造场地氛围）。
 * 故 accent/dark/soft/rgb 四主题恒为青柠，仅 pageBg/card/border/heroA/heroB 变化。
 */
export const THEMES: ThemePalette[] = [
  { key: "lime", name: "青柠", desc: "品牌默认 · 现代硬地球场", accent: "#C8DA2B", dark: "#A8B822", soft: "#F0F5CE", rgb: "200, 218, 43", pageBg: "#F2F2EF", card: "#FFFFFF", border: "#E7E9DF", heroA: "#242B1F", heroB: "#3A4433" },
  { key: "ao", name: "澳网", desc: "澳网 · 硬地蓝", accent: "#C8DA2B", dark: "#A8B822", soft: "#F0F5CE", rgb: "200, 218, 43", pageBg: "#D8E5F4", card: "#F0F7FD", border: "#BDD0E8", heroA: "#16293F", heroB: "#2C4A6E" },
  { key: "french", name: "法网", desc: "法网 · 红土", accent: "#C8DA2B", dark: "#A8B822", soft: "#F0F5CE", rgb: "200, 218, 43", pageBg: "#E2CABC", card: "#F8EDE5", border: "#D5BAA8", heroA: "#3C231A", heroB: "#5E382A" },
  { key: "wimbledon", name: "温网", desc: "温网 · 草地", accent: "#C8DA2B", dark: "#A8B822", soft: "#F0F5CE", rgb: "200, 218, 43", pageBg: "#D0E0C9", card: "#EDF5E9", border: "#B8CFAB", heroA: "#20301C", heroB: "#3B5226" },
];

interface SettingsState {
  /** 金额隐私开关：隐藏具体花费 */
  hideAmounts: boolean
  /** 球场主题 */
  theme: ThemeKey
}

const defaultSettings = (): SettingsState => ({
  hideAmounts: false,
  theme: "lime",
});

/** 校验主题值，非法值回退默认 */
function isThemeKey(value: unknown): value is ThemeKey {
  return THEMES.some((t) => t.key === value);
}

/**
 * 全局设置 store
 *
 * 管理金额隐私、球场主题等本地偏好，持久化到 storage。
 */
export const useSettingsStore = defineStore("settings", {
  state: defaultSettings,

  getters: {
    /** 是否隐藏金额 */
    shouldHideAmounts: (state): boolean => state.hideAmounts,
    /** 当前主题色板 */
    themePalette: (state): ThemePalette =>
      THEMES.find((t) => t.key === state.theme) ?? THEMES[0],
  },

  actions: {
    /** 初始化：从 storage 恢复偏好（App onLaunch 调用） */
    init() {
      const raw = uni.getStorageSync(SETTINGS_KEY);
      if (raw) {
        try {
          const saved = JSON.parse(raw) as Partial<SettingsState> & { useLimeTheme?: boolean };
          // 旧数据迁移：useLimeTheme 从未生效，忽略其值，默认 theme = lime
          Object.assign(this, {
            hideAmounts: saved.hideAmounts ?? false,
            theme: isThemeKey(saved.theme) ? saved.theme : "lime",
          });
        } catch {
          // 忽略损坏的 storage
        }
      }
    },

    /** 持久化当前偏好 */
    persist() {
      uni.setStorageSync(SETTINGS_KEY, JSON.stringify({
        hideAmounts: this.hideAmounts,
        theme: this.theme,
      }));
    },

    /** 切换金额隐私 */
    toggleHideAmounts() {
      this.hideAmounts = !this.hideAmounts;
      this.persist();
    },

    /** 设置球场主题 */
    setTheme(key: ThemeKey) {
      if (!isThemeKey(key)) return;
      this.theme = key;
      this.persist();
    },
  },
});