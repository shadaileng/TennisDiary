> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 27 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-07 |
> | 对应功能/内容 | Phase 2-1：数据层（`services/data.ts` + store action 对接 B1 接口）+ 组件库地基（`components/` 首批组件）+ 前端 utils 工具迁移 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.1.0 | 实施完成：数据层 + utils + 组件库落地 |
>
> **关联文档**：[Phase 2 总纲（26）](./26-Phase2-业务页面实现总纲.md) · [Phase1-6 Pinia store（18）](./18-Phase1-6-PiniaStore搭建.md) · [Phase1-7 网络层（19）](./19-Phase1-7-网络层封装.md) · [Phase1-4 自定义组件（16）](./16-Phase1-4-Tailwind自定义组件.md)

# Step 27：Phase 2-1 数据层 + 组件库地基

## 一、目标

1. **数据层**：新增 `services/data.ts`，封装日记/装备/体重/打卡/统计接口；补齐 `diary` / `gear` / `weight` 三个 store 的 `fetchList` / `create` / `update` / `remove` action，从 TODO 空实现改为对接真实接口
2. **utils 迁移**：把参考源码 `utils.ts` 中 Phase 2 需要的前端纯工具函数迁移到 `src/utils/index.ts`（枚举常量、日期/金额格式化、聚合函数）
3. **组件库地基**：建立 `src/components/` 首批可复用组件（Empty / NavBar / Cell / Field / Stepper / Tag / ActionSheet / Popup），供后续页面使用

## 二、现状盘点

- ✅ `services/request.ts`：`get/post/put/del` 已封装 JWT 注入 + 401 处理
- ✅ `types/index.ts`：全部实体与入参类型已定义（`Diary`/`Gear`/`WeightRecord`/`Stats`/`Checkin` + `*Create`/`*Update`）
- ⚠️ `services/` 仅有 `auth.ts` / `request.ts`，无 data 系列 API 封装
- ⚠️ `diary`/`gear`/`weight` store 的 `fetchList()` 均为 `// TODO` 空实现
- ⚠️ `src/components/` **为空**
- ⚠️ `src/utils/` **为空**（参考源码 `utils.ts` 的纯函数需迁移）

## 三、决策记录

| 决策点 | 结论 |
|---|---|
| 接口封装位置 | 新增 `src/services/data.ts`，独立于 `auth.ts` |
| store action 命名 | 统一 `fetchList` / `create` / `update` / `remove`，维护 `loading` 状态 |
| utils 迁移范围 | 仅迁移**纯前端通用工具**（枚举、日期、金额、聚合）；Web 专属（DOM/Blob/Canvas）留给 Phase 5/B2 |
| 组件实现 | 全部用 Tailwind 自定义组件（不用 Vant），`src/components/` 平铺 + `components/index.ts` 统一导出 |
| 组件 props 风格 | 显式 `defineProps` + `emit`，类型完整，符合 `vue-tsc` 严格检查 |

## 四、技术方案

### 4.1 `src/services/data.ts`（新增）

统一封装 data 系列接口，类型对齐 `types/index.ts`：

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

> 说明：`request.ts` 的 `get/post/put/del` 已统一拼接 `BASE_URL + API_PREFIX`，故 data 层传入相对路径（如 `/diaries`）。

### 4.2 store action 补齐

三个 store 改为调用 `services/data.ts`，并在写操作后同步内存态：

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
  this.diaries = [d, ...this.diaries];   // 最新在前
  return d;
},
async update(id: number, body: DiaryUpdate) {
  const d = await updateDiary(id, body);
  this.diaries = this.diaries.map(x => x.id === id ? d : x);
  return d;
},
async remove(id: number) {
  await deleteDiary(id);
  this.diaries = this.diaries.filter(x => x.id !== id);
},
```

`gear` / `weight` store 同理（`weight` 无 update，仅 create/remove）。

### 4.3 `src/utils/index.ts`（新增，迁移）

迁移参考源码 `utils.ts` 中的纯函数（剔除 Web 专属函数）：

| 迁移项 | 说明 |
|---|---|
| `INTENSITY` / `MOOD` | 强度/心情 1-5 的 label + emoji |
| `SESSION_TYPES` / `GEAR_CATEGORIES` / `ANALYSIS_KINDS` | 枚举常量 |
| `todayStr` / `nowTimeStr` / `pad` | 日期/时间字符串 |
| `fmtDuration` / `fmtMoney` / `weekdayCN` / `monthKey` | 格式化工具 |
| `sumCosts` | 花费合计（需 `CostItem` 类型） |
| `lastNDays` | 最近 n 天数组 |

> 依赖 `@/types` 的类型：`sumCosts(costs: CostItem[])` 用 `import type { CostItem } from "@/types"`。

### 4.4 组件库首批组件（`src/components/`）

| 组件 | 关键 props / emit | 说明 |
|---|---|---|
| `Empty.vue` | `{ icon?: string; text?: string; buttonText?: string }` / `emit("action")` | 空态占位，可带操作按钮 |
| `NavBar.vue` | `{ title: string; showBack?: boolean; rightText?: string }` / `emit("back"|"right")` | 顶部标题栏 |
| `CellGroup.vue` | `{ title?: string }` | 分组容器 |
| `Cell.vue` | `{ title: string; label?: string; value?: string; isLink?: boolean }` / `emit("click")` | 列表项 |
| `Field.vue` | `{ label: string; modelValue; type?: 'text'\|'textarea'\|'number'; placeholder?; maxlength? }` / `emit("update:modelValue")` | 表单输入项 |
| `Stepper.vue` | `{ modelValue: number; min?; max?; step? }` / `emit("update:modelValue")` | 步进器（时长/强度/心情） |
| `Tag.vue` | `{ text: string; color?: 'lime'\|'olive'\|'neutral' }` | 标签 |
| `ActionSheet.vue` | `{ show: boolean; actions: {name,value}[]; title? }` / `emit("update:show"|"select")` | 底部弹出枚举选择 |
| `Popup.vue` | `{ show: boolean }` / `emit("update:show")` | 通用弹层容器（插槽内容） |

所有组件样式用 Tailwind 主题 token（`bg-lime-dark` / `bg-paper` 等），并在 `components/index.ts` 统一导出，页面按需引入。

## 五、产出物

### 新建文件

| 文件 | 说明 |
|---|---|
| `miniapp/src/services/data.ts` | data 系列接口封装 |
| `miniapp/src/utils/index.ts` | 前端通用工具函数迁移 |
| `miniapp/src/components/Empty.vue` | 空态组件 |
| `miniapp/src/components/NavBar.vue` | 标题栏 |
| `miniapp/src/components/CellGroup.vue` | 列表分组 |
| `miniapp/src/components/Cell.vue` | 列表项 |
| `miniapp/src/components/Field.vue` | 表单输入 |
| `miniapp/src/components/Stepper.vue` | 步进器 |
| `miniapp/src/components/Tag.vue` | 标签 |
| `miniapp/src/components/ActionSheet.vue` | 底部选择 |
| `miniapp/src/components/Popup.vue` | 弹层容器 |
| `miniapp/src/components/index.ts` | 组件统一导出 |
| `docs/plans/27-Phase2-1-数据层与组件库.md` | 本方案文档 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `miniapp/src/stores/diary.ts` | `fetchList`/`create`/`update`/`remove` 对接接口 |
| `miniapp/src/stores/gear.ts` | 同上 |
| `miniapp/src/stores/weight.ts` | `fetchList`/`create`/`remove` 对接接口 |
| `docs/README.md` | 文档一览 + 执行进度补 27 |
| `docs/.vitepress/config.mts` | plans 侧边栏补 27 |

## 六、验收标准

- [x] `services/data.ts` 全部接口类型正确，与后端 `*Response`/`*Create`/`*Update` 对齐
- [x] `diary` / `gear` / `weight` store 的 action 无 TODO，`loading` 状态正确维护
- [x] store 写操作后内存态同步（新增插头/更新替换/删除过滤）
- [x] `utils/index.ts` 迁移函数与参考源码行为一致（`sumCosts`/`fmtDuration`/`lastNDays` 等）
- [x] `components/` 首批 9 个组件均可用 Tailwind 主题渲染，`vue-tsc` 无类型错误
- [x] `pnpm type-check` 通过
- [x] `pnpm build:mp-weixin` 构建成功
- [x] 未登录调用 data 接口 401 时由 `request.ts` 统一处理（不抛未捕获异常）

## 七、提交拆分

1. `feat(miniapp): 数据层 services/data.ts 封装 + 三个 store 对接真实接口`（MINOR bump）
2. `feat(miniapp): 迁移前端 utils 工具函数`（并入 1 或独立 `refactor`）
3. `feat(miniapp): 建立 components 组件库地基（9 个基础组件）`（MINOR bump）
4. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase 2-1 完成）`

## 八、执行记录

- 2026-08-07：实施完成
  - 新建 `services/data.ts`：封装 diaries / gears / weights / checkin / stats 全部接口
  - 补齐 `stores/diary.ts`、`stores/gear.ts`、`stores/weight.ts` 的 `fetchList`/`create`/`update`/`remove` action，维护 `loading` 并同步内存态
  - 新建 `utils/index.ts`：迁移枚举（INTENSITY/MOOD/SESSION_TYPES/GEAR_CATEGORIES/ANALYSIS_KINDS）与纯函数（pad/todayStr/nowTimeStr/lastNDays/weekdayCN/monthKey/fmtDuration/fmtMoney/sumCosts）
  - 新建 `components/` 首批 9 个组件（Empty/NavBar/CellGroup/Cell/Field/Stepper/Tag/ActionSheet/Popup）+ `index.ts` 统一导出
  - 文档同步：`docs/README.md`（一览 + 进度表）、`docs/.vitepress/config.mts`（侧边栏）
  - 验证：`pnpm type-check`、`pnpm build:mp-weixin`、`pnpm docs:build` 全部通过；WXSS 产物确认 Tailwind 类名正常生成
