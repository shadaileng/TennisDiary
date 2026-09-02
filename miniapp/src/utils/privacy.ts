/**
 * 通用隐私/权限错误处理工具
 *
 * 对齐微信官方推荐方案（参考 tarot）：
 * - manifest.json 设置 __usePrivacyCheck__: true，由微信自动拉起官方隐私弹窗
 * - 开发者需在 mp.weixin.qq.com 后台配置「用户隐私保护指引」声明 API 用途
 * - 运行时权限（auth deny / denied）→ 引导 openSetting
 * - 隐私声明未配置（errno 112）→ 无法由代码修复，通用提示
 * - 取消操作 → 仅记录日志
 */

// ==================== 错误分类 ====================

/** 用户主动取消操作 */
export function isUserCancel(err: any): boolean {
  return /cancel/i.test(String(err?.errMsg || ''));
}

/**
 * 运行期权限被拒（auth deny / denied）
 * 对应微信设置中「相册/相机」等权限被用户关闭
 */
export function isRuntimePermissionDenied(err: any): boolean {
  const msg = String(err?.errMsg || '');
  return /auth deny|auth denied|denied|is denied/i.test(msg);
}

/**
 * 隐私声明未配置（errno 112：api scope is not declared in the privacy agreement）
 * 说明开发者未在 mp.weixin.qq.com 后台「用户隐私保护指引」中声明对应 API 用途
 */
export function isPrivacyScopeError(err: any): boolean {
  const msg = String(err?.errMsg || '');
  return err?.errno === 112 || /privacy|隐私|scope is not declared/i.test(msg);
}

// ==================== 隐私授权引导 ====================

/** 查询当前隐私授权状态；低版本基础库或异常时按「无需授权」兜底 */
export function checkPrivacySetting(): Promise<{ needAuthorization: boolean; privacyContractName: string }> {
  return new Promise((resolve) => {
    // #ifdef MP-WEIXIN
    if (typeof wx !== "undefined" && typeof wx.getPrivacySetting === "function") {
      wx.getPrivacySetting({
        success: (res) => resolve(res),
        fail: () => resolve({ needAuthorization: false, privacyContractName: "" }),
      });
      return;
    }
    // #endif
    resolve({ needAuthorization: false, privacyContractName: "" });
  });
}

/**
 * 在用户手势内编程式拉起微信隐私授权弹窗。
 * - 已授权 / 低版本基础库：立即成功
 * - 用户同意：resolve(true)
 * - 用户拒绝或接口失败：resolve(false)
 */
export function requirePrivacyAuthorize(): Promise<boolean> {
  return new Promise((resolve) => {
    // #ifdef MP-WEIXIN
    if (typeof wx !== "undefined" && typeof wx.requirePrivacyAuthorize === "function") {
      wx.requirePrivacyAuthorize({
        success: () => resolve(true),
        fail: () => resolve(false),
      });
      return;
    }
    // #endif
    resolve(true);
  });
}

/** 打开官方「用户隐私保护指引」全文 */
export function openPrivacyContract(): void {
  // #ifdef MP-WEIXIN
  if (typeof wx !== "undefined" && typeof wx.openPrivacyContract === "function") {
    wx.openPrivacyContract({});
  }
  // #endif
}
