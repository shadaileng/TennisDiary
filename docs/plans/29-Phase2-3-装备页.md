> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 29 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-07 |
> | 对应功能/内容 | Phase 2-3：装备页（画报卡片流 + 新增/编辑表单 + 照片上传），对接 `/api/gears` CRUD |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.1.0 | 实施完成：choosePhoto 工具 + 装备列表页 + 表单页 |
>
> **关联文档**：[Phase 2 总纲（26）](./26-Phase2-业务页面实现总纲.md) · [Phase 2-1 数据层（27）](./27-Phase2-1-数据层与组件库.md) · [B1-7 装备接口（07）](./07-B1-7-装备接口.md)

# Step 29：Phase 2-3 装备页

## 一、目标

1. **装备列表页** `pages/gear/gear.vue`：改造占位页为「画报卡片流」（两列网格），顶部装备投入 Hero + 件数，分类/月份筛选，右下 FAB，`onShow` 拉取 `/api/gears`
2. **装备表单页** `pages/gear/form.vue`：新增/编辑共用，含分类、名称、购入日期、价格、感受、照片，提交 `POST/PUT /api/gears`，编辑可删除
3. **照片处理工具**：`uni.chooseMedia` 选图 + `uni.compressImage` 压缩 + `FileSystemManager.readFile` 转 dataURL 存入 `photo` 字段
4. **金额隐私**：投入合计按 `settings.hideAmounts` 隐藏

> **不做（依赖 Phase B2 AI）**：参考源码的「订单截图 OCR 一键识别」需 AI Key，本 Phase 不实现。

## 二、现状盘点

- ✅ 后端 `/api/gears` CRUD 已就绪（`GearCreate`/`GearUpdate`/`GearResponse`，`photo` 为字符串字段）
- ✅ `gear` store 已对接接口（`fetchList`/`create`/`update`/`remove`）
- ✅ 组件库已有 Seg/Empty/FAB 思路（FAB 为页面内样式）
- ✅ `utils` 有 `GEAR_CATEGORIES`/`todayStr`/`fmtMoney`
- ⚠️ `pages/gear/gear.vue` 是纯占位页，`pages/gear/form.vue` 不存在
- ⚠️ 缺照片压缩为 dataURL 的工具函数（小程序端用）

## 三、决策记录

| 决策点 | 结论 |
|---|---|
| 列表形态 | 两列「画报卡片流」（参考源码），照片封面 + 无照片时渐变 + 分类图标 emoji |
| 表单承载 | 子页面 `pages/gear/form.vue`，`navigateTo` 跳转，编辑 `?id=N` |
| 照片存储 | `photo` 存 dataURL（`data:image/jpeg;base64,...`），压缩控制体积（宽 ≤900，质量 0.8） |
| 照片处理 | `uni.chooseMedia` 选图 → `uni.compressImage` 压缩 → `getFileSystemManager().readFile` 转 base64 |
| 筛选 | 分类 chips（横向滚动）+ 月份 chips，仅显示已有数据 |
| OCR 识别 | 不做（依赖 AI，Phase B2） |
| 金额隐私 | 投入合计按 `settings.hideAmounts` 显示 `¥**` |

## 四、技术方案

### 4.1 照片工具函数 `utils/index.ts` 新增

```ts
/** 选择图片并压缩为 dataURL（photo 字段存储） */
async function choosePhoto(maxW = 900, quality = 0.8): Promise<string>
```

实现：`uni.chooseMedia({count:1, mediaType:['image']})` → `uni.compressImage` → `uni.getFileSystemManager().readFile({encoding:'base64'})` → 拼 `data:image/jpeg;base64,`。

### 4.2 装备列表页 `pages/gear/gear.vue`

- **Hero 卡**：装备总投入（或筛选后投入）+ 件数 + slogan "MY TENNIS CLOSET"
- **筛选 chips**：分类（全部 + 已有分类）、月份（全部 + 已有月份），横向滚动
- **画报卡片流**：两列网格 `grid grid-cols-2 gap-3`，卡片 3:4 比例，照片封面 / 无照片渐变 + 分类 emoji，底部渐变显示名称/日期/价格
- **FAB**：右下「+」→ `navigateTo('/pages/gear/form')`
- **空态**：`Empty` 组件
- **onShow**：`gearStore.fetchList()`

### 4.3 装备表单页 `pages/gear/form.vue`

- `onLoad(query)`：`id` 存在则编辑，回填；否则新建（默认分类「球拍」、日期今天）
- 字段：
  - 分类：`Seg`（GEAR_CATEGORIES）
  - 名称：输入框
  - 购入日期：`picker mode=date`
  - 金额：数字输入
  - 感受：`textarea`
  - 照片：选择封面（显示预览，可移除）
- 保存：`store.create` / `store.update`，成功后 `navigateBack`
- 删除：编辑模式底部「删除」，`uni.showModal` 确认

### 4.4 `pages.json`

新增装备表单页。

## 五、产出物

### 新建文件

| 文件 | 说明 |
|---|---|
| `miniapp/src/pages/gear/form.vue` | 装备新建/编辑表单页 |
| `docs/plans/29-Phase2-3-装备页.md` | 本方案文档 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `miniapp/src/pages/gear/gear.vue` | 占位页 → 画报卡片流列表 |
| `miniapp/src/utils/index.ts` | 新增 `choosePhoto` 工具 |
| `miniapp/src/pages.json` | 新增 form 页 |
| `docs/README.md` / `config.mts` / `AGENTS.md` | 文档同步 |

## 六、验收标准

- [x] 装备画报卡片流展示（照片/无照片渐变 + 分类 + 名称 + 日期 + 价格）
- [x] 分类/月份筛选生效，空筛选结果有提示 + 清除筛选
- [x] `onShow` 拉取列表，新增/编辑返回后自动刷新
- [x] 表单新建：`POST /api/gears` 成功并跳回列表
- [x] 表单编辑：`PUT /api/gears/{id}` 回填数据，保存后更新
- [x] 照片：选图压缩为 dataURL，预览/移除正常
- [x] 删除：`uni.showModal` 确认后 `DELETE`
- [x] 金额隐私开关生效
- [x] `pnpm type-check` 通过
- [x] `pnpm build:mp-weixin` 构建成功

## 七、提交拆分

1. `feat(miniapp): utils 新增 choosePhoto 图片压缩工具`（MINOR bump）
2. `feat(miniapp): 装备列表页（画报卡片流 + 筛选 + Hero）`（MINOR bump）
3. `feat(miniapp): 装备表单页（新增/编辑/照片/删除）`（MINOR bump）
4. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase 2-3 完成）`

## 八、执行记录

- 2026-08-07：实施完成
  - `utils/index.ts` 新增 `choosePhoto`（chooseMedia → compressImage → readFile base64 → dataURL）
  - `services/data.ts` 补充 `getGear`（单条详情，修复构建报错）
  - 重写 `pages/gear/gear.vue`：Hero 投入卡 + 分类/月份筛选 chips（scroll-view）+ 两列画报卡片流 + FAB + 空态，`onShow` 拉取 `gearStore.fetchList()`
  - 新增 `pages/gear/form.vue`：分类 Seg + 名称/日期/金额/感受 + 照片上传预览/移除，新建 `create` 编辑 `update` 删除 `remove`
  - `pages.json` 注册 gear/form 页
  - 验证：`pnpm type-check`、`pnpm build:mp-weixin` 通过；产物 `pages/gear/form` 正常生成
