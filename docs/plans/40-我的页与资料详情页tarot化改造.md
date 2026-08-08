> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 40 |
> | 文档版本 | v1.3.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 「我的」页 + 「编辑资料（资料详情）」页参考 tarot 项目进行视觉与交互改造：用户卡升级、功能菜单化、退出登录移入资料详情页、资料编辑改为每字段自动保存 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.1.0 | 实施：mine.vue 用户卡渐变+统计徽章+功能菜单（未登录隐藏菜单）；profile-edit.vue 居中大头像+每字段自动保存+底部退出登录；`type-check` 与 `build:mp-weixin` 通过 |
> | 2026-08-07 | v1.2.0 | 修复 Tailwind 自定义色未生成（`@config` 注入 + 独立 `app.css` 入口，对齐 tarot），全项目品牌色类恢复；全量检查构建/类型/lint 通过 |
> | 2026-08-08 | v1.3.0 | weapp-tailwindcss spacing 类生成 bug（m-/p-/gap-/w-/h- 等带 rem 单位的类全部缺失），改为 scoped SCSS 硬编码色值方案（直接从 tarot 移植样式结构），彻底绕开 weapp-tailwindcss；构建通过 |
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
4. 保持项目青柠/橄榄配色体系，沿用现有 store 与 services 逻辑，不破坏游客模式与既有鉴权。

## 三、方案设计

### 3.1 「我的」页（`mine.vue`）

按 tarot 三段式布局重构，保持青柠/橄榄体系。**已登录**与**未登录**两种状态布局如下：

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

- **用户卡**：深橄榄渐变 `linear-gradient(135deg, #242b1f, #3a4433)` + 青柠光斑（`rgba(200,218,43,0.2)` + `blur(40rpx)` 伪元素）；头像青柠描边 `box-shadow: 0 0 0 4rpx rgba(200,218,43,0.7)`；昵称加粗加大 `32rpx`。
- **统计徽章区**：登录后拉取 `getStats()`，展示「累计打球 / 累计时长 / 装备」三列玻璃卡（`rgba(255,255,255,0.1)`），失败静默降级为 0，不阻塞页面。
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

- **头像**：居中大图 `120rpx`，下方「点击更换头像」提示；小程序 `open-type="chooseAvatar"`，H5 用 `uni.chooseImage` 降级（沿用 Step 38 条件编译方案）。
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

## 五、实施步骤

1. **重构 `mine.vue`**：用户卡渐变 + 统计徽章 + 功能菜单 + 移除退出登录；`script` 增加 `getStats` 拉取（登录时）与 `goStats` / `goEditProfile` 跳转。
2. **重构 `profile-edit.vue`**：居中大头像、细分隔线表单、每字段自动保存（昵称 blur、性别/生日 change）、新增退出登录。
3. **验证**：构建编译无误，手工验收交互（登录态/游客态、自动保存、退出跳转）。

## 六、样式方案演进（重要）

### 6.1 初始方案：Tailwind 类 + weapp-tailwindcss

最初两页使用大量 Tailwind 工具类（`m-`/`p-`/`gap-`/`w-`/`h-` 等）实现布局，依赖 weapp-tailwindcss 在构建时提取并生成 WXSS。

### 6.2 问题一：自定义色类缺失

发现全项目自定义色类（`olive`/`lime`/`paper`/`ink`）从未被生成到 WXSS。

**根因**：`vite.config.ts` 的 `cssEntries` 指向 `App.vue`（Vue 组件），weapp-tailwindcss 无法正确解析 `<style lang="scss">` 内的 `@tailwind` 指令，加载不到 `tailwind.config.js` 自定义色。

**修复**（对齐 tarot）：
- 新建 `src/app.css`（独立 CSS 入口 + `@config "../tailwind.config.js"` + `@tailwind` 三指令）
- `App.vue` 改为非 scoped `@import '@/app.css'`
- `vite.config.ts` 修正 `cssEntries` 和 `tailwindcssBasedir`

### 6.3 问题二：Spacing 类全部缺失

自定义色修复后，布局仍乱。诊断发现 weapp-tailwindcss 生成器存在 bug：**所有带 rem 单位的 spacing/尺寸类（`m-`/`p-`/`gap-`/`w-`/`h-`/`min-h-`/`rounded-` 等）全部未生成到 WXSS**，仅有 `flex`/`flex-col`/`items-center` 等无单位类存活。

### 6.4 最终方案：scoped SCSS 硬编码（移植自 tarot）

用户要求"直接从 tarot 移植过来，修改风格即可"。最终方案：

- **mine.vue** 和 **profile-edit.vue** 完全采用 `<style lang="scss" scoped>` + 硬编码色值
- 样式结构直接移植自 tarot 对应页面，仅替换色值体系为青柠/橄榄：
  - 深橄榄渐变：`linear-gradient(135deg, #242b1f, #3a4433)`
  - 青柠光斑：`rgba(200, 218, 43, 0.2)` + `blur(40rpx)` 伪元素
  - 白色卡片：`#ffffff` + `border-radius: 20-28rpx`
  - 页面底色：`#f2f2ef`
  - 青柠强调：`rgba(200, 218, 43, 0.7)`（头像描边/开关颜色）
  - 退出登录红色：`#e74c3c`
- **不依赖任何 Tailwind 工具类**，彻底绕开 weapp-tailwindcss 的 spacing 类生成 bug

## 七、涉及文件

| 文件 | 改动 |
|------|------|
| `miniapp/src/pages/mine/mine.vue` | 重构：tarot 风格 scoped SCSS（硬编码色值），用户卡渐变+统计徽章+功能菜单；移除退出登录 |
| `miniapp/src/pages/profile-edit/profile-edit.vue` | 重构：tarot 风格 scoped SCSS（硬编码色值），居中大头像+每字段自动保存+底部退出登录 |
| `miniapp/src/app.css` | 新建：独立 Tailwind 入口 + `@config`（修复自定义色类，供其他页面使用） |
| `miniapp/src/App.vue` | 改为非 scoped `@import '@/app.css'` |
| `miniapp/vite.config.ts` | `cssEntries`/`tailwindcssBasedir` 修正 |
| `miniapp/tailwind.config.js` | `content` 扩展、移除无用 safelist |

复用（不改动）：`stores/auth.ts`、`stores/settings.ts`、`services/auth.ts`、`services/data.ts`（`getStats`）、`types`（`Stats`/`User`）、`utils`（`resolveUploadUrl`/`maskMiddle`/`fmtDuration`）。
