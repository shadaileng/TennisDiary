> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 77 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-13 |
> | 对应功能/内容 | 修复小程序 AI 分析页 `uni.chooseVideo` 点击无响应 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-13 | v1.0.0 | 初版 |
>
> **关联文档**：[75-5：Phase 4 电子教练小程序页](./75-5-Phase4-电子教练小程序页.md)

# 修复小程序 AI 分析 chooseVideo 选视频失败

## 问题现象

小程序「AI 分析」页面（`pages/coach/analyze.vue`）点击「选择视频」区域无任何响应，文件选择器不弹出，无 Loading 遮罩。

## 排查过程

### 第一步：添加 fail 回调定位错误

原始代码 `chooseVideo` 函数只有 `success` 回调，`uni.chooseVideo` 失败时静默无响应，无法定位问题。

```ts
// 原始代码（无 fail 回调）
function chooseVideo() {
  uni.chooseVideo({
    sourceType: ["album", "camera"],
    maxDuration: 90,
    success: (res) => {
      videoPath.value = res.tempFilePath;
      hitTime.value = 0;
    },
  });
}
```

添加 `fail` 回调后，控制台输出：

```
[chooseVideo] 失败 {errMsg: "chooseVideo:fail|maxDuration can not over 60"}
(env: Windows,mp,2.02.2607171; lib: 3.17.0)
```

### 第二步：分析错误原因

`maxDuration` 是 `uni.chooseVideo` 的**约束参数**，用于告知文件选择器"只允许选择 X 秒以内的视频"。微信小程序运行时在**弹出选择器之前**就校验此参数：

- `maxDuration: 90` 超过微信平台限制（最大 60 秒）
- 参数校验失败，直接拒绝调用，选择器未弹出

> 注意：这是前置约束，不是"选完视频后检查时长"。

### 第三步：确认权限不是问题

`uni.chooseVideo` / `uni.chooseMedia` 是用户侧 UI API，不需要在 `manifest.json` 中声明权限，系统会在运行时弹出授权弹窗。当前 `mp-weixin` 配置已足够。

## 修复内容

### 1. `maxDuration: 90` → `60`

**文件**：`miniapp/src/pages/coach/analyze.vue:126`

```ts
function chooseVideo() {
  uni.chooseVideo({
    sourceType: ["album", "camera"],
    maxDuration: 60,  // 修正：微信小程序上限 60 秒
    success: (res) => {
      videoPath.value = res.tempFilePath;
      hitTime.value = 0;
    },
    fail: (err) => {
      console.error("[chooseVideo] 失败", err);
      if (err.errMsg && !err.errMsg.includes("cancel")) {
        uni.showToast({ title: "选择视频失败，请检查权限设置", icon: "none" });
      }
    },
  });
}
```

### 2. 提示文案同步更新

**文件**：`miniapp/src/pages/coach/analyze.vue:44`

```diff
- 支持 mp4 / mov，单次挥拍最长 15 秒 · 综合分析最长 90 秒
+ 支持 mp4 / mov，单次挥拍最长 15 秒 · 综合分析最长 60 秒
```

## 经验总结

| 要点 | 说明 |
|------|------|
| API 约束参数是前置校验 | `maxDuration` 在调用时即校验，不等用户选完文件 |
| 微信小程序 API 限制 | `chooseVideo` 的 `maxDuration` 上限为 60 秒 |
| 始终添加 fail 回调 | `uni.*` API 失败时无默认提示，必须自行处理 |
| 权限声明不是必须 | `chooseVideo` / `chooseMedia` 是用户侧 UI API，运行时授权 |
