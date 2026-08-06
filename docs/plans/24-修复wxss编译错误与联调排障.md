> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 24 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-06 |
> | 对应功能/内容 | 修复小程序 `app.wxss` 编译错误（Tailwind 冒号变体转义选择器）+ 后端 404 联调排障（端口占用与 `.env` 缺失） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-06 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1-3：Tailwind CSS 集成](./15-Phase1-3-Tailwind集成.md) · [Phase1-4：Tailwind 自定义组件](./16-Phase1-4-Tailwind自定义组件.md) · [21：前后端 `.env` 配置模板](./21-环境变量配置模板.md)

# Step 24：修复 WXSS 编译错误与联调排障

## 一、问题现象

微信开发者工具启动小程序时出现两类错误：

### 1. `app.wxss` 编译失败（阻塞全局样式）

```
[ WXSS 文件编译错误] ./app.wxss
./app.wxss(1:2544): unexpected `\` at pos 2544
```

错误指向 `app.wxss` 末尾选择器 **`.active\:opacity-90:active`**。该选择器来自 `diary.vue` 中 Tailwind 变体类 `active:opacity-90`：Tailwind 将变体冒号转义为 `\:` 输出，而 **微信 WXSS 解析器不支持选择器反斜杠转义**，导致整个全局样式文件编译失败。

### 2. 静默登录 404

```
auth.js:1 静默登录失败 ApiError: Not Found
```

排查发现：`127.0.0.1:8000` 端口被**另一个项目**（Tennis Motion System，`/openapi.json` 标题可见）占用，Tennis Diary 后端并未运行。小程序请求 `http://127.0.0.1:8000/api/auth/login` 打到错误服务器，FastAPI 返回 404。

## 二、根因分析

### 2.1 WXSS 反斜杠转义

`miniapp/src/pages/diary/diary.vue:46`：

```html
class="bg-lime-dark ... active:opacity-90"
```

Tailwind 编译产物（`app.wxss` 末尾）：

```css
.active\:opacity-90:active{opacity:.9!important}
```

全项目扫描确认 `app.wxss` 中反斜杠仅出现 1 次（唯一转义选择器），`grep active:|hover:|focus:` 仅命中 `diary.vue` 一处。因此这是唯一触发点。

### 2.2 端口占用

| 项 | 值 |
|---|---|
| 监听进程 | PID 21472（Scoop python.exe，`Tennis Motion System` FastAPI） |
| 其 `/openapi.json` | `title: "Tennis Motion System", version: "0.1.0"`，路由 `/api/auth/wechat-login`、`/api/rooms` 等 |
| 其结果 | 小程序请求 `/api/auth/login` → 404 |

### 2.3 `server/.env` 缺失

`server/` 仅有 `.env.example`，无 `.env`。`Settings` 中 `WX_APPID` / `WX_SECRET` 默认空字符串。即使端口修复，`wx_service.code_to_openid` 会用空 appid 调微信 code2session，返回 `40013 invalid appid` → 登录 401。

## 三、决策记录

| 决策点 | 结论 |
|---|---|
| `active:opacity-90` 处理 | 弃用 Tailwind 冒号变体类，改自定义类 + scoped `:active` 规则（方案 A）。微信 H5 / WXSS 均支持 `:active` 伪类，跨端一致；不采用 `separator: '_'` 全局改法（改动面大、语义不直观） |
| 交互态组件规范 | 本步骤沉淀约束：**小程序端禁用 Tailwind 冒号变体**（`active:`/`hover:`/`focus:` 等，会编译出 `\:` 转义选择器）。交互态统一用 scoped 伪类或微信 `hover-class` |
| 端口占用 | 直接结束占用进程（用户确认），Tennis Diary 后端复用 8000 端口 |
| `WX_SECRET` | 无真实密钥时先创建 `.env` 模板（填 `WX_APPID`），`WX_SECRET` 留空待用户补充；此时登录仍会 401 |

## 四、技术方案

### 4.1 `miniapp/src/pages/diary/diary.vue`

按钮 class 去掉 `active:opacity-90`，新增自定义类 `press-btn`：

```html
<view
  class="press-btn bg-lime-dark text-white text-center text-sm font-medium py-3 rounded-full"
  @tap="handleRecord"
>
```

空 `<style scoped>` 补充：

```css
<style scoped>
.press-btn:active {
  opacity: 0.9;
}
</style>
```

### 4.2 后端端口与运行环境

1. 结束占用进程：`taskkill /PID 21472 /F`
2. 启动后端：`cd server && uv run uvicorn app.main:app --reload --port 8000`
3. 验证：`/health` 返回 Tennis Diary 版本；`/openapi.json` 标题为 "Tennis Diary API"；`/api/auth/login` 不再 404

### 4.3 `server/.env`

复制 `.env.example` 为 `.env`，填入：

```env
WX_APPID=wxXXXXXXXXXXXXXX
WX_SECRET=            # 用户补充真实值后登录才可用
```

> `.env` 已被 `.gitignore` 忽略，不纳入版本管理。

## 五、产出物

| 文件 | 改动 |
|---|---|
| `docs/plans/24-修复wxss编译错误与联调排障.md` | 本方案文档 |
| `miniapp/src/pages/diary/diary.vue` | 移除 `active:opacity-90`，新增 `press-btn` + scoped `:active` |
| `server/.env` | 新建（不入库）：`WX_APPID` + `WX_SECRET` 占位 |
| `docs/README.md` | 文档一览 + 执行进度补 24 |
| `docs/.vitepress/config.mts` | plans 侧边栏补 24 |

## 六、验收标准

- [ ] `pnpm build:mp-weixin` 成功；`dist/build/mp-weixin/app.wxss` 全文无反斜杠 `\`
- [ ] 微信开发者工具重新编译，`app.wxss` 编译错误消失，页面样式正常
- [ ] `127.0.0.1:8000` 运行的是 Tennis Diary 后端（`/openapi.json` 标题验证）
- [ ] `curl /api/auth/login` 不再返回 404（未填 `WX_SECRET` 时预期为 401/422，属预期）
- [ ] `pnpm docs:build` 通过（VitePress 侧边栏变更）

## 七、提交拆分

1. `fix(miniapp): 修复 active:opacity-90 导致 app.wxss 编译失败`

## 八、执行记录

- 2026-08-06：实施完成
  - 定位并复现 `app.wxss` 编译错误：唯一触发点为 `diary.vue` 的 `active:opacity-90`，Tailwind 编译出 `.active\:opacity-90:active` 转义选择器，WXSS 解析失败
  - `diary.vue` 移除 `active:opacity-90`，新增 `press-btn` + scoped `.press-btn:active { opacity: 0.9 }`
  - 重建 `pnpm build:mp-weixin`：`app.wxss` 反斜杠数量 0，`press-btn.data-v-14e1e42a:active{opacity:.9}` 进入 `diary.wxss`
  - 定位 404 根因：端口 8000 被 Tennis Motion System（PID 21472）占用，其 `multiprocessing` worker（PID 25056）持有监听套接字，双双结束
  - 启动 Tennis Diary 后端：`/health` → `{"status":"ok","version":"1.0.0"}`，`/openapi.json` → "Tennis Diary API 1.0.0"，`/api/auth/login` 由 404 恢复为 405（GET）/ 422（POST 缺 code）
  - 创建 `server/.env`：`WX_APPID=wxXXXXXXXXXXXXXX`，`WX_SECRET` 留空待用户补充；填入真实密钥前登录预期返回 401 `appid missing`
