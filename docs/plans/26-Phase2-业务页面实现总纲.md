> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 26 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | Phase 2 总纲：数据层（store 对接 B1 接口）+ 业务页面（日记/装备/统计/我的）+ 图表组件迁移 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase 总纲（01）](./01-tennis-diary-迁移微信小程序分析.md) · [Phase1-6 Pinia store（18）](./18-Phase1-6-PiniaStore搭建.md) · [Phase1-7 网络层（19）](./19-Phase1-7-网络层封装.md) · [Phase1-4 自定义组件（16）](./16-Phase1-4-Tailwind自定义组件.md) · [Step 25 静默登录门控（25）](./25-静默登录门控-首次启动不请求后台.md)

# Step 26：Phase 2 业务页面实现总纲

## 一、目标

将小程序端 4 个 Tab 占位页（`diary` / `gear` / `stats` / `mine`）改造为**对接 B1 后台接口的真实业务页面**，并补齐数据层与图表组件：

1. **数据层**：`diary` / `gear` / `weight` 三个 store 的 `fetchList` 等 action 从 TODO 空实现改为对接 `/api/*` 真实接口（Phase 2 定义中的「调 B1 data 接口」）
2. **组件库**：建立 `src/components/` 基础可复用组件（表单控件、列表项、弹层、空态、图表等），供各页面复用
3. **四个业务页**：日记（列表 + 新建/编辑表单）、装备（CRUD）、统计（汇总 + 体重记录 + 图表）、我的（用户信息 + 手动登录/登出入口）
4. **图表迁移**：参考源码 `Charts.tsx` 的 SVG 图表改写成小程序可用的 canvas / CSS 实现

> **Phase 2 官方定义**（方案 01 第 276 行）：
> > Phase 2 | 小程序 | 数据层（调 B1 data 接口）、日记/装备/体重/打卡页面 Vue SFC 改写 + Charts 迁移（Vant 4 组件加速 UI 搭建）| 5-7 天
>
> 说明：本项目已在 Step 16 决策放弃 Vant，改用 **Tailwind 自定义组件**（`components/` 目录当前为空，需在本 Phase 建立）。「打卡页面」因 `mine` 页内联训练营入口承载，不单独建 Tab。

## 二、现状盘点

### 2.1 数据层（store）— 待补齐

| store | 文件 | 现状 | 需对接接口 |
|---|---|---|---|
| `diary` | `stores/diary.ts` | `fetchList()` 为 TODO 空实现 | `GET/POST /api/diaries`、`GET/PUT/DELETE /api/diaries/{id}` |
| `gear` | `stores/gear.ts` | `fetchList()` 为 TODO 空实现 | `GET/POST /api/gears`、`GET/PUT/DELETE /api/gears/{id}` |
| `weight` | `stores/weight.ts` | `fetchList()` 为 TODO 空实现 | `GET/POST /api/weights`、`DELETE /api/weights/{id}` |
| `auth` | `stores/auth.ts` | 已完整（login/logout/ensureLogin） | — |
| `settings` | `stores/settings.ts` | 已完整（本地偏好） | — |

### 2.2 网络层与类型 — 已就绪

- ✅ `services/request.ts`：`get/post/put/del` 已封装 JWT 注入 + 401 处理
- ✅ `services/auth.ts`：`getLoginCode` / `login` / `getMe`
- ✅ `types/index.ts`：`Diary` / `Gear` / `WeightRecord` / `Stats` / `Checkin` 及对应 `*Create` / `*Update` 入参类型
- ⚠️ 缺 `services/` 下 data 系列 API 封装（需新增）

### 2.3 页面现状

| Tab | 页面文件 | 现状 |
|---|---|---|
| 日记 | `pages/diary/diary.vue` | 有雏形（Tab 切换 + 占位 Cell + 记录按钮，数据硬编码） |
| 装备 | `pages/gear/gear.vue` | 纯占位 |
| 统计 | `pages/stats/stats.vue` | 纯占位 |
| 我的 | `pages/mine/mine.vue` | 纯占位 |

### 2.4 组件与图表

- ⚠️ `src/components/` **为空**（需新建）
- 参考源码图表 `components/Charts.tsx`（SVG）包含：`LineChart`（折线）、`YearHeatmap`（年热力图）、`MonthHeatmap`（月热力图）、`Radar`（雷达）、`ScoreBar`（横向条）、`Bars`（柱状）
- **关键约束**：小程序 **不支持内联 `<svg>`**，需改写为 canvas 或纯 CSS。热力图/柱状/横向条可用 CSS grid/flex 实现；折线/雷达需用 canvas 实现。

## 三、决策记录

| 决策点 | 结论 |
|---|---|
| 组件库方案 | 延续 Step 16 决策：Tailwind 自定义组件（不用 Vant），建 `src/components/` |
| 图表实现方式 | 小程序不支持内联 SVG → **热力图/柱状/横向条用纯 CSS（view）实现**；**折线图/雷达图用 canvas 2D 实现**，封装为 uni-app 组件 |
| 数据层组织 | 新增 `services/data.ts` 统一封装 data 系列接口（diaries/gears/weights/checkin/stats），store action 调 service |
| 页面表单形态 | 新建/编辑采用**独立页面或弹出层**（参考源码 `DiaryForm.tsx` 为独立页）。因小程序无 modal 表单，采用**子页面**承载表单，通过 `uni.navigateTo` 跳转 |
| store 拉取时机 | 各 Tab 页 `onShow` 时调用对应 store 的 `fetchList()`（返回列表页刷新数据），避免 `onLoad` 单次加载导致返回不刷新 |
| 未登录兜底 | 页面请求 401 由 `request.ts` 统一处理登出；数据接口在未登录时返回空列表 + 引导提示（复用 Step 25 门控后的手动登录入口） |
| 体重「围度」字段 | `WeightRecord` 含 `bust/waist/hip` 可选字段，表单按需提供录入 |

## 四、技术方案

### 4.1 数据层：`services/data.ts`（新增）

统一封装 data 系列接口，供 store action 调用：

```ts
// 日记
getDiaries(): Promise<Diary[]>                          // GET /diaries
createDiary(body: DiaryCreate): Promise<Diary>          // POST /diaries
getDiary(id: number): Promise<Diary>                    // GET /diaries/{id}
updateDiary(id: number, body: DiaryUpdate): Promise<Diary> // PUT /diaries/{id}
deleteDiary(id: number): Promise<MessageResponse>       // DELETE /diaries/{id}

// 装备
getGears(): Promise<Gear[]>                             // GET /gears
createGear(body: GearCreate): Promise<Gear>             // POST /gears
updateGear(id: number, body: GearUpdate): Promise<Gear> // PUT /gears/{id}
deleteGear(id: number): Promise<MessageResponse>        // DELETE /gears/{id}

// 体重
getWeights(): Promise<WeightRecord[]>                   // GET /weights
createWeight(body: WeightCreate): Promise<WeightRecord> // POST /weights
deleteWeight(id: number): Promise<MessageResponse>      // DELETE /weights/{id}

// 打卡
getCheckins(): Promise<Checkin[]>                       // GET /checkin
createCheckin(body: CheckinCreate): Promise<Checkin>    // POST /checkin

// 统计
getStats(): Promise<Stats>                              // GET /stats
```

### 4.2 store action 补齐

三个 store 的 `fetchList` / `create` / `update` / `remove` 改为调用 `services/data.ts`，并维护 `loading` 状态：

```ts
// stores/diary.ts 示例
async fetchList() {
  this.loading = true;
  try {
    this.diaries = await getDiaries();
  } finally {
    this.loading = false;
  }
},
async create(body: DiaryCreate) {
  const d = await createDiary(body);
  this.diaries.unshift(d);   // 最新在前
  return d;
},
async remove(id: number) {
  await deleteDiary(id);
  this.diaries = this.diaries.filter(d => d.id !== id);
},
```

`gear` / `weight` store 同理。

### 4.3 组件库：`src/components/`

首批复用组件（Phase 2 页面共用地基）：

| 组件 | 说明 |
|---|---|
| `Empty.vue` | 空态占位（图标 + 文案 + 可选操作按钮） |
| `NavBar.vue` | 页面顶部标题栏（返回 / 标题 / 右侧操作） |
| `Cell.vue` / `CellGroup.vue` | 列表项 / 分组（左标题 + 右值 + 箭头） |
| `Field.vue` | 表单输入项（label + input/textarea + placeholder） |
| `Stepper.vue` | 步进器（数字增减，用于时长/强度/心情等） |
| `Tag.vue` | 标签（类型/状态展示） |
| `ActionSheet.vue` | 底部弹出选择（类型、分类等枚举选择） |
| `Popup.vue` | 通用弹层容器（覆盖层 + 内容区） |
| `ChartLine.vue` | 折线图（canvas 2D） |
| `ChartRadar.vue` | 雷达图（canvas 2D） |
| `Heatmap.vue` | 打卡热力图（CSS grid，年/月两种模式） |
| `Bars.vue` | 柱状图（CSS flex，纯 view） |
| `ScoreBar.vue` | 横向进度条（纯 CSS） |

> 图表组件从参考源码 `Charts.tsx` 迁移：逻辑（坐标计算/配色/数据映射）保持一致，渲染层由 SVG 改为 canvas 或 CSS view。

### 4.4 四个业务页面

#### (1) 日记页 `pages/diary/diary.vue`（Step 27）

- 顶部统计概览（今日训练/近 7 天次数与时长）+ 「记录训练/比赛」按钮
- 日记列表：按日期倒序，每项显示日期、类型、时长、强度/心情、花费
- 点击列表项 → 编辑；右上角「+」→ 新建
- 表单页（子页面 `pages/diary/form.vue`）：
  - 日期（`picker`）、时间、类型（训练/比赛/发球机/发球练习，ActionSheet）
  - 时长（Stepper）、强度 / 心情（Stepper 1-5）
  - 花费明细（动态增删 `name` + `amount`）、装备使用（动态增删 `name` + `feeling`）
  - 笔记（textarea）
- 删除：列表项长按或编辑页删除按钮 → 确认后 `DELETE`

#### (2) 装备页 `pages/gear/gear.vue`（Step 28）

- 装备列表按分类分组（store getter `groupedByCategory`）
- 每项：分类、名称、购买日期、价格、感受、照片缩略图
- 新增/编辑表单（子页面 `pages/gear/form.vue`）：分类（ActionSheet）、名称、购买日期（picker）、价格（输入）、感受（textarea）、照片（`uni.chooseMedia`，dataURL 上传）
- 删除：确认后 `DELETE`

#### (3) 统计页 `pages/stats/stats.vue`（Step 29）

- 汇总卡片：总次数 / 总时长 / 平均强度 / 平均心情 / 总花费 / 平均评分（对接 `/api/stats`）
- 体重管理：体重记录列表 + 新增（日期/体重/围度）+ 折线图 `ChartLine` 展示体重趋势
- 训练热力图（可选）：`Heatmap` 展示打卡分布（对接 `/api/checkin`）
- 月度柱状图：`Bars` 展示每月训练时长/次数（数据由 diary 列表聚合，或新增前端聚合函数）

#### (4) 我的页 `pages/mine/mine.vue`（Step 30）

- 用户信息卡：头像、昵称（来自 `auth.user`，未登录显示「未登录」）
- 登录/登出入口（**补齐 Step 25 遗留的手动登录入口**）：
  - 未登录 → 「登录」按钮触发 `auth.login()`（`wx.login` 全链路）
  - 已登录 → 显示用户信息 + 「退出登录」触发 `auth.logout()`
- 设置入口：金额隐私开关、主题偏好（`settings` store）
- 训练营打卡入口（可选项，对接 `/api/checkin`）

## 五、执行拆分（Step 26.1 – 26.4）

| Step | 内容 | 产出 |
|---|---|---|
| **26.1** | 数据层 + 组件库地基 | `services/data.ts` + store action 补齐 + `components/` 首批组件（Empty/NavBar/Cell/Field/Stepper/Tag/ActionSheet/Popup） |
| **26.2** | 日记页 | `pages/diary/diary.vue` 列表 + `pages/diary/form.vue` 表单，对接 `/api/diaries` |
| **26.3** | 装备页 + 统计页 | `pages/gear/*`、`pages/stats/*`，图表组件（ChartLine/ChartRadar/Heatmap/Bars/ScoreBar），对接 `/api/gears` `/api/weights` `/api/stats` `/api/checkin` |
| **26.4** | 我的页 | `pages/mine/mine.vue` 用户信息 + 手动登录/登出 + 设置入口 |

> 每个子 Step 单独建方案文档（27-30），遵守 TDD 规范与原子提交。总纲文档编号 26 作为 Phase 2 综述，各子 Step 文档编号 27-30。

## 六、验收标准

- [ ] `services/data.ts` 封装完整，类型与后端 `*Response` / `*Create` / `*Update` 对齐
- [ ] `diary` / `gear` / `weight` store 的 `fetchList` / `create` / `update` / `remove` 不再有 TODO，实际对接接口
- [ ] `components/` 首批组件可复用，无魔法样式散落（用 Tailwind 主题 token）
- [ ] 四个 Tab 页均为真实业务页面（非占位），对接对应接口
- [ ] 图表组件（折线/雷达）canvas 渲染正确，热力图/柱状/横向条 CSS 渲染正确
- [ ] 未登录状态下页面优雅降级（空列表 + 引导登录），不抛未捕获异常
- [ ] `pnpm type-check` 通过
- [ ] `pnpm build:mp-weixin` 构建成功
- [ ] `pnpm docs:build` 通过（文档侧边栏变更）
- [ ] H5 端可完整走通「登录 → 新建日记 → 列表展示 → 编辑 → 删除」闭环

## 七、提交拆分

每个子 Step 单独提交，类型规范参考各子 Step 文档。

## 八、风险与注意事项

1. **SVG → canvas/CSS 迁移**：小程序不支持内联 SVG，`Charts.tsx` 全部重写渲染层；坐标系计算逻辑可复用，需逐组件核对像素表现
2. **表单子页面导航**：小程序 `navigateTo` 传参受限，新建/编辑共用一个表单页，编辑时通过 URL 传 `id`，`onLoad` 再 `GET` 详情或从 store 取
3. **store 刷新时机**：用 `onShow` 触发 `fetchList()` 保证返回列表页时数据最新，避免陈旧数据
4. **图片上传**：装备照片用 `uni.chooseMedia` 拿临时路径，当前后端 `Gear.photo` 为 dataURL/路径字段（B1 未做独立上传接口），Phase 2 先存 dataURL，文件服务在 Phase B2 完善
5. **文档同步**：完成后更新 `docs/README.md` 执行进度 + `docs/.vitepress/config.mts` 侧边栏

## 九、执行记录

- 待执行。
