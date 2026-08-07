> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 40 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-07 |
> | 对应功能/内容 | 「我的」页 + 「编辑资料（资料详情）」页参考 tarot 项目进行视觉与交互改造：用户卡升级、功能菜单化、退出登录移入资料详情页、资料编辑改为每字段自动保存 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.1.0 | 实施：mine.vue 用户卡渐变+统计徽章+功能菜单（未登录隐藏菜单）；profile-edit.vue 居中大头像+每字段自动保存+底部退出登录；`type-check` 与 `build:mp-weixin` 通过 |
> | 2026-08-07 | v1.2.0 | 修复 Tailwind 自定义色未生成（`@config` 注入 + 独立 `app.css` 入口，对齐 tarot），全项目品牌色类恢复；全量检查构建/类型/lint 通过 |
>
> **关联文档**：[Step 38：修复登录时序与用户资料编辑](./38-修复登录时序与用户资料编辑-参考tarot.md) · [Phase2-5：我的页](./31-Phase2-5-我的页.md) · [Phase2-4：统计页](./30-Phase2-4-统计页.md) · [参考仓库 tarot](https://github.com/shadaileng/tarot)

# Step 40：我的页与资料详情页 tarot 化改造

## 一、背景

当前「我的」页（`mine.vue`）与「编辑资料」页（`profile-edit.vue`）视觉较为简陋、交互偏传统：

| 问题 | 现状 |
|------|------|
| 我的页用户卡 | 纯色卡片堆叠，无渐变/徽章/统计大数字，视觉无层次 |
| 我的页功能入口 | 设置开关直接平铺，无 tarot「图标 + 标签 + 箭头」卡片式菜单美感 |
| 我的页退出登录 | 直接放在用户卡操作区，视觉拥挤 |
| 资料编辑页 | 依赖整卡「保存」按钮批量保存，需手动点击；无 tarot 每字段自动保存的流畅体验 |
| 资料编辑页视觉 | 头像偏小、表单无细分隔线节奏、无退出登录入口 |

用户要求：**资料详情（编辑资料）页的样式布局也参考 tarot `profile-detail.vue`**，保存交互采用 **方案 A（每字段自动保存）**。

## 二、目标

1. 「我的」页参考 tarot `profile.vue` 重构：渐变用户卡（带统计徽章）、功能入口卡片式菜单。
2. 「编辑资料」页参考 tarot `profile-detail.vue` 重构：居中大头像、细分隔线表单、每字段自动保存、底部退出登录。
3. 退出登录从「我的」主页面移除，仅保留在资料详情页（与 tarot 一致）。
4. 保持项目青柠/橄榄 Tailwind 配色体系，沿用现有 store 与 services 逻辑，不破坏游客模式与既有鉴权。

## 三、方案设计

### 3.1 「我的」页（`mine.vue`）

按 tarot 三段式布局重构，保持青柠/橄榄 Tailwind 体系。**已登录**与**未登录**两种状态布局如下：

#### 已登录布局

```
┌────────────────────────────────┐
│ 用户信息卡（深橄榄渐变 + 青柠光斑） │
│  头像 | 昵称 | ID | 性别·生日  ›  │
│  累计打球N次 | 累计时长 | 装备N件   │  ← 登录时拉 /stats
│  [编辑资料] 主按钮                │
└────────────────────────────────┘
│ 功能入口（卡片式菜单）             │
│  📊 统计总览              ›       │
│  ⚙️ 编辑资料              ›       │
│  💰 金额隐私          [开关]       │
│  🎨 青柠主题          [开关]       │
└────────────────────────────────┘
│ 关于区域                          │
└────────────────────────────────┘
```

#### 未登录布局（游客态）

```
┌────────────────────────────────┐
│ 用户信息卡（深橄榄渐变 + 青柠光斑） │
│  🎾 头像 | 未登录                │
│  登录后可同步日记数据             │
│  [微信一键登录] 主按钮            │  ← 唯一登录入口
└────────────────────────────────┘
│ （功能菜单整体隐藏，不显示）        │
│ 关于区域                          │
└────────────────────────────────┘
```

**关键点**：

- **用户卡**：`bg-gradient-to-br from-olive via-olive-mid to-olive` 深色渐变 + 青柠光斑（`bg-lime/20 blur-2xl`）；头像青柠描边 `ring-2 ring-lime/70`；昵称加粗加大。
- **统计徽章区**：登录后拉取 `getStats()`，展示「累计打球 / 累计时长 / 装备」三列玻璃卡（`bg-white/10`），失败静默降级为 0，不阻塞页面。
- **功能菜单**：每行「图标 + 标签 + 箭头/开关」，`统计总览` 用 `switchTab` 跳统计 Tab，`编辑资料` 用 `navigateTo` 跳资料详情页。
- **退出登录**：从主页面**移除**（移到资料详情页），`doLogout` 函数一并删除。
- **游客模式**：未登录不发请求，统计区隐藏，主按钮显示「微信一键登录」。
  - **登录入口决策**：仅保留用户卡内**一个「微信一键登录」按钮**。tarot 的底部 `LoginGuide` 引导卡在小程序端虽也是微信登录，但其卡片内入口面向 H5 邮箱登录场景；本项目为纯微信小程序，**不采用** tarot 底部 `LoginGuide` 引导卡，避免重复入口。
  - **功能菜单可见性**：未登录时**不显示**功能菜单（统计总览/编辑资料/金额隐私/青柠主题均隐藏），只保留用户卡（登录引导）+ 关于区；登录后才显示功能菜单。

### 3.2 资料详情页（`profile-edit.vue`）

参考 tarot `profile-detail.vue`，采用**方案 A（每字段自动保存）**：

```
┌────────────────────────────────┐
│     头像（居中大图 120rpx）       │
│        🎾 / avatar-img          │
│       点击更换头像                │
└────────────────────────────────┘
│ 白底圆角卡片                       │
│  昵称  [输入框]        (blur/confirm 自动保存) │
│  ────── 细分隔线                  │
│  性别  [保密/男/女]  ›  (picker 变更即保存)    │
│  ────── 细分隔线                  │
│  生日  [日期]        ›  (picker 变更即保存)    │
└────────────────────────────────┘
│  退出登录（居中红色，独立）          │
└────────────────────────────────┘
```

**关键点**：

- **头像**：居中大图（`w-[120rpx] h-[120rpx]` 或等值 Tailwind 类），下方「点击更换头像」提示；小程序 `open-type="chooseAvatar"`，H5 用 `uni.chooseImage` 降级（沿用 Step 38 条件编译方案）。
- **每字段自动保存**：
  - 昵称：`@blur` / `@confirm` 触发保存，空值忽略。
  - 性别：`picker @change` 变更即 `updateProfile({ gender })`。
  - 生日：`picker @change` 变更即 `updateProfile({ birthday })`。
  - 头像：选择后先 `uploadAvatar` 再 `updateProfile({ avatar_url })`。
- **去掉整卡「保存」按钮**；每次保存成功 `updateUser` 同步本地，用轻提示反馈。
- **退出登录**：放表单下方独立居中红色入口，`showModal` 确认后 `authStore.logout()` + `switchTab` 回「我的」Tab。

## 四、验收标准

1. 「我的」页用户卡为深橄榄渐变 + 青柠光斑，登录后展示三列统计徽章，点击可跳转统计 Tab / 编辑资料。
2. 「我的」页功能入口为「图标 + 标签 + 箭头/开关」卡片式菜单，金额隐私 / 青柠主题开关正常。
3. 「我的」页**不再出现**退出登录入口。
4. 资料详情页为居中大头像 + 细分隔线表单，无整卡保存按钮。
5. 昵称失焦、性别/生日变更即自动保存并同步本地用户缓存，成功有轻提示。
6. 资料详情页底部有独立「退出登录」，确认后回到「我的」Tab 且登录态清空。
7. 游客模式：未登录「我的」页不发 `/stats` 请求，显示「微信一键登录」。
8. `ruff` 无关（纯前端）；`miniapp` 下 `pnpm build:mp-weixin` 构建通过、`pnpm type-check` 通过，无编译错误。
9. **Tailwind 自定义色修复**：`dist/build/mp-weixin/app.wxss` 中应包含 `from-olive`/`via-olive-mid`/`to-olive`/`bg-olive`/`bg-paper`/`bg-lime/20`/`ring-lime/70` 等品牌色类（运行 `grep -cE "olive|lime|paper" app.wxss` 验证 > 0）。

## 五、实施步骤

1. **重构 `mine.vue`**：用户卡渐变 + 统计徽章 + 功能菜单 + 移除退出登录；`script` 增加 `getStats` 拉取（登录时）与 `goStats` / `goEditProfile` 跳转。
2. **重构 `profile-edit.vue`**：居中大头像、细分隔线表单、每字段自动保存（昵称 blur、性别/生日 change）、新增退出登录。
3. **验证**：构建编译无误，手工验收交互（登录态/游客态、自动保存、退出跳转）。

## 六、Tailwind 集成问题修复（重要）

实施中发现**全项目自定义色类（`olive`/`lime`/`paper`/`ink`）从未被生成到 WXSS**，导致所有页面品牌色失效（界面纯白、无层次）。根因与修复如下：

### 根因

- `vite.config.ts` 里 `WeappTailwindcss({ cssEntries: [src/App.vue] })` 指向 **Vue 组件**；weapp-tailwindcss 解析 `App.vue` 时**无法正确提取其 `<style lang="scss">` 内的 `@tailwind utilities` 指令**。
- 因此 weapp-tailwindcss 虽接管了 Tailwind CSS 生成，但**加载不到 `tailwind.config.js` 的自定义色**，回退到内置默认 config，仅生成默认色（`bg-white` 等）与基础工具类；`bg-olive`、`from-olive` 等被当作「未知类」丢弃。

### 修复（对齐 tarot 集成方式）

| 文件 | 改动 |
|------|------|
| `miniapp/src/app.css`（新建） | 独立 Tailwind 样式入口：`@config "../tailwind.config.js";` + `@tailwind base; @tailwind components; @tailwind utilities;` |
| `miniapp/src/App.vue` | `<style>`（非 scoped、非 scss）`@import '@/app.css';` |
| `miniapp/vite.config.ts` | `cssEntries` 改为指向 `src/app.css`；补充 `tailwindcssBasedir: __dirname` |
| `miniapp/tailwind.config.js` | `content` 扩展为 `./src/**/*.{html,js,ts,jsx,tsx,vue}`（排除 node_modules/dist/unpackage） |

**关键点**：`@config` 指令**显式指定 config 路径**，使 weapp-tailwindcss 的运行时无论基于何 cwd 都能加载到 `tailwind.config.js`，从而正确识别所有自定义色类。此问题影响**全项目**（日记/装备/统计页的品牌色一并修复）。

## 七、涉及文件

| 文件 | 改动 |
|------|------|
| `miniapp/src/pages/mine/mine.vue` | 重构用户卡/功能菜单/统计徽章；移除退出登录 |
| `miniapp/src/pages/profile-edit/profile-edit.vue` | tarot 化布局 + 每字段自动保存 + 新增退出登录 |
| `miniapp/src/app.css` | 新建：独立 Tailwind 入口 + `@config` |
| `miniapp/src/App.vue` | 改为非 scoped `@import '@/app.css'` |
| `miniapp/vite.config.ts` | `cssEntries`/`tailwindcssBasedir` 修正 |
| `miniapp/tailwind.config.js` | `content` 扩展、移除无用 safelist |

复用（不改动）：`stores/auth.ts`、`stores/settings.ts`、`services/auth.ts`、`services/data.ts`（`getStats`）、`types`（`Stats`/`User`）、`utils`（`resolveUploadUrl`/`maskMiddle`/`fmtDuration`）。
