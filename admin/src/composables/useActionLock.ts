import { ref } from 'vue'

/**
 * 通用操作锁：防止提交类操作重复触发（防连点）。
 * 用法：
 *   const { pending, runWithLock } = useActionLock()
 *   const submit = () => runWithLock(async () => { ... })
 * 按钮可绑定 :disabled="pending"
 */
export function useActionLock() {
  const pending = ref(false)

  async function runWithLock<T>(fn: () => Promise<T> | T): Promise<T | undefined> {
    if (pending.value) return
    pending.value = true
    try {
      return await fn()
    } finally {
      pending.value = false
    }
  }

  return { pending, runWithLock }
}
