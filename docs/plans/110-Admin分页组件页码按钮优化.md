> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 110 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-26 |
> | 对应功能/内容 | Admin 公共 Pagination 组件分页按钮优化（页码 + 省略号） |
>
> **关联文档**：[Table.vue](../../admin/src/components/common/Table.vue) · [Pagination.vue](../../admin/src/components/common/Pagination.vue)

# 110：Admin 分页组件页码按钮优化

## 一、背景与目标

### 1.1 问题描述

`admin/src/components/common/Pagination.vue` 当前仅提供「上一页 / 下一页 + 1/20 文本指示」，无法快速跳转到任意页，长列表（如审计日志、日记）翻页体验差。该组件被 10 个视图复用，统一改造即可全局生效。

### 1.2 目标

将分页条升级为带页码按钮的形式：

```
上一页 | 1 | … | 4 5 6 | … | 20 | 下一页
```

规则：

- 首页 `1` 与尾页 `totalPages` 永远显示。
- 中间取以当前页为中心的**最多 3 个连续数字**。
- 与首尾不相邻时插入 `…` 分隔。
- 当前页高亮，其余可点击跳转。

## 二、详细方案

### 2.1 核心算法（computed `pages`）

```ts
const pages = computed<(number | '...')[]>(() => {
  const total = totalPages.value
  if (total <= 1) return [1]
  let start = props.currentPage - 1
  let end = props.currentPage + 1
  if (start < 2) {
    const shift = 2 - start
    start += shift
    end += shift
  }
  if (end > total - 1) {
    const shift = end - (total - 1)
    end -= shift
    start -= shift
  }
  start = Math.max(start, 2)
  end = Math.min(end, total - 1)

  const result: (number | '...')[] = [1]
  if (start > 2) result.push('...')
  for (let i = start; i <= end; i++) result.push(i)
  if (end < total - 1) result.push('...')
  if (total > 1) result.push(total)
  return result
})
```

示例（total = 20）：

| current | 渲染 |
|---------|------|
| 1 | `1 2 3 4 … 20` |
| 5 | `1 … 4 5 6 … 20` |
| 20 | `1 … 17 18 19 20` |

### 2.2 模板改造

- 保留左侧「共 X 条」。
- 用 `v-for` 渲染 `pages`：数字按钮 `@click="go(p)"`，当前页加高亮类；`…` 渲染为不可点击占位符。
- 保留 `上一页` / `下一页` 按钮及禁用态样式。

### 2.3 事件

- 新增 `go(p: number)`：`emit('update:currentPage', p)`。
- `prev` / `next` 逻辑保持不变。

### 2.4 接口兼容

组件 props（`total` / `page-size` / `v-model:current-page`）不变，所有 10 处调用无需修改。

## 三、影响范围

仅改动 `admin/src/components/common/Pagination.vue`。涉及调用：files / weights / users / event-logs / audit-logs / gears / diaries / analyses / admins 共 9 个视图（另有 users 等）。

## 四、验证

```bash
cd admin && pnpm run type-check && pnpm run build
```
