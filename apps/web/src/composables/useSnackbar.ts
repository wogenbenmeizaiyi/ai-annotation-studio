import { ref } from 'vue'

const visible = ref(false)
const text = ref('')
const color = ref('info')
const timeout = ref(3000)

export function useSnackbar() {
  const showSnackbar = (msg: string, c: string = 'info', t: number = 3000) => {
    text.value = msg
    color.value = c
    timeout.value = t
    visible.value = true
  }

  return {
    visible,
    text,
    color,
    timeout,
    showSnackbar,
  }
}
