> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 103 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🚧 进行中 |
> | 最后更新 | 2026-08-22 |
> | 对应功能/内容 | 小程序电子教练 iOS 端 chooseVideo 选择视频转圈兼容性修复 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-22 | v1.0.0 | 初版 |
>
> **关联文档**：[77：小程序 AI 分析 chooseVideo 选视频失败修复](./77-小程序AI分析chooseVideo选视频失败修复.md)、[99：电子教练时间轴多段剪辑](./99-电子教练时间轴多段剪辑.md)

# 小程序 iOS 端 chooseVideo 选择视频转圈兼容性修复

## 问题描述

小程序端电子教练界面选择视频控件，在 iOS 端会出现选择视频后持续转圈的现象，无法正常返回视频选择结果。

## 根因分析

### 微信社区已知问题

| # | 原因 | 影响 | 严重度 |
|---|------|------|--------|
| 1 | **`wx.chooseVideo` 已停止维护**（基础库 2.21.0 起），iOS 端返回值行为不一致，部分场景不触发 success/fail 回调 | 全平台 | 高 |
| 2 | **`wx.chooseMedia` iOS 端已知 Bug** — `mediaType: ['mix']` 时 iOS 选择视频返回 `chooseMedia:fail`，tempFiles 为空 | iOS 16.x/17.x/18.x | 高 |
| 3 | **隐私协议未声明** — `chooseMedia:fail api scope is not declared in the privacy agreement`（errno 112） | 2023.10.17 后强制 | 高 |
| 4 | **iOS SDK 未配置 Media SDK** — `project.miniapp.json` 需勾选 Media SDK，iOS SDK≥1.3.11 需额外勾选 Video SDK + Image SDK | iOS | 中 |
| 5 | **iPhone 16 + iOS 18 特定问题** — `chooseVideo` 选择视频后无响应，不触发回调（HBuilderX 4.33 已修复） | iPhone 16/iOS 18 | 高 |

### 当前代码现状

当前 `analyze.vue` 使用 `uni.chooseVideo`：
- ✅ 已正确不传 `maxDuration`（避免选择器不弹出）
- ✅ 已有 `fail` 回调处理（用户取消/权限拒绝/通用错误）
- ✅ 已有 `onVideoMeta` 兜底获取视频时长
- ⚠️ 使用的 `uni.chooseVideo` 是**已废弃 API**，未迁移至 `uni.chooseMedia`

## 修复方案

### 1. 将 `uni.chooseVideo` 迁移到 `uni.chooseMedia`

使用 `uni.chooseMedia` 替代已废弃的 `uni.chooseVideo`：
- 设置 `mediaType: ['video']`（非 `mix`，避免 iOS mix 模式 bug）
- 设置 `count: 1`（单选视频）
- `sourceType: ['album', 'camera']`
- 不传 `maxDuration`（相册不限制，拍摄由后续预检查兜底）

### 2. 添加选择超时检测

15 秒内未收到 success/fail 回调则自动取消并提示用户，避免无限转圈。

### 3. 增强 iOS 错误处理

对 `chooseMedia:fail` 增加更细粒度的错误提示：
- 隐私声明未配置 → 提示开发者检查后台配置
- 权限被拒 → 引导用户开启权限
- 文件复制失败 → 提示重试

## 修改文件

- `miniapp/src/pages/coach/analyze.vue` — `chooseVideo()` 函数

## 配置层（需开发者手动操作）

1. **mp.weixin.qq.com 后台**：确保「用户隐私保护指引」已声明「选中的照片或视频信息」和「摄像头」
2. **微信开发者工具**：确认已勾选 Media SDK，iOS SDK≥1.3.11 需额外勾选 Video SDK + Image SDK
