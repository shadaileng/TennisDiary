> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 01 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🚧 进行中 |
> | 最后更新 | 2026-08-04 |
> | 对应功能/内容 | VitePress + CloudStudio 部署踩坑记录 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-04 | v1.0.0 | 初版 |
>
> **关联文档**：[Tennis Diary 迁移微信小程序分析](../plans/01-tennis-diary-迁移微信小程序分析.md)

# VitePress 踩坑记录

记录在 CloudStudio 环境中部署 VitePress 文档站点遇到的各种问题和解决方案。

---

## 坑 1：`&` 后台运行导致进程挂起

### 现象

```bash
npx vitepress dev docs --host 0.0.0.0 --port 5173 &
```

进程状态显示 `TNl`（Stopped/Suspended），端口在监听但请求无响应，curl 会卡住。

### 原因

Shell 的 `&` 后台进程在终端断开或收到 `SIGTSTP` 信号后会被挂起。VitePress 作为 watch 模式的开发服务器，需要持续运行，不适合简单的 `&` 后台化。

### 解决

```bash
nohup npx vitepress dev docs --host 0.0.0.0 --port 5173 > /tmp/vitepress.log 2>&1 & disown
```

使用 `nohup` + `disown` 确保进程脱离终端控制。但更推荐直接在前台终端运行 `pnpm docs:dev`，便于查看日志和排查问题。

### 教训

不要在终端中使用 `&` 直接后台运行 VitePress。要么前台运行，要么用 `nohup ... & disown`。

---

## 坑 2：多个 vitepress 进程抢占同一端口

### 现象

`ss -tlnp | grep 5173` 显示多个 node 进程同时监听 5173 端口，请求随机卡住或响应异常。

### 原因

多次启动 vitepress 而没有先杀掉旧进程，导致端口被多个进程争抢。

### 解决

每次重启前先彻底清理：

```bash
pkill -9 -f vitepress 2>/dev/null
sleep 1
# 然后再启动
```

验证只有一个进程：

```bash
ss -tlnp | grep 5173
# 应该只有一行 LISTEN
```

---

## 坑 3：CloudStudio 代理域名被 Vite 阻止

### 现象

```
Blocked request. This host ("xxx.cloudstudio.club") is not allowed.
To allow this host, add "xxx.cloudstudio.club" to `server.allowedHosts` in vite.config.js.
```

### 原因

Vite 默认只允许 `localhost` 访问。通过 CloudStudio 代理访问时，请求的 Host 头是代理域名，被 Vite 安全策略拦截。

### 解决

在 VitePress 配置中添加：

```ts
// docs/.vitepress/config.mts
export default defineConfig({
  vite: {
    server: {
      allowedHosts: ['.cloudstudio.club'],  // 通配所有 CloudStudio 子域名
    },
  },
})
```

### 注意

`allowedHosts` 必须是字符串数组，VitePress 中需要包在 `vite.server` 下，因为 VitePress 的 `server` 配置项不直接支持此属性。

---

## 坑 4：开发模式下 `@fs/` 和 `@vite/` 路径 404（已证伪）

> ⚠️ **2026-08-05 修正**：本坑的根因实际上是**坑3（403 `Blocked request`）没配到位**。`@fs/`、`@vite/client` 404 是 403 被拦截后浏览器拿不到这些虚拟模块导致的连锁假象，不是 dev 模式本身在代理下不可用。配置正确后 dev 模式可正常工作。

### 现象（当时看到的）

开发模式（`vitepress dev`）下通过 CloudStudio 代理访问，所有 `@fs/` 和 `@vite/client` 的请求返回 404：

```
GET /@vite/client net::ERR_ABORTED 404
GET /@fs/workspace/node_modules/... net::ERR_ABORTED 404
```

### 根因

**不是 dev 模式不兼容代理，而是坑3（403 `Blocked request`）没配好。** Vite 6 默认只允许 `localhost`，CloudStudio 代理域名的请求被 403 拦截后，浏览器后续加载 `@vite/client`、`@fs/` 等虚拟模块时拿不到响应，表现为 404。

### 正确解法

配好 `host: true` + `allowedHosts: true`（或具体域名），403 消除后 dev 模式即可正常工作：

```ts
// docs/.vitepress/config.mts
export default defineConfig({
  vite: {
    server: {
      host: true,
      allowedHosts: true,  // 或 ['.cloudstudio.club']
    },
  },
})
```

```bash
# 直接前台运行，支持热更新
pnpm docs:dev
```

### 备选方案（仅当 dev 模式确实不可用时）

如果代理层对 WebSocket/HMR 有特殊限制导致 dev 模式仍然异常，可退回 build + preview：

```bash
npx vitepress build docs
npx vitepress preview docs --host 0.0.0.0 --port 5173
```

**注意**：build + preview 是纯静态文件，无热更新，每次变更需要重新构建。**不是首选方案。**

---

## 坑 5：CloudStudio 代理缓存旧响应

### 现象

重新 build 并重启 preview 后，通过代理访问仍然看到旧页面内容。

### 原因

CloudStudio 代理层有缓存机制，可能缓存了之前的响应。

### 解决

1. **URL 加时间戳参数**：`/?_t=1733722800` 绕过缓存
2. **浏览器硬刷新**：`Ctrl+Shift+R`
3. **换一个端口**：如果缓存问题持续，换一个端口（如 4173）启动

---

## 坑 6：VitePress 构建报死链错误

### 现象

```bash
[vitepress] 1 dead link(s) found.
build error:
```

### 原因

文档中的 Markdown 链接指向了不存在的文件或不在 VitePress 扫描范围内的路径。

### 解决

- 确保链接目标文件存在且在 `srcExclude` 白名单内
- 对于指向参考代码等不在 VitePress 范围内的路径，改为纯文本描述而非链接
- 或者在配置中关闭死链检查：

```ts
export default defineConfig({
  ignoreDeadLinks: true,
})
```

---

## 坑 7：中文文件名导致 URL 编码问题

### 现象

文件名为 `01-tennis-diary-迁移微信小程序分析.md`，访问时 URL 中的中文被编码为 `%E8%BF%81...`，部分代理或浏览器处理异常。

### 解决

VitePress 构建时会自动处理中文文件名的 URL 编码，访问时直接用编码后的 URL 即可。如果需要 clean URL（不带 `.html`），配置：

```ts
export default defineConfig({
  cleanUrls: true,
})
```

---

## 坑 8：Sidebar 和 Nav 配置不符合官方规范

### 现象

把所有链接都塞进 Nav 下拉菜单 + 全局数组 Sidebar，导致首页也有侧边栏，结构混乱。

### 正确做法

遵循 VitePress 官方规范：

**Nav** 用于顶层板块导航，直接链接到页面：

```ts
nav: [
  { text: '首页', link: '/' },
  { text: '方案', link: '/plans/01-xxx' },
]
```

**Sidebar** 用对象形式按路径前缀匹配，实现不同板块显示不同侧边栏：

```ts
sidebar: {
  '/plans/': [
    {
      text: '方案',
      items: [
        { text: '文档标题', link: '/plans/01-xxx' },
      ],
    },
  ],
  '/guides/': [
    {
      text: '指南',
      items: [
        { text: '文档标题', link: '/guides/01-xxx' },
      ],
    },
  ],
}
```

首页使用 `layout: home`（Hero 布局）时不显示侧边栏，进入具体文档页时自动匹配对应侧边栏。

---

## 总结

| 坑 | 一句话 | 关键动作 |
|---|---|---|
| 后台进程挂起 | `&` 不适合 VitePress | 前台运行或用 `nohup` |
| 多进程抢端口 | 旧进程没杀干净 | 先 `pkill` 再启动 |
| Host 被拦截 | Vite 默认只认 localhost | 配 `allowedHosts` |
| @fs 路径 404 | 根因是 403 没配好，dev 本身可用 | 配 `host:true` + `allowedHosts:true` |
| 代理缓存 | CloudStudio 缓存旧内容 | 加时间戳参数 |
| 死链报错 | 链接指向不存在文件 | 修复链接或 `ignoreDeadLinks` |
| 中文编码 | URL 含百分号编码 | VitePress 自动处理 |
| Nav/Sidebar 乱配 | 没按官方规范 | Nav 直链 + Sidebar 路径匹配 |

---

> **经验法则**：在 CloudStudio 这类代理环境下，**先配好 `host: true` + `allowedHosts: true`，然后直接用 `vitepress dev`（支持热更新）**。仅当代理层对 WebSocket 有特殊限制导致 HMR 异常时，才退回 `vitepress build + vitepress preview`。每次启动前通过 `pkill -9 -f vitepress` 清理旧进程，用 `ss -tlnp | grep 5173` 确认只有一个进程在监听。
