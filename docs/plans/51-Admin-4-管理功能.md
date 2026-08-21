> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 51-Admin-4 |
> | 文档版本 | v2.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-21 |
> | 对应功能/内容 | 后台管理前端管理功能（用户/角色/管理员管理） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
> | 2026-08-21 | v2.0.0 | 根据实际代码更新：功能模块完善 |
>
> **关联文档**：[Phase Admin 后台管理前端总纲](./47-Admin-后台管理前端.md)

# Phase Admin-4：管理功能

## 一、目标

实现用户管理、角色管理、管理员管理页面，对接后端管理API。

## 二、前置条件

- Phase Admin-2 已完成（布局与登录）
- Phase B2-1 已完成（管理员、角色、用户管理API）

## 三、详细执行步骤

### 3.1 实现通用组件

#### Table 组件
**src/components/common/Table.vue**：
```vue
<template>
  <div class="bg-white rounded-lg shadow-md overflow-hidden">
    <table class="min-w-full divide-y divide-gray-200">
      <thead class="bg-gray-50">
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
          >
            {{ column.title }}
          </th>
          <th v-if="$slots.actions" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
            操作
          </th>
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-200">
        <tr
          v-for="(row, index) in data"
          :key="index"
          class="hover:bg-gray-50"
          :class="{ 'cursor-pointer': rowClickable }"
          @click="rowClickable && emit('row-click', row)"
        >
          <td
            v-for="column in columns"
            :key="column.key"
            class="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
          >
            <slot :name="'cell-' + column.key" :row="row" :value="row[column.key]">
              {{ row[column.key] }}
            </slot>
          </td>
          <td v-if="$slots.actions" class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium" @click.stop>
            <slot name="actions" :row="row" />
          </td>
        </tr>
        <tr v-if="data.length === 0">
          <td :colspan="columns.length + ($slots.actions ? 1 : 0)" class="px-6 py-12 text-center text-gray-500">
            暂无数据
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
```

#### Modal 组件
**src/components/common/Modal.vue**：
```vue
<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="visible"
        class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
        @click.self="emit('close')"
      >
        <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
          <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-800">{{ title }}</h3>
            <button @click="emit('close')" class="text-gray-400 hover:text-gray-600">&times;</button>
          </div>
          <div class="px-6 py-4">
            <slot />
          </div>
          <div v-if="$slots.footer" class="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
```

#### Pagination 组件
**src/components/common/Pagination.vue**：
```vue
<template>
  <div class="flex items-center justify-between mt-4">
    <div class="text-sm text-gray-600">
      共 {{ total }} 条
    </div>
    <div class="flex items-center gap-2">
      <button
        @click="emit('update:page', page - 1)"
        :disabled="page <= 1"
        class="px-3 py-1 text-sm border rounded disabled:opacity-50"
      >
        上一页
      </button>
      <span class="text-sm text-gray-600">{{ page }} / {{ totalPages }}</span>
      <button
        @click="emit('update:page', page + 1)"
        :disabled="page >= totalPages"
        class="px-3 py-1 text-sm border rounded disabled:opacity-50"
      >
        下一页
      </button>
    </div>
  </div>
</template>
```

### 3.2 实现用户管理 API

**src/api/users.ts**：
```typescript
import request from './index'

export interface User {
  id: number
  openid: string
  nickname: string
  avatar_url: string
  gender: number | null
  birthday: string | null
  created_at: string
}

export interface UserListResponse {
  items: User[]
  total: number
}

export function getUsers(params: { offset?: number; limit?: number }): Promise<UserListResponse> {
  return request.get('/api/admin/users', { params })
}

export function getUser(userId: number): Promise<User> {
  return request.get(`/api/admin/users/${userId}`)
}

export function deleteUser(userId: number) {
  return request.delete(`/api/admin/users/${userId}`)
}
```

### 3.3 实现用户管理页面

**src/views/users/index.vue**：
```vue
<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">用户管理</h1>
    
    <Table :columns="columns" :data="users" :row-clickable="true" @row-click="showUserDetail">
      <template #cell-avatar_url="{ row }">
        <img :src="row.avatar_url" class="w-8 h-8 rounded-full" />
      </template>
      <template #cell-created_at="{ row }">
        {{ formatDate(row.created_at) }}
      </template>
      <template #actions="{ row }">
        <button @click.stop="showUserDetail(row)" class="text-olive-600 hover:text-olive-800">
          查看
        </button>
      </template>
    </Table>
    
    <Pagination
      :page="page"
      :total="total"
      :page-size="pageSize"
      @update:page="handlePageChange"
    />
  </div>
</template>
```

## 四、已完成内容

- 实现用户管理页面（列表、分页、查看详情）
- 实现角色管理页面（列表、新建、编辑、删除、权限配置）
- 实现管理员管理页面（列表、新建、编辑、重置密码、启用/禁用、删除）
- 实现通用组件（Table、Pagination、Modal）
- 封装用户、角色、管理员API

## 五、验收标准

| 验收项 | 标准 |
|--------|------|
| 用户管理 | 列表分页、查看详情正常 |
| 角色管理 | CRUD操作正常，系统角色保护 |
| 管理员管理 | 创建/编辑/删除/重置密码正常 |
| 通用组件 | Table、Pagination、Modal功能正常 |

## 六、提交规范

```bash
feat(admin): 实现管理功能页面

- 实现用户管理API和页面
- 实现角色管理API和页面
- 实现管理员管理API和页面
- 实现通用组件（Table、Pagination、Modal）
```
