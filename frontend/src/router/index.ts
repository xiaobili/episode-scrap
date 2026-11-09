import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'scan',
      component: () => import('@/views/ScanView.vue'),
      meta: { title: '扫描' },
    },
    {
      path: '/parse',
      name: 'parse',
      component: () => import('@/views/ParseView.vue'),
      meta: { title: '解析' },
    },
    {
      path: '/scrape',
      name: 'scrape',
      component: () => import('@/views/ScrapeView.vue'),
      meta: { title: '刮削' },
    },
    {
      path: '/rename',
      name: 'rename',
      component: () => import('@/views/RenameView.vue'),
      meta: { title: '重命名' },
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: () => import('@/views/TasksView.vue'),
      meta: { title: '任务中心' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { title: '设置' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.afterEach((to) => {
  const title = (to.meta.title as string | undefined) ?? '工作台'
  document.title = `${title} · EpisodeScrap`
})

export default router
