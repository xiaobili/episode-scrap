import { reactive } from 'vue'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  type: ToastType
  message: string
}

const state = reactive<{ items: ToastItem[] }>({ items: [] })
let sequence = 0

function remove(id: number) {
  const index = state.items.findIndex((item) => item.id === id)
  if (index >= 0) state.items.splice(index, 1)
}

function push(type: ToastType, message: string, duration = 3600) {
  const id = ++sequence
  state.items.push({ id, type, message })
  window.setTimeout(() => remove(id), duration)
}

export function useToast() {
  return {
    state,
    success: (message: string) => push('success', message),
    error: (message: string) => push('error', message, 5000),
    info: (message: string) => push('info', message),
    dismiss: remove,
  }
}
