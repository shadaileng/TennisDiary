> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 28 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-07 |
> | 对应功能/内容 | Phase 2-2：日记页（列表 + 新建/编辑表单），对接 `/api/diaries` CRUD |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.1.0 | 实施完成：Seg/EmojiScale 组件 + 日记列表页 + 表单页 |
>
> **关联文档**：[Phase 2 总纲（26）](./26-Phase2-业务页面实现总纲.md) · [Phase 2-1 数据层与组件库（27）](./27-Phase2-1-数据层与组件库.md) · [B1-6 日记接口（06）](./06-B1-6-日记接口.md) · [Phase1-4 自定义组件（16）](./16-Phase1-4-Tailwind自定义组件.md)

# Step 28：Phase 2-2 日记页

## 一、目标

1. **日记列表页** `pages/diary/diary.vue`：改造现有占位雏形为真实列表，按月分组展示，顶部训练时长 Hero 卡片，右下「记录」FAB，`onShow` 拉取 `/api/diaries`
2. **日记表单页** `pages/diary/form.vue`：新建/编辑共用，含训练类型、时间时长、强度、心情、花费明细、配套装备、复盘笔记，提交 `POST/PUT /api/diaries`，编辑可删除
3. **新增表单组件**：`Seg`（分段选择）、`EmojiScale`（强度/心情表情选择），补充组件库

## 二、现状盘点

- ✅ 后端 `/api/diaries` CRUD 已就绪（`DiaryCreate`/`DiaryUpdate`/`DiaryResponse`）
- ✅ `diary` store 已对接接口（`fetchList`/`create`/`update`/`remove`）
- ✅ 组件库已有 Empty/NavBar/CellGroup/Cell/Field/Stepper/Tag/ActionSheet/Popup
- ✅ `utils` 已迁移 `SESSION_TYPES`/`INTENSITY`/`MOOD`/`todayStr`/`nowTimeStr`/`fmtDuration`/`fmtMoney`/`sumCosts`/`weekdayCN`
- ⚠️ 缺 `Seg`（分段选择）、`EmojiScale`（表情滑块）表单组件
- ⚠️ `pages/diary/diary.vue` 是硬编码雏形，`pages/diary/form.vue` 不存在

## 三、决策记录

| 决策点 | 结论 |
|---|---|
| 表单承载 | 新建子页面 `pages/diary/form.vue`，`navigateTo` 跳转；编辑时 URL 传 `?id=N` |
| 列表刷新 | Tab 页 `onShow` 调 `diaryStore.fetchList()`；表单返回后列表自动刷新 |
| 新增组件 | 新增 `Seg.vue`（训练类型）、`EmojiScale.vue`（强度/心情），符合参考源码交互 |
| 花费明细 | 动态增删 `name`+`amount`，保存前过滤空项；合计用 `sumCosts` |
| 装备明细 | 动态增删 `name`+`feeling`，保存前过滤空 `name` |
| 金额隐私 | 列表/合计按 `settings.hideAmounts` 显示 `¥**` |
| 训练类型图标 | 用 emoji 映射（Target/Trophy/Zap/🎾），避免引入图标库 |
| 删除交互 | 表单页右上「删除」，`uni.showModal` 确认后 `DELETE` |

## 四、技术方案

### 4.1 新增表单组件

**`Seg.vue`**（分段选择器）— 训练类型 SESSION_TYPES：
```ts
props: { modelValue: string; options: readonly string[] }
emit: { (e: "update:modelValue", value: string): void }
```

**`EmojiScale.vue`**（表情滑块）— 强度/心情 1-5：
```ts
props: { modelValue: number; options: readonly { v: number; label: string; emoji: string }[] }
emit: { (e: "update:modelValue", value: number): void }
```

两者加入 `components/index.ts` 导出。

### 4.2 日记列表页 `pages/diary/diary.vue`

- **Hero 卡片**：深色圆角卡，展示累计时长「X / 10000 小时」进度条 + slogan
- **按月分组**：`sortedDiaries` 按 `date.slice(0,7)` 分组，组头显示次数 + 月合计花费
- **列表项 Cell**：类型图标 + 类型 + 日期/周几/时间 + 时长 + 强度/心情 emoji + 花费
- **FAB**：右下角圆形「+」→ `navigateTo('/pages/diary/form')`
- **空态**：无日记时用 `Empty` 组件 + 「记录」按钮
- **onShow**：`diaryStore.fetchList()`

### 4.3 日记表单页 `pages/diary/form.vue`

- `onLoad(query)`：`query.id` 存在则编辑模式，`getDiary(id)` 或从 store 取详情填充
- 字段：
  - 训练类型：`Seg`（SESSION_TYPES，默认「训练」）
  - 日期 `picker mode=date` + 时间 `picker mode=time`
  - 时长：输入框 + 快捷 `[60,90,120]`
  - 强度/心情：`EmojiScale`
  - 花费明细：动态增删，合计显示
  - 配套装备：动态增删
  - 复盘笔记：`textarea`
- 保存：新建 `store.create` / 编辑 `store.update`，成功后 `navigateBack`
- 删除：编辑模式右上「删除」，`uni.showModal` 确认后 `store.remove` + `navigateBack`

### 4.4 `pages.json`

新增日记表单页：
```json
{ "path": "pages/diary/form", "style": { "navigationBarTitleText": "写日记" } }
```

## 五、产出物

### 新建文件

| 文件 | 说明 |
|---|---|
| `miniapp/src/components/Seg.vue` | 分段选择器 |
| `miniapp/src/components/EmojiScale.vue` | 表情滑块（1-5） |
| `miniapp/src/pages/diary/form.vue` | 日记新建/编辑表单页 |
| `docs/plans/28-Phase2-2-日记页.md` | 本方案文档 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `miniapp/src/components/index.ts` | 导出 Seg / EmojiScale |
| `miniapp/src/pages/diary/diary.vue` | 占位雏形 → 真实列表 |
| `miniapp/src/pages.json` | 新增 form 页 |
| `docs/README.md` | 文档一览 + 执行进度补 28 |
| `docs/.vitepress/config.mts` | plans 侧边栏补 28 |
| `AGENTS.md` | Phase 2-2 状态 |

## 六、验收标准

- [x] 日记列表按月分组展示，Hero 卡显示累计时长，空态正确
- [x] `onShow` 拉取列表，新建/编辑返回后自动刷新
- [x] 表单新建：`POST /api/diaries` 成功入库并跳回列表
- [x] 表单编辑：`PUT /api/diaries/{id}` 回填数据，保存后更新列表
- [x] 删除：`uni.showModal` 确认后 `DELETE`，列表移除
- [x] 花费/装备明细动态增删，空项保存前过滤，合计正确
- [x] 金额隐私开关（`settings.hideAmounts`）生效，隐藏具体金额
- [x] `pnpm type-check` 通过
- [x] `pnpm build:mp-weixin` 构建成功
- [x] H5 端可完整走通「列表 → 新建 → 保存 → 列表展示 → 编辑 → 删除」

## 七、提交拆分

1. `feat(miniapp): 新增 Seg / EmojiScale 表单组件`（MINOR bump）
2. `feat(miniapp): 日记列表页（按月分组 + Hero 卡 + FAB + 空态）`（MINOR bump）
3. `feat(miniapp): 日记表单页（新建/编辑/删除）`（MINOR bump）
4. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase 2-2 完成）`

## 八、执行记录

- 2026-08-07：实施完成
  - 新增 `components/Seg.vue`（分段选择）、`components/EmojiScale.vue`（表情滑块），加入 `index.ts` 导出
  - 重写 `pages/diary/diary.vue`：Hero 累计时长卡 + 按月分组列表 + FAB + 空态，`onShow` 拉取 `diaryStore.fetchList()`
  - 新增 `pages/diary/form.vue`：类型/日期/时间/时长/强度/心情/花费明细/配套装备/复盘，新建 `create` 编辑 `update` 删除 `remove`（`uni.showModal` 确认）
  - `pages.json` 注册 form 页
  - 验证：`pnpm type-check`、`pnpm build:mp-weixin` 通过；产物 `pages/diary/form` 与 `components/Seg|EmojiScale` 正常生成
