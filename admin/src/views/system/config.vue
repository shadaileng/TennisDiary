<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-800">系统配置</h1>
      <div class="flex items-center gap-3">
        <button
          @click="testConnect"
          :disabled="testing"
          class="px-4 py-2 text-sm bg-olive-600 text-white rounded-lg hover:bg-olive-700 disabled:opacity-50"
        >
          {{ testing ? '测试中…' : '测试 AI 连接' }}
        </button>
        <button
          @click="refresh"
          class="px-4 py-2 text-sm bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
        >
          刷新
        </button>
        <button
          @click="handleResetAll"
          :disabled="resetAllPending || configs.summary?.overridden === 0"
          class="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
        >
          {{ resetAllPending ? '恢复中…' : '全部恢复默认' }}
        </button>
      </div>
    </div>

    <p v-if="connectMsg" class="mb-4 text-sm" :class="connectMsg.ok ? 'text-green-600' : 'text-red-500'">
      {{ connectMsg.text }}
    </p>

    <!-- 概览条 -->
    <div v-if="configs.summary" class="grid grid-cols-3 gap-6 mb-6">
      <div class="bg-white rounded-lg shadow-md p-4 flex flex-col items-center">
        <span class="text-3xl font-bold text-gray-800">{{ configs.summary.total }}</span>
        <span class="text-sm text-gray-500 mt-1">配置项总数</span>
      </div>
      <div class="bg-white rounded-lg shadow-md p-4 flex flex-col items-center">
        <span class="text-3xl font-bold text-olive-600">{{ configs.summary.editable }}</span>
        <span class="text-sm text-gray-500 mt-1">可动态配置</span>
      </div>
      <div class="bg-white rounded-lg shadow-md p-4 flex flex-col items-center">
        <span class="text-3xl font-bold" :class="configs.summary.overridden ? 'text-green-600' : 'text-gray-800'">
          {{ configs.summary.overridden }}
        </span>
        <span class="text-sm text-gray-500 mt-1">已自定义覆盖</span>
      </div>
    </div>

    <!-- AI 状态概览 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-800">AI 服务商</h2>
        <div class="flex items-center gap-3">
          <span
            v-if="ai.summary"
            :class="ai.summary.ok ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'"
            class="px-3 py-1 rounded-full text-xs font-medium"
          >
            {{ ai.summary.ok ? '全部就绪' : `缺失: ${ai.summary.missing.join('、')}` }}
          </span>
          <button
            @click="openProviderManager"
            class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
          >
            管理服务商
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-600 mb-1.5">当前服务商（直选）</label>
          <div class="flex items-center gap-2">
            <select
              :value="providerValue"
              @change="onProviderSelectChange"
              class="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-olive-600"
            >
              <option value="custom">自定义（使用独立配置）</option>
              <option v-for="p in providers" :key="p.id" :value="p.name">
                {{ p.name }}{{ p.is_selected ? '（当前）' : '' }}
              </option>
            </select>
            <span
              v-if="providerValue !== 'custom'"
              class="text-xs px-2 py-1 bg-green-100 text-green-800 rounded-full shrink-0"
            >
              引用生效
            </span>
          </div>
          <p v-if="providerValue === 'custom'" class="text-xs text-gray-400 mt-1.5">
            直选服务商后接口地址与密钥引用服务商条目；自定义时使用下方 AI 分类中的独立配置。
          </p>
          <p v-else class="text-xs text-gray-400 mt-1.5">
            修改服务商条目（含密钥）将全局生效，无需重启。
          </p>
        </div>

        <div class="space-y-2">
          <div class="flex justify-between items-center">
            <span class="text-gray-600">API Key</span>
            <div class="text-right">
              <span v-if="ai.ai?.configured" class="text-green-600 font-medium">已配置</span>
              <span v-else class="text-red-500">未配置</span>
              <div v-if="ai.ai?.key_masked" class="text-xs text-gray-400">{{ ai.ai.key_masked }}</div>
            </div>
          </div>
          <div class="flex justify-between items-center gap-4">
            <span class="text-gray-600 shrink-0">模型</span>
            <div v-if="providerValue !== 'custom'" class="flex-1 flex items-center justify-end gap-2">
              <select
                :value="effectiveModel"
                @change="onModelSelectChange"
                class="px-3 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-olive-600 text-sm max-w-[260px]"
              >
                <option v-for="m in providerModelOptions" :key="m.value" :value="m.value">
                  {{ m.label }}
                </option>
              </select>
            </div>
            <span v-else class="text-gray-800">{{ ai.ai?.model || '--' }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">Base URL</span>
            <span class="text-gray-800 truncate ml-4">{{ ai.ai?.base_url || '--' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 分类卡片 -->
    <div class="grid grid-cols-1 gap-6">
      <div v-for="cat in categories" :key="cat.key" class="bg-white rounded-lg shadow-md">
        <div class="flex items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100">
          <div>
            <h2 class="text-lg font-semibold text-gray-800">{{ cat.label }}</h2>
            <p class="text-sm text-gray-500 mt-0.5">{{ cat.description }}</p>
          </div>
          <span class="text-sm text-gray-400">
            {{ cat.editable_count > 0 ? `${cat.editable_count} 项可编辑 · ` : '' }}{{ cat.item_count }} 项
          </span>
        </div>
        <div class="px-6 py-2">
          <template v-if="cat.key === 'ai' && providerValue !== 'custom'">
            <div class="py-3 border-b border-gray-50 text-sm text-gray-500">
              <span class="text-olive-600 font-medium">{{ providerValue }}</span>
              服务商引用生效中：接口地址与密钥由服务商条目提供，模型可单独覆盖。
            </div>
          </template>
          <div
            v-for="item in itemsByCategory(cat.key)"
            :key="item.key"
            class="flex items-center justify-between py-3 border-b border-gray-50 last:border-0"
          >
            <div class="flex-1 pr-4">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-gray-800">{{ item.label }}</span>
                <span class="font-mono text-xs text-gray-400">{{ item.key }}</span>
              </div>
              <p class="text-xs text-gray-500 mt-0.5">{{ item.description }}</p>
              <div class="mt-1.5 flex items-center gap-2">
                <span
                  class="px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="item.key === 'ai.model' && providerValue !== 'custom' ? 'bg-olive-100 text-olive-700' : sourceBadgeClass(item.source)"
                >
                  {{ item.key === 'ai.model' && providerValue !== 'custom' ? '引用生效' : sourceBadgeText(item.source) }}
                </span>
                <span class="text-sm text-gray-700">{{ displayValue(item) }}</span>
                <span
                  v-if="item.key === 'ai.model' && providerValue !== 'custom'"
                  class="text-xs text-gray-400"
                >
                  （来自服务商{{ providerValue }}，可配置 ai.model 覆盖）
                </span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <button
                v-if="item.editable"
                @click="openEdit(item)"
                class="px-3 py-1.5 text-sm bg-olive-600 text-white rounded-lg hover:bg-olive-700"
              >
                {{ item.source === 'db' ? '修改' : '配置' }}
              </button>
              <button
                v-if="item.source === 'db'"
                @click="handleReset(item)"
                :disabled="resetPending"
                class="px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 disabled:opacity-50"
              >
                恢复默认
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 配置项编辑弹窗 -->
    <div v-if="editing" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="cancelEdit">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-800">配置 {{ editing.label }}</h3>
          <button @click="cancelEdit" class="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>
        <div class="px-6 py-4">
          <p class="text-sm text-gray-500 mb-3">{{ editing.description }}</p>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            {{ editing.value_type === 'secret' ? '密钥' : '值' }}
          </label>
          <select
            v-if="editing.value_type === 'select'"
            v-model="editValue"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-olive-600"
          >
            <option v-for="opt in editing.options || []" :key="opt" :value="opt">{{ opt }}</option>
          </select>
          <input
            v-else
            :type="editing.value_type === 'secret' ? 'password' : 'text'"
            v-model="editValue"
            :placeholder="editing.source === 'db'
              ? '已设置，留空则不修改'
              : editing.value_type === 'secret' ? '留空保持默认' : editing.default_value"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-olive-600"
          />
          <div class="mt-3 text-xs text-gray-400">
            生效值 = 自定义覆盖 &gt; 环境变量默认；留空或填写与默认一致将回退到默认值。
          </div>
        </div>
        <div class="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
          <button
            @click="cancelEdit"
            class="px-4 py-2 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
          >
            取消
          </button>
          <button
            @click="handleSave"
            :disabled="savePending"
            class="px-4 py-2 text-sm bg-olive-600 text-white rounded-lg hover:bg-olive-700 disabled:opacity-50"
          >
            {{ savePending ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 服务商管理弹窗 -->
    <div
      v-if="showProviderManager"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      @click.self="closeProviderManager"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4 max-h-[85vh] flex flex-col">
        <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-800">管理服务商</h3>
          <button @click="closeProviderManager" class="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        <div class="px-6 py-4 overflow-y-auto">
          <!-- 服务商表格 -->
          <div class="flex items-center justify-between mb-3">
            <p class="text-sm text-gray-500">手动维护 OpenAI 兼容服务商；被当前直选引用的服务商不可删除。</p>
            <button
              @click="openProviderForm()"
              class="px-3 py-1.5 text-sm bg-olive-600 text-white rounded-lg hover:bg-olive-700"
            >
              + 新增服务商
            </button>
          </div>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-gray-500 border-b border-gray-100">
                <th class="py-2 pr-3 font-medium">名称</th>
                <th class="py-2 pr-3 font-medium">Base URL</th>
                <th class="py-2 pr-3 font-medium">模型</th>
                <th class="py-2 pr-3 font-medium">API Key</th>
                <th class="py-2 pr-3 font-medium">启用</th>
                <th class="py-2 pr-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in providers" :key="p.id" class="border-b border-gray-50">
                <td class="py-2.5 pr-3">
                  <span class="font-medium text-gray-800">{{ p.name }}</span>
                  <span v-if="p.is_selected" class="ml-1.5 text-xs px-1.5 py-0.5 bg-olive-100 text-olive-700 rounded-full">当前</span>
                </td>
                <td class="py-2.5 pr-3 text-gray-600 truncate max-w-[180px]">{{ p.base_url }}</td>
                <td class="py-2.5 pr-3 text-gray-600 truncate max-w-[180px]" :title="p.models.join('、')">
                  {{ p.default_model }}<span v-if="p.models.length > 1" class="text-gray-400"> 等 {{ p.models.length }} 个</span>
                </td>
                <td class="py-2.5 pr-3 text-gray-600">{{ p.api_key || '—' }}</td>
                <td class="py-2.5 pr-3">
                  <span :class="p.enabled ? 'text-green-600' : 'text-gray-400'">{{ p.enabled ? '启用' : '停用' }}</span>
                </td>
                <td class="py-2.5 text-right whitespace-nowrap">
                  <button @click="openProviderForm(p)" class="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200">编辑</button>
                  <button
                    @click="handleDeleteProvider(p)"
                    :disabled="providerPending"
                    class="ml-1.5 px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100 disabled:opacity-50"
                  >
                    删除
                  </button>
                </td>
              </tr>
              <tr v-if="providers.length === 0">
                <td colspan="6" class="py-8 text-center text-gray-400">暂无服务商，点击「新增服务商」添加</td>
              </tr>
            </tbody>
          </table>

          <!-- 新增/编辑表单 -->
          <div v-if="showProviderForm" class="mt-4 border border-gray-200 rounded-lg p-4 bg-gray-50">
            <h4 class="text-sm font-semibold text-gray-800 mb-3">
              {{ providerForm.id ? '编辑服务商' : '新增服务商' }}
            </h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">名称 *</label>
                <input v-model="providerForm.name" class="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-olive-600" placeholder="如：阿里云百炼" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">模型 *</label>
                <div class="space-y-1.5">
                  <div v-for="(_, idx) in providerForm.models" :key="idx" class="flex items-center gap-1.5">
                    <input
                      v-model="providerForm.models[idx]"
                      class="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-olive-600"
                      :placeholder="idx === 0 ? '默认模型，如：qwen-vl-max' : '如：qwen-plus'"
                    />
                    <span v-if="idx === 0" class="text-xs px-1.5 py-0.5 bg-olive-100 text-olive-700 rounded shrink-0">默认</span>
                    <span
                      v-if="modelCheckOf(idx)"
                      class="text-xs px-1.5 py-0.5 rounded shrink-0"
                      :class="modelCheckOf(idx)!.ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                      :title="modelCheckOf(idx)!.message"
                    >
                      {{ modelCheckOf(idx)!.ok ? '✓ 可用' : '✗ 不可用' }}
                    </span>
                    <button
                      type="button"
                      @click="removeModel(idx)"
                      class="px-2 py-1 text-xs bg-gray-200 text-gray-600 rounded hover:bg-gray-300 shrink-0"
                    >
                      删
                    </button>
                  </div>
                  <div class="flex gap-2">
                    <button
                      type="button"
                      @click="providerForm.models.push('')"
                      class="flex-1 py-1.5 text-xs border border-dashed border-gray-300 text-gray-500 rounded-lg hover:border-olive-400 hover:text-olive-600"
                    >
                      + 添加模型
                    </button>
                    <button
                      type="button"
                      @click="handleCheckModels"
                      :disabled="modelCheckPending"
                      class="px-3 py-1.5 text-xs bg-olive-600 text-white rounded-lg hover:bg-olive-700 disabled:opacity-50 shrink-0"
                    >
                      {{ modelCheckPending ? '校验中…' : '校验模型' }}
                    </button>
                  </div>
                </div>
                <p class="text-xs text-gray-400 mt-1">首行为默认模型；保存时自动去除空行</p>
                <div
                  v-if="checkResult && !checkResult.ok"
                  class="mt-1.5 text-xs text-red-600"
                >
                  校验失败：{{ checkResult.message }}
                </div>
                <div
                  v-if="checkResult && checkResult.ok && checkResult.strategy === 'list' && (checkResult.available || []).length"
                  class="mt-1.5 text-xs text-gray-500"
                >
                  服务商可用模型（{{ checkResult.available!.length }} 个）：
                  <span class="text-gray-400">{{ checkResult.available!.slice(0, 12).join('、') }}{{ (checkResult.available!.length > 12 ? ' …' : '') }}</span>
                </div>
                <div
                  v-if="checkResult && checkResult.ok && checkResult.strategy === 'probe'"
                  class="mt-1.5 text-xs text-gray-500"
                >
                  该接口不支持模型列表，已逐模型探测：
                  <span
                    v-for="r in checkResult.results"
                    :key="r.model"
                    class="mr-2"
                    :class="r.ok ? 'text-green-600' : 'text-red-600'"
                    :title="r.message"
                  >
                    {{ r.model }} {{ r.ok ? '✓' : '✗' }}
                  </span>
                </div>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">Base URL *</label>
                <input v-model="providerForm.base_url" class="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-olive-600" placeholder="https://.../v1" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">API Key</label>
                <input
                  v-model="providerForm.api_key"
                  type="password"
                  class="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-olive-600"
                  :placeholder="providerForm.id ? '留空则不修改' : '可选，留空表示无 Key'"
                />
              </div>
            </div>
            <div class="mt-3 flex items-center gap-2">
              <input v-model="providerForm.enabled" type="checkbox" id="provider-enabled" class="accent-olive-600" />
              <label for="provider-enabled" class="text-sm text-gray-600">启用（可被直选引用）</label>
            </div>
            <div class="mt-4 flex justify-end gap-2">
              <button @click="cancelProviderForm" class="px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
                取消
              </button>
              <button
                @click="handleSaveProvider"
                :disabled="providerSavePending"
                class="px-3 py-1.5 text-sm bg-olive-600 text-white rounded-lg hover:bg-olive-700 disabled:opacity-50"
              >
                {{ providerSavePending ? '保存中…' : '保存' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useToastStore } from '@/stores/toast'
import { useActionLock } from '@/composables/useActionLock'
import {
  getConfigs,
  updateConfig,
  resetConfig,
  resetAllConfigs,
  getProviders,
  addProvider,
  updateProvider,
  deleteProvider,
  checkProviderModels,
  type ConfigItem,
  type ConfigList,
  type AiProvider,
  type ProviderModelsCheck,
  type ModelCheckResult
} from '@/api/config'
import { getAiStatus, testAiConnect, type AiStatus } from '@/api/system'

const toast = useToastStore()
const configs = ref<ConfigList>({
  summary: { total: 0, editable: 0, overridden: 0, categories: [] },
  items: []
})
const ai = ref<AiStatus>({
  ai: { configured: false, model: '', base_url: '', key_masked: '', provider: 'custom' },
  ffmpeg: { available: false, version: '' },
  mediapipe: { available: false },
  pose_model: { available: false, path: '' },
  summary: { ok: false, missing: [] }
})
const providers = ref<AiProvider[]>([])
const testing = ref(false)
const connectMsg = ref<{ ok: boolean; text: string } | null>(null)

const { pending: savePending, runWithLock: runSave } = useActionLock()
const { pending: resetPending, runWithLock: runReset } = useActionLock()
const { pending: resetAllPending, runWithLock: runResetAll } = useActionLock()
const { pending: providerPending, runWithLock: runProviderDelete } = useActionLock()
const { pending: providerSavePending, runWithLock: runProviderSave } = useActionLock()
const { pending: modelCheckPending, runWithLock: runModelCheck } = useActionLock()
const checkResult = ref<ProviderModelsCheck | null>(null)

const editing = ref<ConfigItem | null>(null)
const editValue = ref('')

const showProviderManager = ref(false)
const showProviderForm = ref(false)
const providerForm = reactive<{
  id: number | null
  name: string
  base_url: string
  api_key: string
  models: string[]
  enabled: boolean
}>({ id: null, name: '', base_url: '', api_key: '', models: [''], enabled: true })

const categories = computed(() => {
  return configs.value.summary.categories.map(cat => ({
    ...cat,
    editable_count: configs.value.items.filter(i => i.category === cat.key && i.editable).length
  }))
})

const providerItem = computed(() => configs.value.items.find(i => i.key === 'ai.provider'))
const providerValue = computed(() => providerItem.value?.value || 'custom')
const selectedProvider = computed(() => providers.value.find(p => p.name === providerValue.value))

const effectiveModel = computed(() => {
  if (providerValue.value === 'custom') return ai.value.ai?.model || ''
  return ai.value.ai?.model || selectedProvider.value?.default_model || ''
})

const providerModelOptions = computed<{ value: string; label: string }[]>(() => {
  const models = selectedProvider.value?.models || []
  const options = models.map(m => ({ value: m, label: m }))
  const effective = effectiveModel.value
  if (effective && !models.includes(effective)) {
    options.push({ value: effective, label: `自定义: ${effective}` })
  }
  options.unshift({ value: '', label: '跟随服务商默认' })
  return options
})

const itemsByCategory = (key: string) => {
  let items = configs.value.items.filter(i => i.category === key)
  if (key === 'ai' && providerValue.value !== 'custom') {
    items = items.filter(i => i.key !== 'ai.api_key' && i.key !== 'ai.base_url')
  }
  return items
}

const sourceBadgeClass = (source: string) => {
  if (source === 'db') return 'bg-green-100 text-green-800'
  if (source === 'builtin') return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-600'
}

const sourceBadgeText = (source: string) => {
  if (source === 'db') return '自定义'
  if (source === 'builtin') return '内置'
  return '默认'
}

const displayValue = (item: ConfigItem) => {
  if (item.key === 'ai.model' && providerValue.value !== 'custom') {
    return ai.value.ai?.model || item.value
  }
  if (!item.has_value) return '（未设置）'
  return item.value
}

const fetchConfigs = async () => {
  try {
    configs.value = await getConfigs()
  } catch (e) {
    console.error('Failed to fetch configs:', e)
  }
}

const fetchAiStatus = async () => {
  try {
    ai.value = await getAiStatus()
  } catch (e) {
    console.error('Failed to fetch AI status:', e)
  }
}

const fetchProviders = async () => {
  try {
    const data = await getProviders()
    providers.value = data.providers
  } catch (e) {
    console.error('Failed to fetch providers:', e)
  }
}

const refresh = () => {
  fetchConfigs()
  fetchAiStatus()
  fetchProviders()
}

const onProviderSelectChange = async (event: Event) => {
  const value = (event.target as HTMLSelectElement).value
  if (value === providerValue.value) return
  try {
    await updateConfig('ai.provider', value)
    toast.success(value === 'custom' ? '已切换为自定义配置' : `已直选服务商：${value}`)
    refresh()
  } catch (e) {
    console.error('Failed to select provider:', e)
  }
}

const openEdit = (item: ConfigItem) => {
  editing.value = item
  editValue.value = ''
}

const cancelEdit = () => {
  editing.value = null
  editValue.value = ''
}

const handleSave = () =>
  runSave(async () => {
    if (!editing.value) return
    await updateConfig(editing.value.key, editValue.value)
    toast.success('配置已保存')
    cancelEdit()
    refresh()
  })

const handleReset = (item: ConfigItem) =>
  runReset(async () => {
    await resetConfig(item.key)
    toast.success(`${item.label} 已恢复默认`)
    refresh()
  })

const handleResetAll = () => {
  if (!window.confirm('确定将全部配置恢复为环境变量默认值吗？此操作不可撤销。')) return
  runResetAll(async () => {
    await resetAllConfigs()
    toast.success('已全部恢复默认')
    refresh()
  })
}

const testConnect = async () => {
  testing.value = true
  connectMsg.value = null
  try {
    const res = await testAiConnect()
    connectMsg.value = {
      ok: res.ok,
      text: res.message || (res.ok ? 'AI 连接正常' : 'AI 连接失败')
    }
  } catch (e) {
    connectMsg.value = { ok: false, text: 'AI 连接测试失败' }
  } finally {
    testing.value = false
  }
}

// ==================== 服务商管理 ====================

const openProviderManager = () => {
  showProviderManager.value = true
  fetchProviders()
}

const closeProviderManager = () => {
  showProviderManager.value = false
  showProviderForm.value = false
}

const openProviderForm = (provider?: AiProvider) => {
  showProviderForm.value = true
  checkResult.value = null
  if (provider) {
    Object.assign(providerForm, {
      id: provider.id,
      name: provider.name,
      base_url: provider.base_url,
      api_key: '',
      models: [...provider.models],
      enabled: provider.enabled
    })
  } else {
    Object.assign(providerForm, { id: null, name: '', base_url: '', api_key: '', models: [''], enabled: true })
  }
}

const removeModel = (idx: number) => {
  if (providerForm.models.length <= 1) {
    toast.warning('至少保留一个模型')
    return
  }
  providerForm.models.splice(idx, 1)
}

const modelCheckOf = (idx: number): ModelCheckResult | null => {
  if (!checkResult.value) return null
  const name = providerForm.models[idx]?.trim()
  if (!name) return null
  if (checkResult.value.strategy === 'list') {
    const available = checkResult.value.available || []
    return { model: name, ok: available.includes(name), message: available.includes(name) ? '可用' : '不在服务商模型列表中' }
  }
  return checkResult.value.results.find(r => r.model === name) || null
}

const handleCheckModels = () =>
  runModelCheck(async () => {
    const models = providerForm.models.map(m => m.trim()).filter(m => m)
    if (!providerForm.base_url.trim()) {
      toast.warning('请先填写 Base URL')
      return
    }
    if (models.length === 0) {
      toast.warning('至少填写一个模型名')
      return
    }
    checkResult.value = await checkProviderModels({
      base_url: providerForm.base_url.trim(),
      api_key: providerForm.api_key.trim(),
      models
    })
    const missing = checkResult.value.results.filter(r => !r.ok)
    if (checkResult.value.ok && missing.length === 0) {
      toast.success('全部模型可用')
    } else if (checkResult.value.ok) {
      toast.warning(`${missing.length} 个模型不可用，请核对模型名`)
    } else {
      toast.error(checkResult.value.message || '校验失败')
    }
  })

const cancelProviderForm = () => {
  showProviderForm.value = false
  checkResult.value = null
}

const handleSaveProvider = () =>
  runProviderSave(async () => {
    const payload = {
      name: providerForm.name,
      base_url: providerForm.base_url,
      api_key: providerForm.api_key,
      models: providerForm.models.map(m => m.trim()).filter(m => m),
      enabled: providerForm.enabled
    }
    if (payload.models.length === 0) {
      toast.warning('至少需要一个模型')
      return
    }
    if (providerForm.id) {
      await updateProvider(providerForm.id, payload)
      toast.success('服务商已更新')
    } else {
      await addProvider(payload)
      toast.success('服务商已添加')
    }
    showProviderForm.value = false
    fetchProviders()
    refresh()
  })

const onModelSelectChange = async (event: Event) => {
  const value = (event.target as HTMLSelectElement).value
  const current = effectiveModel.value
  if (value === '' && current === (selectedProvider.value?.default_model || '')) {
    return
  }
  try {
    if (value === '') {
      await resetConfig('ai.model')
      toast.success('模型已恢复为服务商默认')
    } else {
      await updateConfig('ai.model', value)
      toast.success(`模型已切换：${value}`)
    }
    refresh()
  } catch (e) {
    console.error('Failed to select model:', e)
  }
}

const handleDeleteProvider = (provider: AiProvider) =>
  runProviderDelete(async () => {
    if (provider.is_selected) {
      toast.warning('该服务商正被 ai.provider 引用，请先在配置中切换服务商')
      return
    }
    if (!window.confirm(`确定删除服务商「${provider.name}」吗？`)) return
    try {
      await deleteProvider(provider.id)
      toast.success(`服务商「${provider.name}」已删除`)
      fetchProviders()
      refresh()
    } catch (e) {
      console.error('Failed to delete provider:', e)
    }
  })

onMounted(refresh)
</script>
