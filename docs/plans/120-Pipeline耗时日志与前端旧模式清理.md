> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 120 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🚧 进行中 |
> | 最后更新 | 2026-08-30 |
> | 对应功能/内容 | Pipeline 各步骤耗时日志 + 前端旧 118 模式清理 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-30 | v1.0.0 | 初版 |
>
> **关联文档**：[119：电子教练后台任务队列与管线模式](./119-电子教练后台任务队列与管线模式.md)

# Pipeline 耗时日志与前端旧模式清理

## 背景

Phase 119 实现了后端管线引擎（PipelineEngine），但管线内部各步骤**没有耗时日志**，无法准确掌握 AI 分析、姿态推理、视频处理等各阶段的实际耗时。同时前端 `analyze.vue` 仍保留旧的 118 模式代码（5 步串行调用），`useUnifiedMode` flag 已硬编码为 `true`，旧代码成为死代码。

## 目标

1. 后端 pipeline 各步骤增加耗时日志，便于性能分析
2. 前端移除旧 118 模式代码，简化分析流程
3. 保留后端旧端点（init/finalize/upload/ai/pose）供测试和其他用途

## 一、后端：Pipeline 耗时日志

### 1.1 修改文件

`server/app/services/pipeline.py`

### 1.2 具体改动

#### 1.2.1 `run_pipeline()` — 整体耗时 + 并行阶段耗时

- 顶部增加 `pipeline_start = time.time()`
- 完成时 `log.info("管线完成 total=%.2fs")`
- 并行阶段包裹 `parallel_start` / `parallel_elapsed`
- 写表阶段包裹 `write_start` / `write_elapsed`

#### 1.2.2 `_process_video()` — 视频处理耗时

- `t0 = time.time()` 包裹 `video_service.process_video()`
- 完成后 `log.info("管线-视频处理耗时: %.2fs frames=%d")`

#### 1.2.3 `_compute_ai()` — AI 评分耗时

- `t0 = time.time()` 包裹 `loop.run_until_complete()`
- 完成后 `log.info("管线-AI评分耗时: %.2fs frames=%d")`

#### 1.2.4 `_compute_pose()` — 姿态推理耗时

- `t0 = time.time()` 包裹 `pose_service.analyze_frames()`
- 完成后 `log.info("管线-姿态推理耗时: %.2fs frames=%d")`

#### 1.2.5 `_update_step_status()` — 增加 `duration_s` 字段

#### 1.2.6 `_initial_pipeline_status()` — 增加顶层计时字段

`started_at` / `completed_at` / `total_duration_s` / `parallel_duration_s`

### 1.3 预期日志输出

```
管线开始 analysis_id=46
管线-视频处理耗时: 4.72s frames=8
管线-并行计算耗时: 102.35s (ai=ok, pose=ok)
管线-AI评分耗时: 100.06s frames=8
管线-姿态推理耗时: 40.22s frames=8
管线-写表耗时: 0.85s
管线完成 analysis_id=46 total=108.12s
```

## 二、前端：移除旧 118 模式

### 2.1 modify files

| 文件 | 改动 |
|------|------|
| `miniapp/src/pages/coach/analyze.vue` | 删除 `startAnalysis()` 函数、`useUnifiedMode` flag、旧 imports |
| `miniapp/src/services/data.ts` | 删除 `createAnalysisInit`、`finalizeAnalysis`、`uploadVideo`、`analyzeSwing`、`analyzePose` |

### 2.2 analyze.vue

- 删除旧 imports（`analyzePose`, `analyzeSwing`, `createAnalysisInit`, `finalizeAnalysis`, `uploadVideo`）
- 删除 `useUnifiedMode` flag
- 删除 `startAnalysis()` 整个函数（~190 行）
- 简化 `handleStartAnalysis()` 直接调用 `startAnalysisUnified()`

### 2.3 data.ts

删除旧端点函数：`uploadVideo()`、`analyzeSwing()`、`analyzePose()`、`createAnalysisInit()`、`finalizeAnalysis()`

保留：`createAnalysis()`、`generateCaption()`、`getAnalyses()`、`getAnalysis()`、`deleteAnalysis()`

### 2.4 后端端点保留

旧端点（init/finalize/upload/ai/pose）**保留不动** — 测试文件仍引用，向后兼容。

## 三、验证

```bash
cd server && uv run ruff check . && uv run ruff format . && uv run pytest -q -m fast
cd miniapp && pnpm run type-check && pnpm run build:mp-weixin
```

## 四、执行步骤

| # | 步骤 | 依赖 |
|---|------|------|
| 1 | `pipeline.py` 添加耗时日志 + `duration_s` 字段 + 顶层计时 | 无 |
| 2 | `analyze.vue` 删除 `startAnalysis()` 和旧 imports | 无 |
| 3 | `data.ts` 删除旧端点函数 | 无 |
| 4 | 运行后端验证 | 1 |
| 5 | 运行前端验证 | 2, 3 |
| 6 | 提交 | 4, 5 |
