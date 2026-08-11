> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 31 |
> | 文档版本 | v1.2.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-11 |
> | 对应功能/内容 | Phase 2-5：我的页（用户信息 + 手动登录/登出 + 设置入口），补齐 Step 25 遗留的手动登录入口 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.1.0 | 实施完成：我的页（用户信息 + 手动登录/登出 + 设置） |
> | 2026-08-11 | v1.2.0 | 修复「编辑资料」重复跳转：移除整卡点击，收敛到右侧箭头 + 底部按钮（`.stop` 阻止冒泡） |
>
> **关联文档**：[Phase 2 总纲（26）](./26-Phase2-业务页面实现总纲.md) · [Phase1-8 对接登录（20）](./20-Phase1-8-对接B1登录流程.md) · [Step 25 静默登录门控（25）](./25-静默登录门控-首次启动不请求后台.md)

# Step 31：Phase 2-5 我的页

## 一、目标

1. **我的页** `pages/mine/mine.vue`：改造占位页为「用户信息 + 登录/登出 + 设置」页
2. **手动登录入口**：补齐 Step 25 遗留的「首次启动不请求后台，等待用户手动登录」的登录按钮（`auth.login()` 完整链路）
3. **设置入口**：金额隐私开关、主题偏好开关（`settings` store）

## 二、现状盘点

- ✅ `auth` store 完整：`login()`（wx.login → token → user）、`logout()`、`init()`、`isLoggedIn` getter
- ✅ `settings` store 完整：`hideAmounts`/`useLimeTheme` + `toggle*` + `persist()`
- ✅ Step 25 已完成静默登录门控，但手动登录入口未设计（文档明确「后续另行设计」）
- ⚠️ `pages/mine/mine.vue` 是纯占位页

## 三、决策记录

| 决策点 | 结论 |
|---|---|
| 登录交互 | 未登录显示「微信一键登录」按钮 → `auth.login()`，成功刷新；已登录显示用户 + 「退出登录」 |
| 登录状态刷新 | 页面 `onShow` 时若已登录且无 user，尝试 `getMe()` 补全（避免深层刷新丢用户态） |
| 设置开关 | 金额隐私（`hideAmounts`）、主题偏好（`useLimeTheme`），用 switch 组件 |
| 退出交互 | 已登录卡片显示「退出登录」，`auth.logout()` + toast |
| 数据备份 | 小程序数据在后端，本地备份不适用，暂缓（B1 未提供导出接口） |

## 四、技术方案

### 4.1 我的页 `pages/mine/mine.vue`

**用户信息卡**（Hero）：
- 已登录：头像（`auth.user.avatar_url`）+ 昵称（`nickname`）+ openid 简写
- 未登录：占位头像 + 「未登录」+ 提示

**操作区**：
- 未登录：整卡可点的「微信一键登录」按钮 → `auth.login()`
- 已登录：「编辑资料」按钮 + 卡片右侧 `›` 箭头 → `navigateTo` 到 `pages/profile-edit/profile-edit`（编辑资料页）；卡片其他区域不触发跳转
- 退出登录：在编辑资料页底部，`uni.showModal` 确认 → `auth.logout()`

**设置区**（CellGroup + switch）：
- 金额隐私：`settings.hideAmounts` 开关
- 主题偏好：`settings.useLimeTheme` 开关

**关于**：版本信息 + slogan

### 4.2 设置 switch

小程序内置 `switch` 组件，`:checked` + `@change` 绑定 `settings.toggle*`。

## 五、产出物

### 新建文件

| 文件 | 说明 |
|---|---|
| `docs/plans/31-Phase2-5-我的页.md` | 本方案文档 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `miniapp/src/pages/mine/mine.vue` | 占位页 → 用户 + 登录/登出 + 设置 |
| `docs/README.md` / `config.mts` / `AGENTS.md` | 文档同步 |

## 六、验收标准

- [x] 已登录：显示头像/昵称；未登录：显示「未登录」+ 登录按钮
- [x] 未登录点登录 → `auth.login()` 完整链路成功，刷新用户态
- [x] 已登录点退出 → `uni.showModal` 确认 → `auth.logout()`，恢复未登录态
- [x] 金额隐私 / 主题偏好开关切换并持久化（storage）
- [x] `pnpm type-check` 通过
- [x] `pnpm build:mp-weixin` 构建成功

## 七、提交拆分

1. `feat(miniapp): 我的页（用户信息 + 手动登录/登出 + 设置入口）`（MINOR bump）
2. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase 2-5 完成 + Phase 2 收尾）`

## 八、执行记录

- 2026-08-07：实施完成
  - 重写 `pages/mine/mine.vue`：用户信息卡（头像/昵称/登录态）+ 手动登录/登出 + 设置开关（金额隐私/青柠主题）+ 关于
  - 补齐 Step 25 遗留的手动登录入口：未登录显示「微信一键登录」→ `auth.login()`；已登录显示「退出登录」→ `auth.logout()`（`uni.showModal` 确认）
  - 设置开关用小程序 `switch` 绑定 `settings.toggleHideAmounts()`/`toggleLimeTheme()`
  - 验证：`pnpm type-check`、`pnpm build:mp-weixin` 通过
- 2026-08-11：修复「编辑资料」重复跳转
  - 问题：用户信息卡 `profile-card` 整体绑定 `@tap` 跳转，且底部「编辑资料」按钮位于卡内也绑定 `@tap`，事件冒泡导致 `goEditProfile()` 触发两次，`uni.navigateTo` 打开两个编辑资料页
  - 修复：移除整张卡的 `@tap` 与 `clickable` class；跳转收敛到卡片右侧 `›` 箭头（`@tap="goEditProfile"`）与底部「编辑资料」按钮（`@tap.stop="goEditProfile"`，`.stop` 阻止冒泡）
  - 验证：`pnpm type-check` 通过
