/**
 * JWT 解析与过期判断工具。
 *
 * 参考 tarot 项目 `src/utils/token.ts` 的做法：登录态 = token 存在且 JWT `exp` 未过期。
 * 兼容微信小程序（无 `atob`）与 H5 端，故使用纯 JS 的 base64url 解码。
 */

/**
 * base64url 解码为字符串（微信小程序无 `atob`，自行实现）。
 * 失败时返回空字符串。
 */
function base64UrlDecode(input: string): string {
  // base64url → base64
  let b64 = input.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64.length % 4;
  if (pad) b64 += "=".repeat(4 - pad);
  try {
    // 优先用全局 atob（H5 环境）
    if (typeof atob === "function") {
      return decodeURIComponent(
        Array.prototype.map
          .call(atob(b64), (c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
          .join(""),
      );
    }
  } catch {
    // atob 失败时继续走手动解码
  }
  const bin = (str: string): string => {
    const bytes = new Uint8Array(str.length);
    for (let i = 0; i < str.length; i++) bytes[i] = str.charCodeAt(i);
    return String.fromCharCode(...bytes);
  };
  const binary = bin(b64.replace(/=/g, "").replace(/\+/g, "+").replace(/\//g, "/"));
  let out = "";
  let i = 0;
  while (i < binary.length) {
    const c1 = binary.charCodeAt(i++);
    const c2 = binary.charCodeAt(i++);
    const c3 = binary.charCodeAt(i++);
    // 处理中文字符的 UTF-8 解码
    if ((c1 & 0x80) === 0) {
      out += String.fromCharCode(c1);
    } else if ((c1 & 0xe0) === 0xc0) {
      out += String.fromCharCode(((c1 & 0x1f) << 6) | (c2 & 0x3f));
    } else if ((c1 & 0xf0) === 0xe0) {
      out += String.fromCharCode(((c1 & 0x0f) << 12) | ((c2 & 0x3f) << 6) | (c3 & 0x3f));
    }
  }
  return out;
}

/**
 * 解码 JWT payload，返回对象。
 * 解析失败返回 null。
 */
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const payload = base64UrlDecode(parts[1]);
    return JSON.parse(payload) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * 判断 token 是否已过期。
 * - 无 `exp` 字段 → 视为未过期（宽松处理，兼容当前后端签发的不含 exp 的 JWT）
 * - 有 `exp` 字段 → `Date.now() >= exp * 1000` 即为过期
 * - 解析失败 → 视为过期（安全失败）
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload) return true;
  const exp = payload.exp as number | undefined;
  if (typeof exp !== "number") return false;
  return Date.now() >= exp * 1000;
}

/**
 * 是否已登录：token 存在且未过期。
 */
export function isLoggedIn(token: string): boolean {
  if (!token) return false;
  return !isTokenExpired(token);
}
