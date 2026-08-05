> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 17-Phase1-5 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-05 |
> | 对应功能/内容 | `types.ts` 类型定义迁移到小程序端 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1：uni-app 小程序前端工程初始化](./12-Phase1-uni-app小程序前端工程初始化.md) · [Tennis Diary 迁移微信小程序分析](./01-tennis-diary-迁移微信小程序分析.md) · [Phase1-7：网络层封装](./19-Phase1-7-网络层封装.md)

# Step Phase1-5：`types.ts` 类型迁移

## 一、目标

将原 Web 版 `types.ts` 的类型定义迁移到小程序端 `src/types/index.ts`，作为前端数据模型基准，字段对齐后台 B1 Pydantic Schemas。

## 二、前置条件

- Phase1-1 / Phase1-2 / Phase1-3 / Phase1-4 完成
- 后台 B1 Schemas 已稳定（`server/app/schemas/schemas.py`）

## 三、迁移策略

### 3.1 命名对齐

原 Web 版 `types.ts` 使用驼峰命名（`createdAt`/`buyDate`/`courseId`），而后台 REST 接口响应使用**蛇形命名**（`created_at`/`buy_date`/`course_id`）。小程序直接对接后台，故迁移时字段以**后台接口为准**。

| 原 Web 字段 | 迁移后字段 | 来源 |
|---|---|---|
| `Diary.createdAt` | `Diary.created_at` | 后台 `DiaryResponse` |
| `Gear.buyDate` | `Gear.buy_date` | 后台 `GearResponse` |
| `Checkin.courseId` | `Checkin.course_id` | 后台 `CheckinResponse` |
| `Analysis.createdAt` | `Analysis.created_at` | 后台 `AnalysisResponse` |
| `Post.createdAt` | `Post.created_at` | 后台 `PostResponse` |

### 3.2 实体接口 vs 创建入参

- **主实体接口**（`Diary`/`Gear`/`WeightRecord`/`Analysis`/`Checkin`/`Post`）：对应后台 `*Response`，含 `id`/`created_at`（时间戳，秒，由后端 `time.time()` 生成）。
- **创建/更新入参**（`*Create`/`*Update`）：供 Phase1-7 网络层与 Phase2 页面提交使用，对齐后台 `*Create`/`*Update`。

### 3.3 平台相关处理

- `RallyClip.video`：原 `Blob` 在小程序端不可用，改用 `File`（`uni.chooseMedia` 返回）。
- `Course`、`AISettings`、`RallyClip`：后台无对应实体，保留为前端本地类型。

### 3.4 新增类型

迁移同时补充后台交互相关类型（原 Web 端未建模）：

| 类型 | 说明 |
|---|---|
| `User` | 当前用户（`UserResponse`） |
| `Token` / `LoginRequest` | 登录（`TokenResponse`/`LoginRequest`） |
| `Stats` | 统计汇总（`StatsResponse`） |
| `MessageResponse` | 通用操作消息 |

## 四、产出物

| 文件 | 说明 |
|---|---|
| `miniapp/src/types/index.ts` | 迁移完成的类型定义 |

## 五、验收标准

- [x] 主实体字段与原 `types.ts` 语义一致（字段命名对齐 B1 后台）
- [x] 含创建/更新入参类型，供网络层与页面使用
- [x] `Course`/`AISettings`/`RallyClip` 等前端本地类型保留
- [x] `pnpm type-check` 通过
- [x] `pnpm build:mp-weixin` 编译通过

## 六、提交拆分

1. `feat(miniapp): types.ts 类型定义迁移`
2. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase1-5 完成）`
