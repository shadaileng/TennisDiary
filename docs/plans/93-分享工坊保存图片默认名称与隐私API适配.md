> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 93 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🚧 进行中 |
> | 最后更新 | 2026-08-17 |
> | 对应功能/内容 | 分享工坊保存图片默认名称 + 微信小程序隐私API适配 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-17 | v1.0.0 | 初版 |
| 2026-08-17 | v1.0.1 | 开始实施：share.vue 新增 cardSavePath、USER_DATA_PATH 持久化写入、超时保护；manifest.json 添加 __usePrivacyCheck__；构建通过 |
>
> **关联文档**：[75-6 Phase 5 分享工坊](./75-6-Phase5-分享工坊.md) · [tarot 小程序隐私API适配方案](https://github.com/shadaileng/tarot-solutions/blob/master/docs/plans/17-微信小程序隐私API适配方案.md)（参考）

# 93：分享工坊保存图片默认名称与隐私 API 适配

## 一、背景与目标

### 1.1 问题描述

分享工坊（`pages/share/share.vue`）保存图片到相册时存在两个问题：

| 问题 | 现象 | 原因 |
|------|------|------|
| **文件名空白** | 保存到相册后文件名显示为空或随机时间戳 | `canvasToTempFilePath` 返回的是微信临时路径（`wxfile://tmp_...`），该路径不含有意义文件名，保存后相册中无法直观识别 |
| **隐私 API 风险** | 调用 `saveImageToPhotosAlbum` 未配置隐私保护指引 | 微信小程序自 2023-10-17 起要求所有使用隐私相关 API 的小程序在后台声明隐私用途，否则可能报错 `appid privacy api banned` |

### 1.2 参考方案

tarot 参考项目（`docs/reference/tarot`）采用以下方案解决文件名问题：

```typescript
// poster.ts — 写入 USER_DATA_PATH 持久路径（含文件名）
const fs = uni.getFileSystemManager()
const data = fs.readFileSync(dlRes.tempFilePath)
const path = `${wx.env.USER_DATA_PATH}/poster-save-${Date.now()}.png`
fs.writeFileSync(path, data)
// saveImageToPhotosAlbum 使用持久路径而非临时路径
uni.saveImageToPhotosAlbum({ filePath: savePath })
```

此方案同时解决了隐私 API 问题——微信官方自动弹窗方案无需自定义代码，只需确保：
1. 微信公众平台已配置「保存用户图片到相册」隐私声明
2. 基础库版本 ≥ 2.32.3

## 二、解决方案

### 2.1 文件名方案：写入 USER_DATA_PATH 持久路径

**核心思路**：将 canvas 导出的临时文件写入 `wx.env.USER_DATA_PATH`（小程序本地持久化目录，无需任何权限），文件名包含日期信息，再以此路径调用 `saveImageToPhotosAlbum`。

**文件名规则**：

| 模板 | 文件名格式 | 示例 |
|------|-----------|------|
| 月度战报 | `网球月报-{YYYY-MM}.png` | `网球月报-2026-08.png` |
| 今日日记 | `网球日记-{YYYY-MM-DD}.png` | `网球日记-2026-08-17.png` |
| 技术评分 | `网球技术评分-{YYYY-MM-DD}.png` | `网球技术评分-2026-08-17.png` |

### 2.2 隐私 API 适配：依赖微信官方弹窗

根据 tarot 项目的经验（方案 26），采用**微信官方隐私弹窗方案**：

- 不注册 `wx.onNeedPrivacyAuthorization` 监听
- 不调用自定义隐私弹窗
- 微信在首次调用隐私 API 时自动弹出官方授权弹窗
- 用户同意后才执行 `saveImageToPhotosAlbum`

**前置条件**：需在微信公众平台手动配置隐私保护指引（无法代码完成）。

## 三、变更文件清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `miniapp/src/pages/share/share.vue` | 新增持久路径逻辑 + 超时保护 |
| 修改 | `miniapp/src/manifest.json` | 添加 `__usePrivacyCheck__: true` |

## 四、实施方案

### 4.1 share.vue 变更

#### 4.1.1 新增 ref

```typescript
const cardSavePath = ref("")  // 持久路径，用于保存相册
```

#### 4.1.2 draw() 成功回调中追加持久化写入

在 `canvasToTempFilePath` 的 `success` 回调中，将临时文件写入持久路径：

```typescript
success: (r: { tempFilePath: string }) => {
  cardURL.value = r.tempFilePath
  // #ifdef MP-WEIXIN
  const fs = uni.getFileSystemManager()
  try {
    const now = new Date()
    const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`)
    const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
    const monthStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
    let fileName: string
    if (tpl.value === "月度战报") {
      fileName = `网球月报-${monthStr}.png`
    } else if (tpl.value === "今日日记") {
      fileName = `网球日记-${dateStr}.png`
    } else {
      fileName = `网球技术评分-${dateStr}.png`
    }
    const savePath = `${wx.env.USER_DATA_PATH}/${fileName}`
    const data = fs.readFileSync(r.tempFilePath)
    fs.writeFileSync(savePath, data)
    cardSavePath.value = savePath
  } catch {
    // 写入失败不影响展示，降级使用 tempFilePath
  }
  // #endif
},
```

#### 4.1.3 saveImage() 使用持久路径 + 超时保护

```typescript
function saveImage() {
  if (saving.value || !cardURL.value) return
  saving.value = true

  let saveTimedOut = false
  const saveTimeout = setTimeout(() => {
    if (saving.value) {
      saveTimedOut = true
      saving.value = false
      uni.showToast({ title: "保存超时，请重试", icon: "none" })
    }
  }, 10000)

  uni.saveImageToPhotosAlbum({
    filePath: cardSavePath.value || cardURL.value,
    success: () => {
      if (saveTimedOut) return
      clearTimeout(saveTimeout)
      uni.showToast({ title: "已保存到相册", icon: "success" })
      saving.value = false
    },
    fail: (err) => {
      if (saveTimedOut) return
      clearTimeout(saveTimeout)
      if (err.errMsg?.includes("auth") || err.errMsg?.includes("denied")) {
        uni.showModal({
          title: "需要相册权限",
          content: "请在设置中允许保存图片到相册",
          confirmText: "去设置",
          success: (m) => {
            if (m.confirm) uni.openSetting()
          },
        })
      } else {
        uni.showToast({ title: "保存失败，请重试", icon: "none" })
      }
      saving.value = false
    },
  })
}
```

### 4.2 manifest.json 变更

在 `mp-weixin` 配置中添加隐私检查开关：

```json
"mp-weixin": {
  "appid": "",
  "setting": {
    "urlCheck": false
  },
  "usingComponents": true,
  "__usePrivacyCheck__": true
}
```

### 4.3 微信公众平台手动配置（必须）

以下操作**无法通过代码完成**，需在发布前手动配置：

1. 登录 [mp.weixin.qq.com](https://mp.weixin.qq.com)
2. 进入 **设置 → 基本设置 → 服务内容声明 → 用户隐私保护指引**
3. 点击 **更新**，添加声明：
   - **保存用户图片到相册**：用于保存网球数据分享卡片
4. 提交审核并等待通过

## 五、验证

```bash
# 类型检查
cd miniapp && pnpm run type-check

# 小程序构建
cd miniapp && pnpm run build:mp-weixin
```

## 六、注意事项

1. **`wx.env.USER_DATA_PATH` 是微信专属 API**，需 `#ifdef MP-WEIXIN` 条件编译，H5 端不受影响
2. **无需额外权限**：`USER_DATA_PATH` 是小程序内置本地存储目录，无需申请任何权限即可读写
3. **降级处理**：持久路径写入失败时，`filePath` 自动降级为 `cardURL.value`（tempFilePath），不影响基本功能
4. **基础库版本**：隐私 API 从基础库 2.32.3 开始支持，低于此版本不会触发隐私检查
5. **测试方法**：开发者工具中「清除模拟器缓存 → 清除授权数据」可重置隐私授权状态
