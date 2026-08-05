import { defineStore } from "pinia";

/** storage 键名 */
const SETTINGS_KEY = "td_settings";

interface SettingsState {
  /** 金额隐私开关：隐藏具体花费 */
  hideAmounts: boolean
  /** 视觉偏好：是否使用青柠强调主题 */
  useLimeTheme: boolean
}

const defaultSettings = (): SettingsState => ({
  hideAmounts: false,
  useLimeTheme: true,
});

/**
 * 全局设置 store
 *
 * 管理金额隐私、视觉偏好等本地偏好，持久化到 storage。
 */
export const useSettingsStore = defineStore("settings", {
  state: defaultSettings,

  getters: {
    /** 是否隐藏金额 */
    shouldHideAmounts: (state): boolean => state.hideAmounts,
  },

  actions: {
    /** 初始化：从 storage 恢复偏好（App onLaunch 调用） */
    init() {
      const raw = uni.getStorageSync(SETTINGS_KEY);
      if (raw) {
        try {
          Object.assign(this, JSON.parse(raw) as Partial<SettingsState>);
        } catch {
          // 忽略损坏的 storage
        }
      }
    },

    /** 持久化当前偏好 */
    persist() {
      uni.setStorageSync(SETTINGS_KEY, JSON.stringify({
        hideAmounts: this.hideAmounts,
        useLimeTheme: this.useLimeTheme,
      }));
    },

    /** 切换金额隐私 */
    toggleHideAmounts() {
      this.hideAmounts = !this.hideAmounts;
      this.persist();
    },

    /** 切换主题偏好 */
    toggleLimeTheme() {
      this.useLimeTheme = !this.useLimeTheme;
      this.persist();
    },
  },
});
