> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 50-Admin-3 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 后台管理前端仪表盘（数据概览+系统状态） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase Admin 后台管理前端总纲](./47-Admin-后台管理前端.md)

# Phase Admin-3：仪表盘

## 一、目标

实现仪表盘页面，展示数据概览卡片（用户数、日记数、装备数、打卡数）和系统状态（磁盘使用、数据库大小、运行时长）。

## 二、前置条件

- Phase Admin-2 已完成（布局与登录）
- Phase B2-3 已完成（系统监控API）

## 三、详细执行步骤

### 3.1 实现系统监控 API

**src/api/system.ts**：
```typescript
import request from './index'

export interface SystemStats {
  stats: {
    users: number
    diaries: number
    gears: number
    weights: number
    checkins: number
    analyses: number
    posts: number
  }
  database_size: string
}

export interface HealthStatus {
  status: string
  version: string
  database: string
  disk_usage: string
  uptime: string
}

export function getSystemStats(): Promise<SystemStats> {
  return request.get('/api/admin/system/stats')
}

export function getHealthStatus(): Promise<HealthStatus> {
  return request.get('/api/admin/system/health')
}
```

### 3.2 完善仪表盘页面

**src/views/dashboard/index.vue**：
```vue
<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">仪表盘</h1>
    
    <!-- 数据概览卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <StatCard
        title="用户总数"
        :value="stats.users"
        icon="UsersIcon"
        color="blue"
      />
      <StatCard
        title="日记总数"
        :value="stats.diaries"
        icon="DocumentTextIcon"
        color="green"
      />
      <StatCard
        title="装备总数"
        :value="stats.gears"
        icon="WrenchIcon"
        color="purple"
      />
      <StatCard
        title="打卡总数"
        :value="stats.checkins"
        icon="CheckCircleIcon"
        color="orange"
      />
    </div>
    
    <!-- 系统状态 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 系统信息 -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">系统信息</h2>
        <div class="space-y-3">
          <div class="flex justify-between">
            <span class="text-gray-600">系统状态</span>
            <span class="text-green-600 font-medium">{{ health.status }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">版本</span>
            <span class="text-gray-800">{{ health.version }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">数据库状态</span>
            <span :class="health.database === 'ok' ? 'text-green-600' : 'text-red-600'" class="font-medium">
              {{ health.database }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">磁盘使用</span>
            <span class="text-gray-800">{{ health.disk_usage }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">运行时长</span>
            <span class="text-gray-800">{{ health.uptime }}</span>
          </div>
        </div>
      </div>
      
      <!-- 数据库信息 -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">数据库信息</h2>
        <div class="space-y-3">
          <div class="flex justify-between">
            <span class="text-gray-600">数据库大小</span>
            <span class="text-gray-800">{{ systemStats.database_size }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">用户数</span>
            <span class="text-gray-800">{{ systemStats.stats.users }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">日记数</span>
            <span class="text-gray-800">{{ systemStats.stats.diaries }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">装备数</span>
            <span class="text-gray-800">{{ systemStats.stats.gears }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">体重记录数</span>
            <span class="text-gray-800">{{ systemStats.stats.weights }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getSystemStats, getHealthStatus } from '@/api/system'
import StatCard from '@/components/common/StatCard.vue'

const stats = reactive({
  users: 0,
  diaries: 0,
  gears: 0,
  checkins: 0
})

const health = reactive({
  status: '--',
  version: '--',
  database: '--',
  disk_usage: '--',
  uptime: '--'
})

const systemStats = reactive({
  database_size: '--',
  stats: {
    users: 0,
    diaries: 0,
    gears: 0,
    weights: 0,
    checkins: 0,
    analyses: 0,
    posts: 0
  }
})

onMounted(async () => {
  try {
    const [healthData, statsData] = await Promise.all([
      getHealthStatus(),
      getSystemStats()
    ])
    
    Object.assign(health, healthData)
    Object.assign(systemStats, statsData)
    Object.assign(stats, statsData.stats)
  } catch (e) {
    console.error('Failed to load dashboard data:', e)
  }
})
</script>
```

### 3.3 实现统计卡片组件

**src/components/common/StatCard.vue**：
```vue
<template>
  <div class="bg-white rounded-lg shadow-md p-6">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-gray-600">{{ title }}</p>
        <p class="text-2xl font-bold" :class="colorClass">{{ value }}</p>
      </div>
      <div class="p-3 rounded-full" :class="iconBgClass">
        <component :is="iconComponent" class="w-6 h-6" :class="iconClass" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  UsersIcon,
  DocumentTextIcon,
  WrenchIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps<{
  title: string
  value: number
  icon: string
  color: 'blue' | 'green' | 'purple' | 'orange'
}>()

const iconMap: Record<string, any> = {
  UsersIcon,
  DocumentTextIcon,
  WrenchIcon,
  CheckCircleIcon
}

const iconComponent = computed(() => iconMap[props.icon] || UsersIcon)

const colorMap = {
  blue: {
    text: 'text-blue-600',
    bg: 'bg-blue-100',
    icon: 'text-blue-600'
  },
  green: {
    text: 'text-green-600',
    bg: 'bg-green-100',
    icon: 'text-green-600'
  },
  purple: {
    text: 'text-purple-600',
    bg: 'bg-purple-100',
    icon: 'text-purple-600'
  },
  orange: {
    text: 'text-orange-600',
    bg: 'bg-orange-100',
    icon: 'text-orange-600'
  }
}

const colorClass = computed(() => colorMap[props.color]?.text || 'text-gray-600')
const iconBgClass = computed(() => colorMap[props.color]?.bg || 'bg-gray-100')
const iconClass = computed(() => colorMap[props.color]?.icon || 'text-gray-600')
</script>
```

## 四、验收标准

| 验收项 | 标准 |
|--------|------|
| 统计卡片 | 正确显示用户数、日记数、装备数、打卡数 |
| 系统信息 | 正确显示系统状态、版本、数据库状态、磁盘使用、运行时长 |
| 数据库信息 | 正确显示数据库大小和各表数据量 |
| 数据加载 | 页面加载时自动获取数据 |
| 错误处理 | 数据加载失败时显示默认值 |

## 五、提交规范

```bash
feat(admin): 实现仪表盘页面

- 实现系统监控API封装
- 实现统计卡片组件（StatCard）
- 实现仪表盘页面（数据概览+系统状态）
```