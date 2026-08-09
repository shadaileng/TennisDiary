> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 60 |
> | 文档版本 | v1.2.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-09 |
> | 对应功能/内容 | LineChart 组件 Canvas 2D 修复 - 使用 getCurrentInstance |
> | 关联文档 | [Step 60 原始方案](./60-LineChart-Canvas-to-SVG.md) |

# Step 60（修订）：LineChart 组件 Canvas 2D 修复

## 一、问题回顾

之前尝试将 LineChart 从 Canvas 迁移到 SVG，但发现：
1. SVG 在 uni-app 小程序中路径数据（`d` 属性）无法正确传递
2. 编译后的 wxml 中 `<path>` 元素缺少 `d` 属性

因此决定改回 Canvas 2D 方案，但需要修复之前 Canvas 方案的问题。

## 二、根本原因分析

### Canvas 方案失败原因

之前使用 `uni.createSelectorQuery().in(this)` 获取 canvas 节点，但：

1. **`this` 上下文问题**：在 Vue 3 `<script setup>` 中，`this` 不是组件实例
2. **编译后代码**：`e.index.createSelectorQuery().in(this)` 中的 `this` 是 `undefined`（strict mode）
3. **vendor.js 实现**：
   ```javascript
   e.in = function(e) {
     return e.$scope ? t.call(this, e.$scope) : t.call(this, function(e) {...})(e)
   }
   ```
   当 `this` 为 `undefined` 时，`e.$scope` 访问会报错

### SVG 方案失败原因

1. **编译问题**：uni-app 编译 SVG 时，动态属性（如 `:d="pathData"`）无法正确传递到 wxml
2. **编译后 wxml**：`<path u-p="{{b}}"/>` 缺少 `d` 属性绑定

## 三、修复方案

### 方案：Canvas 2D + getCurrentInstance

使用 Vue 3 的 `getCurrentInstance()` 获取组件实例，替代错误的 `this`：

```typescript
import { getCurrentInstance, onMounted, watch } from "vue";

const instance = getCurrentInstance();

function draw() {
  // 使用 instance.proxy 作为上下文
  const query = uni.createSelectorQuery().in(instance.proxy);
  query.select("#lineChart")
    .fields({ node: true, size: true })
    .exec((res) => {
      if (!res[0]?.node) return;
      // ... 绘制逻辑
    });
}
```

### 为什么这样可以工作？

1. **`getCurrentInstance()`** 在 setup 中返回正确的组件实例
2. **`instance.proxy`** 是组件的 Vue 实例代理，包含 `$scope` 属性
3. **`createSelectorQuery().in(proxy)`** 会正确使用组件的 `$scope` 进行节点查询

## 四、实现步骤

### Step 1: 修改导入

```typescript
import { getCurrentInstance, onMounted, watch } from "vue";
```

### Step 2: 在 setup 中获取实例

```typescript
const instance = getCurrentInstance();
```

### Step 3: 修改 draw 函数

```typescript
function draw() {
  const query = uni.createSelectorQuery().in(instance.proxy);
  query.select("#lineChart")
    .fields({ node: true, size: true })
    .exec((res) => {
      if (!res[0]?.node) return;
      // ... 绘制逻辑
    });
}
```

## 五、测试验证

1. 编译通过无报错
2. 体重趋势折线图正常显示
3. 数据变化时图表自动更新
4. 无控制台错误

## 六、验收标准

- [x] 编译通过
- [x] 体重趋势图正常显示
- [x] 数据更新时图表重绘
- [x] 无控制台错误

## 七、提交记录

- Commit: `fix(miniapp): 使用 getCurrentInstance 修复 LineChart Canvas 节点查询`
- Version: `1.40.3`
