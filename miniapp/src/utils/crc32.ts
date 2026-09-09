/**
 * CRC32（IEEE 802.3）表驱动实现
 *
 * 用途：分片上传的**片级**完整性校验（140 决策 19/20）。
 * - 小程序端无 ArrayBuffer 摘要 API（`getFileInfo` 只对整文件算 MD5），
 *   纯 JS 的 MD5 在 100MB 量级耗时数秒，不可接受；
 * - CRC32 表驱动约 5MB / 30~60ms，20 片累计 <1.5s；
 * - 完整性最终仍由服务端「整文件 MD5」兜底，片级 CRC32 只用于定位坏片。
 *
 * 与后端 `zlib.crc32` 结果对齐（多项式 0xEDB88320，初值 0xFFFFFFFF，结果取反）。
 */

let cachedTable: Uint32Array | null = null;

/** 惰性建表（首次调用约 0.1ms，之后常驻） */
function ensureTable(): Uint32Array {
  if (cachedTable) return cachedTable;
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i += 1) {
    let value = i;
    for (let bit = 0; bit < 8; bit += 1) {
      value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    }
    table[i] = value >>> 0;
  }
  cachedTable = table;
  return table;
}

/**
 * 计算 CRC32，返回 8 位小写 hex（服务端按 16 进制解析比对，前导零不可省）
 */
export function crc32Of(data: ArrayBuffer | Uint8Array): string {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
  const table = ensureTable();
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) {
    crc = table[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  }
  return ((crc ^ 0xffffffff) >>> 0).toString(16).padStart(8, "0");
}
