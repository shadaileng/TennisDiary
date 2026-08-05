> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 18-Phase1-6 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-05 |
> | 对应功能/内容 | Pinia 全局状态管理搭建 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1：uni-app 小程序前端工程初始化](./12-Phase1-uni-app小程序前端工程初始化.md) · [Phase1-5：types 类型迁移](./17-Phase1-5-types类型迁移.md) · [Phase1-7：网络层封装](./19-Phase1-7-网络层封装.md)

# Step Phase1-6：Pinia store 搭建

## 一、目标

创建全局状态 store，对应原 Web 版 React Context / 各页面本地状态管理，统一管理登录态、日记、装备、体重、设置等状态。

## 二、前置条件

- Phase1-5 完成（`types/index.ts` 类型已就绪）

## 三、技术方案

### 3.1 依赖

| 包 | 用途 |
|---|---|
| `pinia` | Vue 3 全局状态管理 |

### 3.2 Store 清单

| Store | 状态 | 职责 |
|---|---|---|
| `stores/auth.ts` | `token` / `user` | 登录态管理 + 持久化（对接 Phase1-8） |
| `stores/diary.ts` | `diaries` / `current` | 日记列表/当前项（Phase 2 填充） |
| `stores/gear.ts` | `gears` | 装备列表（Phase 2 填充） |
| `stores/weight.ts` | `weights` | 体重记录（Phase 2 填充） |
| `stores/settings.ts` | `hideAmounts` / `useLimeTheme` | 金额隐私、视觉偏好 + 持久化 |

### 3.3 关键机制

- **Options API** 写法（`state`/`getters`/`actions`），与 uni-app 编译兼容良好。
- **持久化**：`auth`/`settings` 用 `uni.setStorageSync`/`getStorageSync` 管理 token、用户、偏好；`init()` action 供 `App.vue onLaunch` 恢复。
- **网络占位**：`diary`/`gear`/`weight` 的 `fetchList` 等网络 action 暂为空实现，待 Phase1-7 网络层接入后填充。
- **`@` 别名**：`@/types` 指向 `src/types`（tsconfig paths，uni 插件自动解析）。

### 3.4 目录结构

```
miniapp/src/stores/
├── index.ts        # store 统一导出
├── auth.ts         # 登录态
├── diary.ts        # 日记
├── gear.ts         # 装备
├── weight.ts       # 体重
└── settings.ts     # 设置
```

## 四、执行步骤

1. `pnpm add pinia`。
2. 创建各 store 文件，类型引用 `@/types`（Phase1-5 迁移结果）。
3. 创建 `stores/index.ts` 统一导出。
4. `main.ts` 注册 `createPinia()`。

## 五、产出物

| 文件 | 说明 |
|---|---|
| `miniapp/src/stores/index.ts` | store 统一导出 |
| `miniapp/src/stores/auth.ts` | 登录态 store |
| `miniapp/src/stores/diary.ts` | 日记 store |
| `miniapp/src/stores/gear.ts` | 装备 store |
| `miniapp/src/stores/weight.ts` | 体重 store |
| `miniapp/src/stores/settings.ts` | 设置 store |
| `miniapp/src/main.ts` | 注册 Pinia |
| `miniapp/package.json` | 新增 pinia 依赖 |

## 六、验收标准

- [x] `pinia` 依赖已安装
- [x] 各 store 可被页面引用
- [x] `auth` store 具备 token 读写与持久化能力
- [x] `settings` store 具备偏好持久化能力
- [x] `main.ts` 已注册 Pinia
- [x] `pnpm type-check` 通过
- [x] `pnpm build:mp-weixin` 编译通过，产物含 pinia

## 七、提交拆分

1. `feat(miniapp): 搭建 Pinia store（auth/diary/gear/weight/settings）`
2. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase1-6 完成）`
