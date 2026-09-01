> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 124 |
> | 文档版本 | v1.2.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-09-01 |
> | 对应功能/内容 | Admin 分析报告页：修复创建时间显示 1970/1/22、修复表格排序混乱、添加筛选条件与查询按钮、表格行点击查看详情、列宽调整与隐藏日期列 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-09-01 | v1.2.0 | 新增列宽调整与隐藏日期列 |
> | 2026-09-01 | v1.1.0 | 新增表格行点击查看详情（参考事件日志） |
> | 2026-09-01 | v1.0.0 | 初版 |
>
> **关联文档**：
> - [75-4：分析报告落库与历史查询](./75-4-分析报告落库与历史查询.md)
> - [75-B2-Admin：Admin 同步 AI 网关功能](./75-B2-Admin同步AI网关功能.md)
> - [87：Admin 时间显示统一东八区](./87-Admin时间显示统一东八区.md)

# Admin 分析报告时间修复与筛选功能

## 一、问题描述

### 1.1 创建时间显示 1970/1/22

**现象**：Admin 分析报告列表页，所有记录的「创建时间」列均显示 `1970/1/22`。

**根因分析**：

| 层 | 代码位置 | 问题 |
|----|----------|------|
| 后端 | `app/models/analysis.py:24` | `created_at = Column(Float, default=0)` 存储 Unix **秒级**时间戳 |
| 前端 | `admin/src/views/analyses/index.vue:44` | 使用 `formatDate(value)` 格式化 |
| 前端 | `admin/src/utils/date.ts:16-18` | `formatDate` 期望接收 **ISO 字符串**，接收数字时按**毫秒**解析 |

**计算验证**：
- 后端返回 `created_at = 1755900000`（秒级时间戳）
- `new Date(1755900000)` 将其解释为 1755900 毫秒 ≈ 1970-01-20T20:41:40Z
- 东八区显示为 `1970/1/22`

**对比其他页面**：日记/装备/体重等页面正确使用 `formatTs(value)`，该函数先 `* 1000` 转毫秒再传给 `new Date()`。

### 1.2 表格记录排序混乱

**现象**：同一天的多条分析记录顺序不稳定，翻页时顺序可能跳变。

**根因分析**：

```python
# server/app/routers/admin/analyses.py:52
analyses = query.order_by(Analysis.date.desc()).offset(offset).limit(limit).all()
```

只按 `date` 字段（`String(10)`，如 `"2026-08-13"`）降序排列。同一天内多条记录无二级排序条件，数据库不保证顺序一致。

**对比其他路由**：diaries/weights/gears 均使用 `created_at.desc()` 排序，天然保证创建越新的越靠前。

### 1.3 缺少筛选功能

**现象**：分析报告列表无筛选条件，只能翻页浏览，无法按用户/日期/类型/模式/状态快速定位。

**现状**：后端仅支持 `user_id` 筛选参数，前端无筛选 UI。

### 1.4 表格行点击方式不一致

**现象**：分析报告需要点击"查看"按钮才能打开详情，与其他页面（事件日志、日记、装备、体重）点击行直接打开详情的交互不一致。

**对比**：

| 页面 | 交互方式 |
|------|----------|
| 事件日志 | 整行可点击，直接打开详情 |
| 日记/装备/体重 | 整行可点击，直接打开详情 |
| 分析报告（当前） | 需点击"查看"按钮 |

---

## 二、修复方案

### 2.1 修复创建时间显示

**修改文件**：`admin/src/views/analyses/index.vue`

| 行号 | 修改前 | 修改后 |
|------|--------|--------|
| 205 | `import { formatDate } from '@/utils/date'` | `import { formatTs } from '@/utils/date'` |
| 44 | `{{ formatDate(value) }}` | `{{ formatTs(value) }}` |

**涉及函数**：`formatTs`（`admin/src/utils/date.ts:4-7`）
```ts
export function formatTs(ts: number | null | undefined): string {
  if (!ts) return '--'
  return new Date(ts * 1000).toLocaleString('zh-CN', { timeZone: TZ })
}
```

### 2.2 修复表格排序

**修改文件**：`server/app/routers/admin/analyses.py`

| 行号 | 修改前 | 修改后 |
|------|--------|--------|
| 52 | `order_by(Analysis.date.desc())` | `order_by(Analysis.date.desc(), Analysis.id.desc())` |

添加 `Analysis.id.desc()` 作为二级排序，同日期内按 ID 降序（创建越新越靠前），保证排序稳定。

### 2.3 添加筛选功能

#### 2.3.1 后端：扩展筛选参数

**修改文件**：`server/app/routers/admin/analyses.py`

新增查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `date_from` | `str \| None` | 开始日期（含），格式 `YYYY-MM-DD` |
| `date_to` | `str \| None` | 结束日期（含），格式 `YYYY-MM-DD` |
| `kind` | `str \| None` | 类型（综合/正手/反手/截击/发球/高压） |
| `mode` | `str \| None` | 模式（single/full） |
| `status` | `str \| None` | 状态（processing/completed/failed） |

筛选逻辑：
```python
if date_from:
    query = query.filter(Analysis.date >= date_from)
if date_to:
    query = query.filter(Analysis.date <= date_to)
if kind:
    query = query.filter(Analysis.kind == kind)
if mode:
    query = query.filter(Analysis.mode == mode)
if status:
    query = query.filter(Analysis.status == status)
```

#### 2.3.2 前端：扩展 API 参数

**修改文件**：`admin/src/api/analyses.ts`

更新 `getAnalyses` 函数参数类型：
```ts
export function getAnalyses(params: {
  offset?: number
  limit?: number
  user_id?: number
  date_from?: string
  date_to?: string
  kind?: string
  mode?: string
  status?: string
}): Promise<AnalysisListResponse>
```

#### 2.3.3 前端：添加筛选 UI

**修改文件**：`admin/src/views/analyses/index.vue`

在标题下方、表格上方添加筛选区域：

```html
<div class="bg-gray-50 rounded-lg p-4 mb-6">
  <div class="flex flex-wrap gap-4 items-end">
    <!-- 开始日期 -->
    <div>
      <label class="block text-sm text-gray-600 mb-1">开始日期</label>
      <input
        type="date"
        v-model="filterForm.date_from"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-olive-500 focus:border-olive-500"
      />
    </div>
    <!-- 结束日期 -->
    <div>
      <label class="block text-sm text-gray-600 mb-1">结束日期</label>
      <input
        type="date"
        v-model="filterForm.date_to"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-olive-500 focus:border-olive-500"
      />
    </div>
    <!-- 类型 -->
    <div>
      <label class="block text-sm text-gray-600 mb-1">类型</label>
      <select
        v-model="filterForm.kind"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-olive-500 focus:border-olive-500"
      >
        <option value="">全部</option>
        <option>综合</option>
        <option>正手</option>
        <option>反手</option>
        <option>截击</option>
        <option>发球</option>
        <option>高压</option>
      </select>
    </div>
    <!-- 模式 -->
    <div>
      <label class="block text-sm text-gray-600 mb-1">模式</label>
      <select
        v-model="filterForm.mode"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-olive-500 focus:border-olive-500"
      >
        <option value="">全部</option>
        <option value="single">单次挥拍</option>
        <option value="full">综合分析</option>
      </select>
    </div>
    <!-- 状态 -->
    <div>
      <label class="block text-sm text-gray-600 mb-1">状态</label>
      <select
        v-model="filterForm.status"
        class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-olive-500 focus:border-olive-500"
      >
        <option value="">全部</option>
        <option value="processing">处理中</option>
        <option value="completed">已完成</option>
        <option value="failed">失败</option>
      </select>
    </div>
    <!-- 按钮组 -->
    <div class="flex gap-2">
      <button
        @click="handleSearch"
        class="bg-olive-600 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-olive-700 transition-colors"
      >
        查询
      </button>
      <button
        @click="handleReset"
        class="bg-gray-200 text-gray-700 px-4 py-1.5 rounded-lg text-sm hover:bg-gray-300 transition-colors"
      >
        重置
      </button>
    </div>
  </div>
</div>
```

#### 2.3.4 前端：添加筛选逻辑

**修改文件**：`admin/src/views/analyses/index.vue`

添加响应式状态和方法：

```ts
// 筛选表单
const filterForm = ref({
  date_from: '',
  date_to: '',
  kind: '',
  mode: '',
  status: '',
})

// 查询（重置分页到第 1 页）
const handleSearch = () => {
  currentPage.value = 1
  fetchAnalyses()
}

// 重置筛选条件
const handleReset = () => {
  filterForm.value = {
    date_from: '',
    date_to: '',
    kind: '',
    mode: '',
    status: '',
  }
  currentPage.value = 1
  fetchAnalyses()
}
```

更新 `fetchAnalyses` 函数，传入筛选参数：

```ts
const fetchAnalyses = async () => {
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const res = await getAnalyses({
      offset,
      limit: pageSize.value,
      ...filterForm.value,  // 传入筛选条件
    })
    analyses.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch analyses:', e)
  }
}
```

### 2.4 表格行点击查看详情

**修改文件**：`admin/src/views/analyses/index.vue`

**背景**：Table 组件已支持行点击（`rowClickable` prop + `row-click` emit），actions 单元格有 `@click.stop` 阻止冒泡。

**修改 1**：Table 组件添加行点击支持

```html
<!-- 修改前 -->
<Table :columns="columns" :data="analyses">

<!-- 修改后 -->
<Table :columns="columns" :data="analyses" :row-clickable="true" @row-click="viewAnalysis">
```

**修改 2**：移除 actions 插槽中的"查看"按钮

```html
<!-- 修改前 -->
<template #actions="{ row }">
  <button @click="viewAnalysis(row)" class="text-olive-600 hover:text-olive-800 mr-3">
    查看
  </button>
  <button @click="confirmDelete(row)" class="text-red-600 hover:text-red-800">
    删除
  </button>
</template>

<!-- 修改后 -->
<template #actions="{ row }">
  <button @click="confirmDelete(row)" class="text-red-600 hover:text-red-800">
    删除
  </button>
</template>
```

### 2.5 列宽调整与隐藏日期列

**修改文件**：`admin/src/views/analyses/index.vue`

**背景**：`date`（训练日期）和 `created_at`（创建时间）语义相近，管理员主要关心记录何时创建，训练日期可在详情弹窗查看。参考 files 页面的列宽定义方式。

**修改 1**：隐藏 `date` 列，调整列定义

```ts
// 修改前
const columns = [
  { key: 'id', title: 'ID' },
  { key: 'user', title: '用户' },
  { key: 'date', title: '日期' },
  { key: 'kind', title: '类型' },
  { key: 'mode', title: '模式' },
  { key: 'thumb', title: '封面' },
  { key: 'score', title: '评分' },
  { key: 'created_at', title: '创建时间' }
]

// 修改后
const columns = [
  { key: 'id', title: 'ID', width: 50 },
  { key: 'user', title: '用户' },
  { key: 'kind', title: '类型', width: 70 },
  { key: 'mode', title: '模式', width: 90 },
  { key: 'thumb', title: '封面', width: 70 },
  { key: 'score', title: '评分', width: 60 },
  { key: 'created_at', title: '创建时间', width: 170 }
]
```

**修改 2**：移除 `#cell-date` 插槽（如有）

**列宽说明**：

| 列 | width | 说明 |
|----|-------|------|
| ID | 50 | 数字，固定窄宽 |
| 用户 | 无 | 自适应昵称长度 |
| 类型 | 70 | 中文短文本（综合/正手等） |
| 模式 | 90 | 徽章（单次挥拍/综合分析） |
| 封面 | 70 | 图片缩略图 h-10 w-16 |
| 评分 | 60 | 数字 |
| 创建时间 | 170 | 完整日期时间（如 `2026/8/13 14:30:25`） |

---

## 三、TDD 测试计划

### 3.1 后端测试

**测试文件**：`server/tests/routers/admin/test_analyses.py`

#### 测试用例 1：筛选参数验证

```python
def test_list_analyses_with_date_filter(client, admin_token, sample_analyses):
    """日期范围筛选"""
    resp = client.get(
        "/api/admin/analyses?date_from=2026-08-10&date_to=2026-08-15",
        headers={"X-Auth-Token": admin_token},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    for item in data:
        assert "2026-08-10" <= item["date"] <= "2026-08-15"
```

#### 测试用例 2：类型筛选

```python
def test_list_analyses_with_kind_filter(client, admin_token, sample_analyses):
    """类型筛选"""
    resp = client.get(
        "/api/admin/analyses?kind=正手",
        headers={"X-Auth-Token": admin_token},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    for item in data:
        assert item["kind"] == "正手"
```

#### 测试用例 3：模式筛选

```python
def test_list_analyses_with_mode_filter(client, admin_token, sample_analyses):
    """模式筛选"""
    resp = client.get(
        "/api/admin/analyses?mode=single",
        headers={"X-Auth-Token": admin_token},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    for item in data:
        assert item["mode"] == "single"
```

#### 测试用例 4：状态筛选

```python
def test_list_analyses_with_status_filter(client, admin_token, sample_analyses):
    """状态筛选"""
    resp = client.get(
        "/api/admin/analyses?status=completed",
        headers={"X-Auth-Token": admin_token},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    for item in data:
        assert item["status"] == "completed"
```

#### 测试用例 5：组合筛选

```python
def test_list_analyses_with_combined_filters(client, admin_token, sample_analyses):
    """组合筛选：日期 + 类型 + 模式"""
    resp = client.get(
        "/api/admin/analyses?date_from=2026-08-01&date_to=2026-08-31&kind=综合&mode=full",
        headers={"X-Auth-Token": admin_token},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    for item in data:
        assert "2026-08-01" <= item["date"] <= "2026-08-31"
        assert item["kind"] == "综合"
        assert item["mode"] == "full"
```

#### 测试用例 6：排序验证

```python
def test_list_analyses_order_by_date_and_id(client, admin_token, sample_analyses):
    """排序验证：先按 date 降序，再按 id 降序"""
    resp = client.get(
        "/api/admin/analyses",
        headers={"X-Auth-Token": admin_token},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    for i in range(len(items) - 1):
        curr = items[i]
        next_item = items[i + 1]
        # 日期降序，或同日期内 ID 降序
        assert (curr["date"] > next_item["date"]) or (
            curr["date"] == next_item["date"] and curr["id"] >= next_item["id"]
        )
```

### 3.2 前端测试（手动验证）

| 验证项 | 预期结果 |
|--------|----------|
| 创建时间列显示 | 显示完整日期时间（如 `2026/8/13 14:30:25`），不再显示 1970/1/22 |
| 排序稳定性 | 同一天多条记录顺序稳定，翻页时不跳变 |
| 日期范围筛选 | 选择开始/结束日期后点击查询，列表仅显示范围内记录 |
| 类型筛选 | 选择「正手」后点击查询，列表仅显示 kind=正手 的记录 |
| 模式筛选 | 选择「单次挥拍」后点击查询，列表仅显示 mode=single 的记录 |
| 状态筛选 | 选择「已完成」后点击查询，列表仅显示 status=completed 的记录 |
| 组合筛选 | 同时选择多个条件，列表显示满足所有条件的记录 |
| 重置功能 | 点击重置按钮，所有筛选条件清空，列表恢复显示全部记录 |
| 分页联动 | 查询/重置后自动回到第 1 页 |
| 行点击查看详情 | 点击表格行直接打开详情弹窗，无需点击"查看"按钮 |
| 删除按钮正常 | 点击删除按钮不会误触发行点击事件 |

---

## 四、执行步骤

### Step 1：RED — 编写测试

1. 在 `server/tests/routers/admin/test_analyses.py` 中添加 6 个测试用例
2. 运行测试确认全部失败（RED）

### Step 2：GREEN — 实现后端筛选

1. 修改 `server/app/routers/admin/analyses.py`：
   - 添加 `date_from`、`date_to`、`kind`、`mode`、`status` 参数
   - 添加对应的 `.filter()` 条件
   - 修改排序为 `order_by(Analysis.date.desc(), Analysis.id.desc())`
2. 运行测试确认通过（GREEN）

### Step 3：GREEN — 修复前端时间显示

1. 修改 `admin/src/views/analyses/index.vue`：
   - import `formatTs` 替代 `formatDate`
   - 模板中 `formatDate(value)` 改为 `formatTs(value)`

### Step 4：GREEN — 添加前端筛选功能

1. 修改 `admin/src/api/analyses.ts`：扩展参数类型
2. 修改 `admin/src/views/analyses/index.vue`：
   - 添加筛选表单 UI
   - 添加 `filterForm`、`handleSearch`、`handleReset`
   - 更新 `fetchAnalyses` 传入筛选参数

### Step 5：GREEN — 表格行点击查看详情

1. 修改 `admin/src/views/analyses/index.vue`：
   - Table 组件添加 `:row-clickable="true"` 和 `@row-click="viewAnalysis"`
   - 移除 `#actions` 插槽中的"查看"按钮（保留"删除"按钮）

### Step 6：GREEN — 列宽调整与隐藏日期列

1. 修改 `admin/src/views/analyses/index.vue`：
   - 移除 `date` 列定义
   - 为各列添加 `width` 属性

### Step 7：REFACTOR — 验证与清理

1. 运行后端验证：`cd server && uv run ruff check . && uv run ruff format . && uv run pytest -q -m fast`
2. 运行前端验证：`cd admin && pnpm run type-check && pnpm run build`
3. 确认无 lint 错误、无类型错误、构建通过

---

## 五、验收标准

- [ ] 创建时间列正确显示完整日期时间（东八区）
- [ ] 表格排序稳定（date + id 二级排序）
- [ ] 筛选区域 UI 完整（日期范围/类型/模式/状态）
- [ ] 查询按钮功能正常
- [ ] 重置按钮功能正常
- [ ] 分页联动正常（查询/重置后回到第 1 页）
- [ ] 点击表格行直接打开详情弹窗
- [ ] 删除按钮点击不误触发行点击事件
- [ ] 日期列已隐藏，只显示创建时间列
- [ ] 列宽合理，表格布局整齐
- [ ] 后端 6 个测试用例全部通过
- [ ] 前端 type-check 通过
- [ ] 前端 build 通过
