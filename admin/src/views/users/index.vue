<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">用户管理</h1>
    </div>

    <!-- 用户列表 -->
    <Table :columns="columns" :data="users">
      <template #cell-avatar_url="{ row }">
        <img
          v-if="row.avatar_url"
          :src="getAvatarUrl(row.avatar_url)"
          class="w-8 h-8 rounded-full"
          alt="avatar"
        />
        <div v-else class="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
          <span class="text-gray-500 text-sm">{{ row.nickname?.charAt(0) || 'U' }}</span>
        </div>
      </template>

      <template #cell-created_at="{ value }">
        {{ formatDate(value) }}
      </template>

      <template #actions="{ row }">
        <button
          @click="viewUser(row)"
          class="text-olive-600 hover:text-olive-800 mr-3"
        >
          查看
        </button>
        <button
          @click="confirmDelete(row)"
          class="text-red-600 hover:text-red-800"
        >
          删除
        </button>
      </template>
    </Table>

    <!-- 分页 -->
    <Pagination
      :total="total"
      :page-size="pageSize"
      v-model:current-page="currentPage"
    />

    <!-- 用户详情模态框 -->
    <Modal v-model="showDetail" title="用户详情">
      <div v-if="selectedUser" class="space-y-4">
        <div class="flex items-center gap-4">
          <img
            v-if="selectedUser.avatar_url"
            :src="getAvatarUrl(selectedUser.avatar_url)"
            class="w-16 h-16 rounded-full"
            alt="avatar"
          />
          <div>
            <p class="font-medium">{{ selectedUser.nickname }}</p>
            <p class="text-sm text-gray-500">ID: {{ selectedUser.id }}</p>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span class="text-gray-500">性别：</span>
            <span>{{ selectedUser.gender || '未设置' }}</span>
          </div>
          <div>
            <span class="text-gray-500">生日：</span>
            <span>{{ selectedUser.birthday || '未设置' }}</span>
          </div>
          <div>
            <span class="text-gray-500">注册时间：</span>
            <span>{{ formatDate(selectedUser.created_at) }}</span>
          </div>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getUsers, deleteUser, type User } from '@/api/users'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import Modal from '@/components/common/Modal.vue'

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'avatar_url', title: '头像' },
  { key: 'nickname', title: '昵称' },
  { key: 'gender', title: '性别' },
  { key: 'created_at', title: '创建时间' }
]

const users = ref<User[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const showDetail = ref(false)
const selectedUser = ref<User | null>(null)

const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('zh-CN')
}

const getAvatarUrl = (avatarUrl: string | null | undefined): string => {
  if (!avatarUrl) return ''
  if (avatarUrl.startsWith('http')) return avatarUrl
  const baseURL = import.meta.env.VITE_API_BASE_URL || ''
  const path = avatarUrl.replace(/^avatars\//, 'avatar/')
  return `${baseURL}/api/upload/${path}`
}

const fetchUsers = async () => {
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const res = await getUsers({ offset, limit: pageSize.value })
    users.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch users:', e)
  }
}

const viewUser = (user: User) => {
  selectedUser.value = user
  showDetail.value = true
}

const confirmDelete = async (user: User) => {
  if (confirm(`确定要删除用户 ${user.nickname} 吗？`)) {
    try {
      await deleteUser(user.id)
      await fetchUsers()
    } catch (e) {
      console.error('Failed to delete user:', e)
    }
  }
}

onMounted(fetchUsers)
</script>
