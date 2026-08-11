> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 70 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-11 |
> | 对应功能/内容 | Admin 端日记/装备/体重管理页点击行查看详情 |
> | 关联文档 | [62-Admin事件日志详情弹窗](./62-Admin事件日志详情弹窗.md)、[47-Admin-后台管理前端](./47-Admin-后台管理前端.md) |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-11 | v1.0.0 | 初版 |

# Step 70：Admin 日记/装备/体重点击查看

## 一、背景

Admin 管理端的「日记管理」「装备管理」「体重管理」三个页面（`diaries`/`gears`/`weights`）目前仅支持删除操作，管理员无法查看单条记录的完整详情。

`62-Admin事件日志详情弹窗` 已实现「点击表格行弹出详情」的交互范式（行 `cursor-pointer` + 点击弹出自定义大号弹窗），本次将同一交互范式复用到三个数据管理页。

## 二、变更内容

### 2.1 公共 Table 组件支持可选行点击

公共组件 `Table.vue` 被 7 个页面使用（diaries/gears/weights/analyses/users/roles/admins），原 `<tr>` 无点击事件。为不影响其它 4 个页面，新增**可选** prop `rowClickable`（默认 `false`），向后兼容：

- `rowClickable` 为 `true` 时：
  - `<tr>` 增加 `cursor-pointer` 样式
  - `<tr>` 绑定 `@click`，向外 emit `row-click`（携带当前行数据）
- 「操作」列 `<td>` 增加 `@click.stop`，阻止点击删除按钮时误触发行点击冒泡

### 2.2 三个页面接入行点击 + 详情弹窗

三个页面改动结构一致（数据源直接用列表行数据，与事件日志一致，列表已返回完整字段）：

- `Table` 传入 `:row-clickable="true"`，监听 `@row-click="viewXxx"`
- 新增 `selectedXxx` 响应式状态与 `viewXxx(row)` 方法
- 表格下方新增事件日志风格的**自定义弹窗**（非公共 `Modal`，因需 `max-w-2xl` 宽度与两列网格）：
  - 全屏遮罩点击关闭、右上角关闭按钮、底部「关闭」按钮三处关闭
  - 内容区 `grid grid-cols-2` 网格展示基本信息
  - 长文本（备注/使用感受）用 `whitespace-pre-wrap`
  - JSON 字符串字段（日记 costs/gears）解析后格式化展示

各页面详情字段：

| 页面 | 详情字段 |
|------|---------|
| **日记** | ID、用户、日期、时间、类型、时长（分钟）、强度、心情、消耗（costs JSON）、装备（gears JSON）、备注、创建时间 |
| **装备** | ID、用户、名称、种类、购买日期、价格（¥）、使用感受、图片、创建时间 |
| **体重** | ID、用户、日期、体重（kg）、胸围、腰围、臀围、创建时间 |

### 2.3 后端补齐体重单条查询接口

体重模块后端 `server/app/routers/admin/weights.py` 仅有列表和删除，**缺少单条查询接口**（日记 `get_diary`、装备 `get_gear` 均已存在），为保持接口完整性补齐 `GET /api/admin/weights/{weight_id}`：

- 风格与 `get_gear` 保持一致
- 记录不存在返回 404「记录不存在」
- 通过 `Depends(get_current_admin)` 鉴权
- 返回 `ApiResponse[WeightAdminResponse]`

### 2.4 前端 API 补充 `getWeight`

`admin/src/api/weights.ts` 增加 `getWeight(id)` 函数，与 `getDiary`/`getGear` 对齐。

## 三、修改文件

| 文件 | 变更 |
|------|------|
| `server/app/routers/admin/weights.py` | **新增** `GET /api/admin/weights/{weight_id}` 单条查询接口 |
| `admin/src/api/weights.ts` | **新增** `getWeight(id)` API 函数 |
| `admin/src/components/common/Table.vue` | 新增可选 `rowClickable` prop，行点击 emit `row-click`，actions 列 `@click.stop` |
| `admin/src/views/diaries/index.vue` | 接入行点击 + 自定义详情弹窗 |
| `admin/src/views/gears/index.vue` | 接入行点击 + 自定义详情弹窗 |
| `admin/src/views/weights/index.vue` | 接入行点击 + 自定义详情弹窗 |

## 四、效果

- 三个数据管理页点击表格行即可查看该条记录的完整详情
- 弹窗交互（遮罩/关闭按钮/两列网格）与事件日志页保持一致，形成统一交互范式
- 体重模块后端 API 补全，与日记/装备对齐
