> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 37 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-07 |
> | 对应功能/内容 | 修复后端 `config.py` 中 `load_dotenv` 路径少算一级导致 `WX_APPID`/`WX_SECRET` 加载为空、微信登录报 `appid missing` 的问题 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.0.0 | 实施完成，修复落地 |
>
> **关联文档**：[核心配置模块（B1-2）](./03-B1-2-核心配置模块.md) · [对接 B1 登录流程（Phase1-8）](./20-Phase1-8-对接B1登录流程.md) · [前后端 `.env` 配置模板（21）](./21-环境变量配置模板.md)

# Step 37：修复 config 加载路径 — 微信登录 appid 缺失

## 一、背景

### 1.1 问题现象

小程序点击「一键登录」后，后台日志报错：

```
2026-08-07 14:31:56.977 | WARNING  | auth:login:27 - 微信登录失败：无效 code，原因=微信登录失败: appid missing, rid: ... (code: 41002)
```

后端 `server/.env` 中已正确填写 `WX_APPID` / `WX_SECRET`，前端 `TD_APPID` 与后端 `WX_APPID` 也一致，但微信 `code2session` 接口仍返回 `appid missing (41002)`，说明微信服务端收到的 `appid` 参数为空。

### 1.2 根因定位

后端配置加载在 `server/app/core/config.py` 顶部：

```python
# 错误写法：实际定位到 server/app/.env（该文件不存在）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
```

`config.py` 位于 `server/app/core/`，`.env` 位于 `server/`，需向上 **三级** `.parent`（`core` → `app` → `server`）。原代码只有两级 `.parent`，加载了不存在的 `server/app/.env`，导致 `os.getenv("WX_APPID", "")` 始终取默认值空字符串 `""`。

`Settings` 类在模块顶层实例化，`--reload` 只会在文件内容变化时重载，因此即使 `.env` 已填好 appid，进程内存中的 `settings.WX_APPID` 仍为空，最终微信 `code2session` 收到空的 `appid` 参数，返回 `41002`。

### 1.3 目标

修正 `load_dotenv` 的路径定位，使后端无论从哪个目录启动都能正确读取 `server/.env` 中的微信配置，登录鉴权恢复可用。

## 二、技术方案

将 `config.py` 顶部 `load_dotenv` 路径补足一级 `.parent`，并补充注释说明层级关系：

```python
# 修复后：config.py 位于 server/app/core/ 下，需向上三级到 server/
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
```

> 对比验证：`server/app/core/config.py` 的 `.parent.parent.parent` 即 `server/`，`server/.env` 存在；`.parent.parent` 是 `server/app/`，该目录下没有 `.env`。

## 三、产出物

| 文件 | 改动 |
|---|---|
| `docs/plans/37-修复config加载路径-微信登录appid缺失.md` | 本方案文档 |
| `server/app/core/config.py` | `load_dotenv` 路径由两级 `.parent` 修正为三级 `.parent` |

## 四、验收标准

- [x] 后端加载配置打印 `WX_APPID` / `WX_SECRET` 与 `.env` 填写值一致（不再为空）
- [x] 调用 `POST /api/auth/login` 传非法 code，返回错误由 `appid missing (41002)` 变为 `invalid code (40029)`，证明 appid 已正确携带
- [x] `bash scripts/verify.sh`（ruff check + ruff format + pytest）全部通过

## 五、提交拆分

1. `fix(server): 修正 config.py load_dotenv 路径，修复微信登录 appid 缺失`

## 六、执行记录

- 2026-08-07：实施完成
  - 定位根因：`config.py` 中 `load_dotenv(Path(__file__).resolve().parent.parent / ".env")` 少算一级 `.parent`，实际加载不存在的 `server/app/.env`
  - 修改 `load_dotenv` 为 `.parent.parent.parent`，正确指向 `server/.env`
  - 验证：本地加载打印 `WX_APPID='wxXXXXXXXXXXXXXX'`（脱敏）；登录接口错误从 `41002 appid missing` 变为 `40029 invalid code`；`bash scripts/verify.sh` 全部通过
