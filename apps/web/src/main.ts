import { createApp } from 'vue'
import vuetify from './plugins/vuetify'
import './assets/main.css'

import App from './App.vue'
import router from './router'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

const app = createApp(App)

app.use(pinia)
app.use(vuetify)
app.use(router)

window.addEventListener('studio:session-expired', () => {
  useAuthStore(pinia).clear()
  if (router.currentRoute.value.meta.public !== true) {
    void router.replace({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
  }
})

app.mount('#app')
