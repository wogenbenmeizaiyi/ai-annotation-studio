import { ref } from 'vue'

const isOpen = ref(false)
const title = ref('')
const message = ref('')
let resolveFn: ((value: boolean) => void) | null = null

export function useConfirmDialog() {
  const showConfirm = (t: string, msg: string): Promise<boolean> => {
    title.value = t
    message.value = msg
    isOpen.value = true
    return new Promise<boolean>((resolve) => {
      resolveFn = resolve
    })
  }

  const onConfirm = () => {
    isOpen.value = false
    resolveFn?.(true)
    resolveFn = null
  }

  const onCancel = () => {
    isOpen.value = false
    resolveFn?.(false)
    resolveFn = null
  }

  return {
    isOpen,
    title,
    message,
    showConfirm,
    onConfirm,
    onCancel,
  }
}
