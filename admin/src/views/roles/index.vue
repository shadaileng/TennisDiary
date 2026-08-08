<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">角色管理</h1>
      <button
        @click="showForm = true"
        class="px-4 py-2 bg-olive-600 text-white rounded-lg hover:bg-olive-700"
      >
        新建角色
      </button>
    </div>

    <!-- 角色列表 -->
    <Table :columns="columns" :data="roles">
      <template #cell-is_system="{ value }">
        <span
          :class="value ? 'bg-gray-100 text-gray-800' : 'bg-green-100 text-green-800'"
          class="px-2 py-1 text-xs rounded-full"
        >
          {{ value ? '系统角色' : '自定义' }}
        </span>
      </template>

      <template #cell-permissions="{ value }">
        <span class="text-sm text-gray-600">{{ value?.length || 0 }} 个权限</span>
      </template>

      <template #actions="{ row }">
        <button
          @click="editRole(row)"
          class="text-olive-600 hover:text-olive-800 mr-3"
          :disabled="row.is_system"
        >
          编辑
        </button>
        <button
          @click="confirmDelete(row)"
          class="text-red-600 hover:text-red-800"
          :disabled="row.is_system"
        >
          删除
        </button>
      </template>
    </Table>

    <!-- 角色表单模态框 -->
    <Modal v-model="showForm" :title="editingRole ? '编辑角色' : '新建角色'">
      <form @submit.prevent="saveRole" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">角色名称</label>
          <input
            v-model="form.name"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            required
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">角色编码</label>
          <input
            v-model="form.code"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            required
            :disabled="!!editingRole"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
          <textarea
            v-model="form.description"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-olive-500"
            rows="3"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">权限</label>
          <div class="max-h-48 overflow-y-auto border rounded-md p-2">
            <label
              v-for="perm in permissions"
              :key="perm.code"
              class="flex items-center gap-2 py-1"
            >
              <input
                type="checkbox"
                :value="perm.code"
                v-model="form.permissions"
                class="w-4 h-4 text-olive-600 border-gray-300 rounded focus:ring-olive-500"
              />
              <span class="text-sm">{{ perm.name }}</span>
            </label>
          </div>
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
          @click="saveRole"
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
import { getRoles, createRole, updateRole, deleteRole, getPermissions, type Role, type Permission } from '@/api/roles'
import Table from '@/components/common/Table.vue'
import Modal from '@/components/common/Modal.vue'

const columns = [
  { key: 'name', title: '角色名' },
  { key: 'code', title: '编码' },
  { key: 'description', title: '描述' },
  { key: 'permissions', title: '权限数' },
  { key: 'is_system', title: '类型' }
]

const roles = ref<Role[]>([])
const permissions = ref<Permission[]>([])
const showForm = ref(false)
const editingRole = ref<Role | null>(null)

const form = ref({
  name: '',
  code: '',
  description: '',
  permissions: [] as string[]
})

const fetchRoles = async () => {
  try {
    roles.value = await getRoles()
  } catch (e) {
    console.error('Failed to fetch roles:', e)
  }
}

const fetchPermissions = async () => {
  try {
    permissions.value = await getPermissions()
  } catch (e) {
    console.error('Failed to fetch permissions:', e)
  }
}

const editRole = (role: Role) => {
  editingRole.value = role
  form.value = {
    name: role.name,
    code: role.code,
    description: role.description,
    permissions: [...role.permissions]
  }
  showForm.value = true
}

const saveRole = async () => {
  try {
    if (editingRole.value) {
      await updateRole(editingRole.value.id, form.value)
    } else {
      await createRole(form.value)
    }
    showForm.value = false
    editingRole.value = null
    form.value = { name: '', code: '', description: '', permissions: [] }
    await fetchRoles()
  } catch (e) {
    console.error('Failed to save role:', e)
  }
}

const confirmDelete = async (role: Role) => {
  if (confirm(`确定要删除角色 ${role.name} 吗？`)) {
    try {
      await deleteRole(role.id)
      await fetchRoles()
    } catch (e) {
      console.error('Failed to delete role:', e)
    }
  }
}

onMounted(() => {
  fetchRoles()
  fetchPermissions()
})
</script>
