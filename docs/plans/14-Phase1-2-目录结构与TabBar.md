> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 12-Phase1-2 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-05 |
> | 对应功能/内容 | 目录结构、pages.json TabBar 与占位页 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1：uni-app 小程序前端工程初始化](./12-Phase1-uni-app小程序前端工程初始化.md) · [Phase1-1：uni-app 工程初始化](./13-Phase1-1-uni-app工程初始化.md)

# Step Phase1-2：目录结构与 TabBar

## 一、目标

建立小程序标准目录结构，配置 `pages.json` 底部 TabBar（日记/装备/统计/我的 四个 Tab），创建各 Tab 占位页面，为后续 Phase 页面开发铺路。

## 二、前置条件

- Phase1-1 完成（uni-app 工程可编译运行）

## 三、详细执行步骤

### 3.1 建立目录结构

在 `miniapp/src/` 下创建标准目录（含空 `components` / `stores` / `types` / `utils` / `services` / `styles`，Phase 后续填充）：

```
miniapp/src/
├── pages/                 # 页面
│   ├── diary/             # 日记（Tab）
│   ├── gear/              # 装备（Tab）
│   ├── stats/             # 统计（Tab）
│   ├── mine/              # 我的（Tab）
│   └── index/             # 原模板默认页（移除）
├── components/            # 公共组件（空）
├── stores/                # Pinia store（空，Phase1-6 填充）
├── types/                 # 类型定义（空，Phase1-5 填充）
├── utils/                 # 工具函数（空）
├── services/              # API 封装（空，Phase1-7 填充）
├── styles/                # 全局样式
├── static/                # 静态资源（TabBar 图标）
├── App.vue
├── main.ts
├── pages.json
├── manifest.json
└── uni.scss
```

### 3.2 TabBar 图标

微信小程序 TabBar 要求 png 图标（建议 81×81px），需为四个 Tab 各准备「未选中/选中」两种图标（共 8 个）存于 `static/tabbar/`。选中色使用橄榄绿/青柠主题。

| Tab | 页面 | 图标命名 |
|---|---|---|
| 日记 | `pages/diary/diary` | `diary.png` / `diary-active.png` |
| 装备 | `pages/gear/gear` | `gear.png` / `gear-active.png` |
| 统计 | `pages/stats/stats` | `stats.png` / `stats-active.png` |
| 我的 | `pages/mine/mine` | `mine.png` / `mine-active.png` |

### 3.3 配置 `pages.json`

- `globalStyle`：沿用橄榄绿/青柠主题（`navigationBarBackgroundColor` 用 olive、标题黑字）
- `pages`：四个 Tab 页 + 可选登录页
- `tabBar`：四个 Tab，`color` / `selectedColor` 对齐主题

### 3.4 创建占位页

各 Tab 页创建简单占位 `.vue`（顶部标题 + 空态提示「开发中」），统一风格。

### 3.5 移除模板默认页

删除 `pages/index/` 模板页，避免冗余。

## 四、产出物

| 文件 | 说明 |
|---|---|
| `miniapp/src/pages/diary/diary.vue` | 日记 Tab 占位页 |
| `miniapp/src/pages/gear/gear.vue` | 装备 Tab 占位页 |
| `miniapp/src/pages/stats/stats.vue` | 统计 Tab 占位页 |
| `miniapp/src/pages/mine/mine.vue` | 我的 Tab 占位页 |
| `miniapp/src/pages.json` | 页面 + TabBar 配置 |
| `miniapp/src/static/tabbar/*.png` | TabBar 图标（8 个） |
| `miniapp/src/components/` `stores/` `types/` `utils/` `services/` `styles/` | 标准目录结构 |

## 五、验收标准

- [x] 底部 TabBar 显示「日记/装备/统计/我的」四个 Tab
- [x] 各 Tab 切换正常，占位页可展示
- [x] TabBar 选中色为青柠/橄榄绿主题色
- [x] 模板默认 `pages/index` 已移除
- [x] `pnpm build:mp-weixin` 编译通过

## 六、提交拆分

1. `docs: 新增 Phase1-2 目录结构与 TabBar 方案`
2. `feat(miniapp): 目录结构与四 Tab TabBar 占位页`
3. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase1-2 完成）`
