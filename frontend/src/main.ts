import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './style.css'

const storedTheme = localStorage.getItem('episode-scrap-theme')
const theme =
  storedTheme === 'light' || storedTheme === 'dark'
    ? storedTheme
    : window.matchMedia('(prefers-color-scheme: light)').matches
      ? 'light'
      : 'dark'
document.documentElement.dataset.theme = theme

createApp(App).use(createPinia()).use(router).mount('#app')
