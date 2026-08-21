> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 52-Admin-5 |
> | 文档版本 | v2.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-21 |
> | 对应功能/内容 | 后台管理前端数据管理（日记/装备/体重/分析） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.1.0 | 列表接口补充 user 对象字段 |
> | 2026-08-08 | v1.0.0 | 初版 |
> | 2026-08-21 | v2.0.0 | 根据实际代码更新 |
>
> **关联文档**：[Phase Admin 后台管理前端总纲](./47-Admin-后台管理前端.md)

# Phase Admin-5：数据管理

## 一、目标

实现日记、装备、体重、分析报告的数据管理页面，对接后端数据管理API。

## 二、前置条件

- Phase Admin-2 已完成（布局与登录）
- Phase B1 已完成（日记、装备、体重等API）

## 三、已完成内容

- 实现日记管理API和页面（列表、查看、删除），列表接口返回 user 对象（id+nickname）
- 实现装备管理API和页面（列表、查看、删除），列表接口返回 user 对象（id+nickname）
- 实现体重管理API和页面（列表、查看、删除），列表接口返回 user 对象（id+nickname）
- 实现分析报告API和页面（列表、查看、删除），列表接口返回 user 对象（id+nickname）

## 四、API接口

### 日记管理

| 函数 | 方法 | 端点 | 说明 |
|------|------|------|------|
| getDiaries | GET | /api/admin/diaries | 日记列表（分页） |
| getDiary | GET | /api/admin/diaries/:id | 日记详情 |
| deleteDiary | DELETE | /api/admin/diaries/:id | 删除日记 |

### 装备管理

| 函数 | 方法 | 端点 | 说明 |
|------|------|------|------|
| getGears | GET | /api/admin/gears | 装备列表（分页） |
| getGear | GET | /api/admin/gears/:id | 装备详情 |
| deleteGear | DELETE | /api/admin/gears/:id | 删除装备 |

### 体重管理

| 函数 | 方法 | 端点 | 说明 |
|------|------|------|------|
| getWeights | GET | /api/admin/weights | 体重列表（分页） |
| deleteWeight | DELETE | /api/admin/weights/:id | 删除体重记录 |

### 分析报告

| 函数 | 方法 | 端点 | 说明 |
|------|------|------|------|
| getAnalyses | GET | /api/admin/analyses | 分析列表（分页） |
| getAnalysis | GET | /api/admin/analyses/:id | 分析详情 |
| deleteAnalysis | DELETE | /api/admin/analyses/:id | 删除分析 |

## 五、验收标准

| 验收项 | 标准 |
|--------|------|
| 日记管理 | 列表分页、查看、删除正常 |
| 装备管理 | 列表分页、查看、删除正常 |
| 体重管理 | 列表分页、查看、删除正常 |
| 分析报告 | 列表分页、查看、删除正常 |
| 用户显示 | 列表正确显示用户昵称 |

## 六、提交规范

```bash
feat(admin): 实现数据管理页面

- 实现日记管理API和页面
- 实现装备管理API和页面
- 实现体重管理API和页面
- 实现分析报告API和页面
```
