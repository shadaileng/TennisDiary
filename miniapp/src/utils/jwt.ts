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
/**
 * 将 base64 字符串按字节还原为 UTF-8 解码后的字符串。
 * 纯手动实现，避免使用展开运算符（`String.fromCharCode(...bytes)`）等
 * 在微信小程序 DevTools 二次编译时可能解析失败的写法。
 */
function bytesToString(bytes: Uint8Array): string {
  let out = "";
  for (let i = 0; i < bytes.length; i++) out += String.fromCharCode(bytes[i]);
  return out;
}

/**
 * 手动 base64 → 二进制字符串。
 * 说明：payload 中的非 ASCII（中文）字符经 base64 编码后还原为原始 UTF-8 字节，
 * 因此这里不做 UTF-8 解码，交由 `decodeUtf8` 统一处理。
 */
function base64ToBinaryString(input: string): string {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let out = "";
  let buffer = 0;
  let bits = 0;
  for (let i = 0; i < input.length; i++) {
    const c = input.charAt(i);
    if (c === "=") break;
    const idx = chars.indexOf(c);
    if (idx < 0) continue;
    buffer = (buffer << 6) | idx;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      out += String.fromCharCode((buffer >> bits) & 0xff);
    }
  }
  return out;
}

/** UTF-8 字节序列解码为字符串（兼容微信小程序）。 */
function decodeUtf8(binary: string): string {
  let out = "";
  let i = 0;
  while (i < binary.length) {
    const c1 = binary.charCodeAt(i++);
    if ((c1 & 0x80) === 0) {
      out += String.fromCharCode(c1);
    } else if ((c1 & 0xe0) === 0xc0) {
      const c2 = binary.charCodeAt(i++);
      out += String.fromCharCode(((c1 & 0x1f) << 6) | (c2 & 0x3f));
    } else if ((c1 & 0xf0) === 0xe0) {
      const c2 = binary.charCodeAt(i++);
      const c3 = binary.charCodeAt(i++);
      out += String.fromCharCode(
        ((c1 & 0x0f) << 12) | ((c2 & 0x3f) << 6) | (c3 & 0x3f),
      );
    } else {
      // 4 字节（emoji 等），按码点拼接，此处简单跳过字节避免误读
      const c2 = binary.charCodeAt(i++);
      const c3 = binary.charCodeAt(i++);
      const c4 = binary.charCodeAt(i++);
      const code =
        ((c1 & 0x07) << 18) |
        ((c2 & 0x3f) << 12) |
        ((c3 & 0x3f) << 6) |
        (c4 & 0x3f);
      if (code > 0xffff) {
        const cc = code - 0x10000;
        out += String.fromCharCode(
          0xd800 + (cc >> 10),
          0xdc00 + (cc & 0x3ff),
        );
      } else {
        out += String.fromCharCode(code);
      }
    }
  }
  return out;
}

function base64UrlDecode(input: string): string {
  // base64url → base64
  let b64 = input.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64.length % 4;
  if (pad) b64 += "=".repeat(4 - pad);
  try {
    // 优先用全局 atob（H5 环境）
    if (typeof atob === "function") {
      const bytes: number[] = [];
      const bin = atob(b64);
      for (let i = 0; i < bin.length; i++) bytes.push(bin.charCodeAt(i));
      return decodeUtf8(bytesToString(new Uint8Array(bytes)));
    }
  } catch {
    // atob 失败时继续走手动解码
  }
  const binary = base64ToBinaryString(b64);
  return decodeUtf8(binary);
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
