> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 68 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-11 |
> | 对应功能/内容 | Admin 端全局 Loading 遮罩与操作防重复提交 |
> | 关联文档 | [47-Admin-后台管理前端](./47-Admin-后台管理前端.md)、[62-Admin事件日志详情弹窗](./62-Admin事件日志详情弹窗.md) |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-11 | v1.0.0 | 初版 |

# Step 68：Admin 全局 Loading 与防重复提交

## 一、背景

Admin 端存在以下体验问题：

1. **点击后界面无反馈**：`app.ts` store 中早已定义 `loading` 状态，但从未被任何页面/拦截器真正使用。所有 API 请求（增删改查）均无全局 loading，用户点击按钮后界面毫无反应，容易误以为操作失败。
2. **重复点击**：列表页的保存、重置密码、切换状态、删除等操作均未做防重复提交，快速双击会重复发起请求，造成数据重复或报错。
3. **操作成功无反馈**：部分操作成功仅刷新列表，未给 toast 提示，用户无法确认操作是否生效。

## 二、变更内容

### 2.1 全局 Loading 遮罩组件

新建 `Loading.vue` 组件，基于 `app.ts` store 中已有的 `loading` 状态渲染全屏遮罩。遮罩使用半透明白色背景 + 旋转 spinner + 「加载中...」文案，`z-index` 低于 Toast（`z-[90]` < Toast `z-[100]`），确保错误/成功提示仍可见。

### 2.2 axios 拦截器自动控制全局 Loading

改造 `api/index.ts`，使用**请求计数器**管理 loading 开关，支持并发请求场景（多个请求同时进行时，最后一个请求结束才关闭 loading）：

- request 拦截器：`pendingCount++`，设置 `loading = true`
- response 拦截器（成功 + 失败）：`pendingCount--`，归零时设置 `loading = false`

这样**所有 API 请求自动带全局 loading**，无需逐个页面改动，点击后立即获得视觉反馈。

### 2.3 App.vue 挂载 Loading 组件

在 `App.vue` 中 `Toast` 旁挂载 `<Loading />`。

### 2.4 通用操作锁 composable（防重复提交）

新建 `useActionLock` 组合式函数，封装「防重入」逻辑，供各页面提交类操作使用：

```ts
const { pending: saving, runWithLock } = useActionLock()

const saveAdmin = () => runWithLock(async () => {
  // ...原有逻辑
})
```

- 操作进行中重复调用 `runWithLock` 会被直接忽略（防连点）
- 返回 `pending` 状态，可绑定到按钮 `:disabled="pending"`

### 2.5 列表页接入操作锁

对 `admins/index.vue` 的 `saveAdmin`、`resetPwd`、`toggleStatus`、`confirmDelete` 四个操作接入 `runWithLock`，保存/重置密码等操作成功后增加 toast 成功提示，替换 `alert()`/`confirm()` 原生弹窗为更一致的 toast 反馈。

## 三、修改文件

| 文件 | 变更 |
|------|------|
| `admin/src/components/common/Loading.vue` | **新增**：全局 Loading 遮罩组件 |
| `admin/src/composables/useActionLock.ts` | **新增**：防重复提交组合式函数 |
| `admin/src/api/index.ts` | 拦截器接入全局 loading（请求计数器） |
| `admin/src/App.vue` | 挂载 `<Loading />` |
| `admin/src/views/admins/index.vue` | 提交类操作接入操作锁 + toast 成功提示 |

## 四、效果

- 所有 API 请求期间显示全屏 loading，点击后立即有反馈，杜绝「点了没反应」
- 提交类操作防重复提交，快速连点只发一次请求
- 操作成功有 toast 提示，明确反馈
