<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">管理员管理</h1>
      <button
        @click="showForm = true"
        class="px-4 py-2 bg-olive-600 text-white rounded-lg hover:bg-olive-700"
      >
        新建管理员
      </button>
    </div>

    <!-- 管理员列表 -->
    <Table :columns="columns" :data="admins">
      <template #cell-is_active="{ value }">
        <span
          :class="value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
          class="px-2 py-1 text-xs rounded-full"
        >
          {{ value ? '启用' : '禁用' }}
        </span>
      </template>

      <template #cell-role="{ row }">
        {{ row.role?.name || '--' }}
      </template>

      <template #cell-last_login="{ value }">
        {{ value ? formatDate(value) : '从未登录' }}
      </template>

      <template #actions="{ row }">
        <button
          @click="editAdmin(row)"
          class="text-olive-600 hover:text-olive-800 mr-3"
        >
          编辑
        </button>
        <button
          @click="resetPwd(row)"
          class="text-yellow-600 hover:text-yellow-800 mr-3"
        >
          重置密码
        </button>
        <button
          @click="toggleStatus(row)"
          class="text-blue-600 hover:text-blue-800 mr-3"
        >
          {{ row.is_active ? '禁用' : '启用' }}
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

    <!-- 管理员表单模态框 -->
    <Modal v-model="showForm" :title="editingAdmin ? '编辑管理员' : '新建管理员'">
      <form @submit.prevent="saveAdmin" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
          <input
            v-model="form.username"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            required
            :disabled="!!editingAdmin"
          />
        </div>
        <div v-if="!editingAdmin">
          <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
          <input
            v-model="form.password"
            type="password"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            required
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">昵称</label>
          <input
            v-model="form.nickname"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">角色</label>
          <select
            v-model="form.role_id"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            required
          >
            <option value="">请选择角色</option>
            <option v-for="role in roles" :key="role.id" :value="role.id">
              {{ role.name }}
            </option>
          </select>
        </div>
      </form>

      <template #footer>
        <button
          @click="showForm = false"
          class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
        >
          取消
        </button>
        <button
          @click="saveAdmin"
          class="px-4 py-2 bg-olive-600 text-white rounded-md hover:bg-olive-700"
        >
          保存
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAdmins, createAdmin, updateAdmin, deleteAdmin, resetPassword, toggleAdminStatus, type Admin } from '@/api/admins'
import { getRoles, type Role } from '@/api/roles'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import Modal from '@/components/common/Modal.vue'

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'username', title: '用户名' },
  { key: 'nickname', title: '昵称' },
  { key: 'role', title: '角色' },
  { key: 'is_active', title: '状态' },
  { key: 'last_login', title: '最后登录' }
]

const admins = ref<Admin[]>([])
const roles = ref<Role[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const showForm = ref(false)
const editingAdmin = ref<Admin | null>(null)

const form = ref({
  username: '',
  password: '',
  nickname: '',
  role_id: '' as string | number
})

const formatDate = (date: string) => {
  return new Date(date).toLocaleString('zh-CN')
}

const fetchAdmins = async () => {
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const res = await getAdmins({ offset, limit: pageSize.value })
    admins.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to fetch admins:', e)
  }
}

const fetchRoles = async () => {
  try {
    roles.value = await getRoles()
  } catch (e) {
    console.error('Failed to fetch roles:', e)
  }
}

const editAdmin = (admin: Admin) => {
  editingAdmin.value = admin
  form.value = {
    username: admin.username,
    password: '',
    nickname: admin.nickname,
    role_id: admin.role_id
  }
  showForm.value = true
}

const saveAdmin = async () => {
  try {
    if (editingAdmin.value) {
      await updateAdmin(editingAdmin.value.id, {
        nickname: form.value.nickname,
        role_id: Number(form.value.role_id)
      })
    } else {
      await createAdmin({
        username: form.value.username,
        password: form.value.password,
        nickname: form.value.nickname,
        role_id: Number(form.value.role_id)
      })
    }
    showForm.value = false
    editingAdmin.value = null
    form.value = { username: '', password: '', nickname: '', role_id: '' }
    await fetchAdmins()
  } catch (e) {
    console.error('Failed to save admin:', e)
  }
}

const resetPwd = async (admin: Admin) => {
  const newPwd = prompt(`请输入 ${admin.username} 的新密码：`)
  if (newPwd) {
    try {
      await resetPassword(admin.id, newPwd)
      alert('密码已重置')
    } catch (e) {
      console.error('Failed to reset password:', e)
    }
  }
}

const toggleStatus = async (admin: Admin) => {
  try {
    await toggleAdminStatus(admin.id, !admin.is_active)
    await fetchAdmins()
  } catch (e) {
    console.error('Failed to toggle status:', e)
  }
}

const confirmDelete = async (admin: Admin) => {
  if (confirm(`确定要删除管理员 ${admin.username} 吗？`)) {
    try {
      await deleteAdmin(admin.id)
      await fetchAdmins()
    } catch (e) {
      console.error('Failed to delete admin:', e)
    }
  }
}

onMounted(() => {
  fetchAdmins()
  fetchRoles()
})
</script>
