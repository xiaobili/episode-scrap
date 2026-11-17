import { onBeforeUnmount, ref, type Ref } from 'vue'

export function useTimecode(fps = 24): Ref<string> {
  const value = ref('')
  const pad = (n: number) => String(n).padStart(2, '0')

  const update = () => {
    const now = new Date()
    const frame = Math.floor((now.getMilliseconds() / 1000) * fps)
    value.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}:${pad(frame)}`
  }

  update()
  const timer = window.setInterval(update, Math.max(16, Math.floor(1000 / fps)))
  onBeforeUnmount(() => window.clearInterval(timer))
  return value
}
