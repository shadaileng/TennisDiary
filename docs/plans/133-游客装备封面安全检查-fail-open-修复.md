> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 133 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-09-05 |
> | 对应功能/内容 | 游客装备封面安全检查 fail-open 修复：技术故障时明确报错而非静默放行 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-09-05 | v1.0.0 | 初版：分析根因（`.catch(() => true)` 无条件 fail-open），提出按状态区分方案 |
> | 2026-09-05 | v1.1.0 | 实施完成：后端返回业务错误码，前端移除 fail-open，toast 提示用户 |
>
> **关联文档**：[104-微信内容安全API集成](./104-微信内容安全API集成.md)、[129-日记装备统计游客本地降级与登录同步](./129-日记装备统计游客本地降级与登录同步.md)

# Step 133：游客装备封面安全检查 fail-open 修复

## 一、问题描述

### 1.1 现状

`POST /api/upload/guest-gear-check` 是游客态装备封面「仅检即弃」检查端点：
- 免鉴权（游客无 token）
- 调用微信 `imgSecCheck` 进行内容安全扫描
- 通过 → 返回 `200 {data: {safe: true}}`，前端保存本地 dataURL
- 违规 → 返回 `400`，前端拦截并 toast 提示

**根因 Bug**：前端 `guestCheckGearImage` 的 `.catch(() => true)` 无条件 fail-open：

```typescript
// miniapp/src/utils/index.ts:211-212
export function guestCheckGearImage(filePath: string, code: string): Promise<boolean> {
  return uploadRaw<{ safe?: boolean }>({ ... })
    .then((d) => !!d.safe)
    .catch(() => true);  // ← 任何异常（网络错误/500/参数校验）都返回 true（安全）
}
```

### 1.2 影响

| 场景 | 后端行为 | 前端处理 | 结果 |
|------|---------|---------|------|
| 违规图片 | 400 HTTP | `uploadRaw` reject → catch → `true` | ✗ **违规但放行** |
| 技术故障（网络/500） | 200 `{safe: true}` | `uploadRaw` resolve → `.then(() => true)` | ✗ **故障但视为通过** |
| 网络错误 | - | `uploadRaw` reject → catch → `true` | ✗ **网络故障但放行** |
| 正常通过 | 200 `{safe: true}` | resolve → `true` | ✓ |

**用户可见症状**：后台请求失败时，小程序端没有提示错误，反而继续显示/保存封面图片。

### 1.3 设计矛盾

原设计意图（见代码注释）：
> fail-open：微信/网络侧异常时返回 safe:true 放行（前端存本地 dataURL，登录同步时仍二次受检）

**问题**：前端无法区分「后端明确返回 safe:true」vs「后端技术故障放行」，导致所有故障场景都被静默放行。

---

## 二、修复方案

### 2.1 核心原则

**按状态区分，技术故障不应静默放行**。

| 场景 | 后端响应 | 前端处理 | 用户可见 |
|------|---------|---------|---------|
| 违规图片 | 400 HTTP | reject → toast | 「图片未通过内容安全检测」 |
| 技术故障 | 200 `{code:50001, success:false}` | reject → toast | 「安全检查失败，请重试」 |
| 网络错误 | - | reject → toast | 「安全检查失败，请重试」 |
| 正常通过 | 200 `{data:{safe:true}}` | resolve → `true` | 图片保存成功 |

### 2.2 改动文件

| 文件 | 改动内容 |
|------|---------|
| `server/app/routers/upload.py` | `guest_gear_check`：技术故障时返回业务错误码（非 `safe: true`） |
| `server/tests/routers/test_upload.py` | 更新 `test_guest_check_fail_open` 断言 |
| `miniapp/src/utils/index.ts` | `guestCheckGearImage`：移除 `.catch(() => true)`，明确要求 `safe === true` |
| `miniapp/src/pages/gear/form.vue` | 捕获异常并 toast 提示 |

---

## 三、详细设计

### 3.1 后端改动

**文件**：`server/app/routers/upload.py`

```python
# 改前（L268-271）
except Exception as exc:
    # fail-open：微信/网络异常放行（正式上传兜底受检）
    log.error("游客封面安全检查异常，放行: %s", exc, exc_info=True)
    return ApiResponse(data={"safe": True})

# 改后
except Exception as exc:
    # 技术故障：返回明确错误码，前端据此拒绝保存
    log.error("游客封面安全检查异常: %s", exc, exc_info=True)
    return ApiResponse(
        code=ErrorCode.INTERNAL_ERROR,
        message="安全检查服务异常，请重试",
        success=False,
        data=None,
    )
```

**需同步添加导入**（L17 已有 `ApiResponse`）：
```python
from app.schemas.common import ApiResponse, ErrorCode
```

### 3.2 前端改动

**文件**：`miniapp/src/utils/index.ts`

```typescript
// 改前（L205-213）
export function guestCheckGearImage(filePath: string, code: string): Promise<boolean> {
  return uploadRaw<{ safe?: boolean }>({
    path: "/upload/guest-gear-check",
    filePath,
    formData: { code },
  })
    .then((d) => !!d.safe)
    .catch(() => true);  // ← 移除这行
}

// 改后
export function guestCheckGearImage(filePath: string, code: string): Promise<boolean> {
  return uploadRaw<{ safe?: boolean }>({
    path: "/upload/guest-gear-check",
    filePath,
    formData: { code },
  }).then((d) => d.safe === true);  // ← 明确要求 safe 字段为 true
}
```

**文件**：`miniapp/src/pages/gear/form.vue`（L195-201）

```typescript
// 改前
const safe = await guestCheckGearImage(tempPath, code);
if (!safe) {
  uni.showToast({ title: "图片未通过内容安全检测", icon: "none" });
  return;
}
form.photo = await compressToDataURL(tempPath);

// 改后（移到 try-catch 外层）
try {
  const safe = await guestCheckGearImage(tempPath, code);
  if (!safe) {
    uni.showToast({ title: "图片未通过内容安全检测", icon: "none" });
    return;
  }
  form.photo = await compressToDataURL(tempPath);
} catch (checkErr) {
  logError("游客封面安全检查失败", { error: (checkErr as Error).message }, undefined, "gear_photo_guest_check_failed", undefined, traceId);
  uni.showToast({ title: "安全检查失败，请重试", icon: "none" });
  return;
}
```

### 3.3 测试更新

**文件**：`server/tests/routers/test_upload.py`（L154-163）

```python
# 改前
def test_guest_check_fail_open(self, _mock_check, _mock_openid, client):
    """微信/网络异常 → 200 {safe:true} fail-open（正式上传兜底受检）"""
    response = client.post(...)
    assert response.status_code == 200
    assert response.json()["data"]["safe"] is True

# 改后
def test_guest_check_fail_open(self, _mock_check, _mock_openid, client):
    """微信/网络异常 → 200 {code:50001, success:false} 前端据此拒绝保存"""
    response = client.post(...)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 50001
    assert data["success"] is False
    assert data["data"] is None
```

---

## 四、风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 技术故障时用户无法保存图片 | 低 | 登录同步时 `/api/upload/gear-image` 仍有二次受检兜底 |
| 现有功能回归 | 低 | 正常流程 unchanged，仅改变错误处理路径 |
| 测试覆盖不足 | 中 | 需更新 `test_guest_check_fail_open` 断言；新增 `test_guest_check_server_error` 用例 |

---

## 五、验证计划

### 5.1 后端验证（TDD 模式）

```bash
# 1. RED：先运行测试，确认失败
cd server && uv run pytest tests/routers/test_upload.py::TestGuestGearCheck::test_guest_check_fail_open -v

# 2. GREEN：修改 upload.py 后重新运行
cd server && uv run pytest tests/routers/test_upload.py::TestGuestGearCheck -v

# 3. 全量 fast 测试
cd server && uv run pytest -q -m fast
```

### 5.2 前端验证

```bash
cd miniapp && pnpm run type-check && pnpm run build:mp-weixin
```

### 5.3 手动测试矩阵

| 场景 | 操作 | 预期结果 |
|------|------|---------|
| 正常通过 | 游客选合规图片 | toast 无提示，图片保存成功 |
| 违规图片 | 游客选违规图片 | toast 「图片未通过内容安全检测」，图片不保存 |
| 技术故障 | 断开网络/停止后端 | toast 「安全检查失败，请重试」，图片不保存 |
| 网络超时 | 模拟慢网络（>60s） | toast 「安全检查失败，请重试」，图片不保存 |

---

## 六、向后兼容性

### 6.1 破坏性变更

**是**。后端响应格式变化：
- 改前：技术故障 → `200 {data: {safe: true}}`
- 改后：技术故障 → `200 {code: 50001, success: false, data: null}`

**影响范围**：仅影响游客态封面安全检查场景，且原行为是 Bug（故障时静默放行），修复后行为更合理。

### 6.2 兜底机制

登录同步时（`sync.ts` 的 `syncGears()`）仍走正式受检上传 `POST /api/upload/gear-image`，该端点已有完善的异常处理（`except Exception` → 400），不会被此次变更影响。

---

## 七、执行步骤

1. **更新文档**（本文档）→ 标记状态 `🚧 进行中`
2. **后端 TDD**：
   - RED：更新测试断言，确认测试失败
   - GREEN：修改 `upload.py`，确认测试通过
   - 验证：运行全量 fast 测试
3. **前端实现**：
   - 修改 `utils/index.ts`
   - 修改 `pages/gear/form.vue`
   - 验证：type-check + build
4. **更新文档** → 标记状态 `✅`

---

## 八、相关 Issue

- [104-微信内容安全API集成](./104-微信内容安全API集成.md)：原始安全检查实现
- [129-日记装备统计游客本地降级与登录同步](./129-日记装备统计游客本地降级与登录同步.md)：游客封面检查端点背景
