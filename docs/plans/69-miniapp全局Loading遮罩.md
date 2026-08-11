> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 69 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-11 |
> | 对应功能/内容 | 小程序端全局 Loading 遮罩（对齐 Admin 端 Phase 68） |
> | 关联文档 | [68-Admin全局Loading与防重复提交](./68-Admin全局Loading与防重复提交.md) |

> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-11 | v1.0.0 | 初版 |

# Step 69：小程序端全局 Loading 遮罩

## 一、背景

Admin 端在 Phase 68 中已实现「全局 Loading 遮罩 + 请求计数器」，点击后立即获得视觉反馈。小程序端尚未接入，存在同样的体验问题：

1. **点击后界面无反馈**：列表加载、表单提交等操作期间无任何 loading 提示，用户容易误以为操作无响应或失败。
2. **与 Admin 端体验不一致**：两端同为同一产品的不同入口，交互反馈标准应保持一致。

本方案将 Admin 端 Phase 68 的「Pinia store 管理 loading + 请求计数器处理并发 + 全屏遮罩组件」模式对齐到小程序端。

> **注意**：小程序端已完成 Phase 2.6 样式方案重构（Tailwind → 自定义 SCSS），样式须使用 `tokens.scss` 注入的变量（`$color-*`、`$space-*`、`$radius-*`、`$shadow-*`），**不引入 Tailwind class**。

## 二、设计要点

### 2.1 模式对齐

| 关注点 | Admin 端（Phase 68） | 小程序端（本方案） |
|------|------|------|
| loading 状态管理 | `stores/app.ts` | `stores/app.ts`（新建） |
| 请求计数 | axios 拦截器 `pendingCount` | `request.ts` 内 `pendingCount` |
| 遮罩组件 | `components/common/Loading.vue` | `components/Loading.vue`（新建） |
| 挂载位置 | `App.vue` | `App.vue` |
| 触发方式 | 拦截器自动 | `uni.request` 前后自动 |

### 2.2 并发计数

多个请求同时进行时，最后一个请求结束才关闭 loading：

- 发起请求：`pendingCount++`，置 `loading = true`
- 请求结束（success / fail 任一终态）：`pendingCount--`，归零时置 `loading = false`

**关键：success 与 fail 两个回调的**所有**终态路径都必须归零计数器**，否则并发时计数会泄漏，导致 loading 提前/延后关闭。

### 2.3 未登录门控不触发 loading

`request.ts` 中「需要鉴权但本地无 token」的短路路径会**提前 `return Promise.reject`，并未真正发起网络请求**。此路径**不触发全局 loading**，避免游客首次进入时无意义地闪现遮罩。

### 2.4 保留原生 `uni.showLoading` 的语义差异

`mine.vue`（我的页）登录时使用原生 `uni.showLoading`（带 mask、仅覆盖登录区域按钮），其语义与全局请求 loading 不同，**保持不变**，两者互不影响。

### 2.5 无循环依赖

`request.ts` 在请求发起/结束时**按需调用** `useAppStore()`（函数内调用而非模块顶层），与 Admin 端 axios 拦截器同理，不会与 store 形成导入死循环。

## 三、修改文件

| 文件 | 变更 |
|------|------|
| `miniapp/src/stores/app.ts` | **新增**：全局 loading 状态 store |
| `miniapp/src/stores/index.ts` | 追加导出 `useAppStore` |
| `miniapp/src/components/Loading.vue` | **新增**：全屏 Loading 遮罩组件 |
| `miniapp/src/App.vue` | 挂载 `<Loading />` |
| `miniapp/src/services/request.ts` | 请求计数 + 全局 loading 开关 |

## 四、实施内容

### 4.1 新建 `stores/app.ts`

```ts
import { defineStore } from "pinia";
import { ref } from "vue";

export const useAppStore = defineStore("app", () => {
  const loading = ref(false);
  function setLoading(val: boolean) {
    loading.value = val;
  }
  return { loading, setLoading };
});
```

### 4.2 修改 `stores/index.ts`

在末尾追加：

```ts
export { useAppStore } from "./app";
```

### 4.3 新建 `components/Loading.vue`

全屏遮罩 + 旋转 spinner + 「加载中...」文案，样式全部使用 `tokens.scss` 变量：

- 遮罩背景：`rgba(242, 242, 239, 0.6)`（近似 `$color-paper` 半透明）
- 卡片：白底、`$radius-card` 圆角、`$shadow-card-md` 阴影
- spinner：`$color-lime-soft` 底 + `$color-lime-dark` 顶部
- 文案：`$font-size-sm` + `$color-olive-light`

```vue
<template>
  <view v-if="loading" class="loading-mask">
    <view class="loading-card">
      <view class="loading-spinner" />
      <text class="loading-text">加载中...</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useAppStore } from "@/stores/app";

const { loading } = storeToRefs(useAppStore());
</script>

<style scoped lang="scss">
.loading-mask {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(242, 242, 239, 0.6);
}
.loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $space-md;
  padding: $space-xl $space-3xl;
  background-color: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card-md;
}
.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid $color-lime-soft;
  border-top-color: $color-lime-dark;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.loading-text {
  font-size: $font-size-sm;
  color: $color-olive-light;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
```

### 4.4 修改 `App.vue`

`<script setup>` 中引入组件，新增 `<template>` 挂载 `<Loading />`，原有 `onLaunch/onShow/onHide/onError` 逻辑与 `@import '@/app.css'` 保持不变：

```vue
<template>
  <Loading />
</template>

<script setup lang="ts">
import { onLaunch, onShow, onHide, onError } from "@dcloudio/uni-app";
import Loading from "@/components/Loading.vue";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";
import { logFatal, flushPendingEvents } from "@/utils/eventLogger";

// ...原有 onLaunch/onShow/onHide/onError 逻辑保持不变
</script>

<style>
@import '@/app.css';
</style>
```

### 4.5 修改 `services/request.ts`

1. 顶部 `import { useAppStore } from "@/stores/app";`
2. 新增模块级计数器与开关函数：

```ts
/** 请求计数器：用于并发场景下正确关闭全局 loading */
let pendingCount = 0;

function setGlobalLoading(loading: boolean) {
  const appStore = useAppStore();
  if (loading) {
    pendingCount++;
    appStore.setLoading(true);
  } else {
    pendingCount = Math.max(0, pendingCount - 1);
    if (pendingCount === 0) {
      appStore.setLoading(false);
    }
  }
}
```

3. `request()` 内调整：
   - **未登录门控短路处不触发 loading**（保持现状，直接 reject）
   - 在 `new Promise` 内、`uni.request` 调用前：`setGlobalLoading(true)`
   - 在 `success` 回调**开头**：`setGlobalLoading(false)`
   - 在 `fail` 回调**开头**：`setGlobalLoading(false)`

## 五、风险与边界

| 场景 | 处理 |
|------|------|
| 未登录门控短路 | 不触发 loading |
| 并发请求 | 计数器归零才关闭，不会提前消失 |
| success 业务错误 / 401 | 已在 success 开头归零，计数不泄漏 |
| fail 网络错误 | 已在 fail 开头归零，计数不泄漏 |
| 与原生 uni.showLoading 冲突 | 语义不同，各自独立，不互扰 |
| 循环依赖 | 函数内按需 `useAppStore()`，无导入死循环 |

## 六、验证

1. `cd miniapp && pnpm build:mp-weixin` 构建通过
2. 小程序中触发任一网络请求，观察全屏遮罩「加载中...」出现并在请求结束后消失
3. 并发场景（如同时触发多个接口）遮罩在最后一个请求结束时才消失
4. 游客未登录进入页面，不闪现无意义的 loading 遮罩
