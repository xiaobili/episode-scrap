<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import SelectMenu from '@/components/SelectMenu.vue'
import TemplateEditor from '@/components/TemplateEditor.vue'
import type { SlateRow } from '@/components/ui-types'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'
import type { OpenListInstance, Settings, StrmRule } from '@/types'

type TabKey = 'providers' | 'openlist' | 'template' | 'strm' | 'jellyfin' | 'general'
type TabTone = 'ok' | 'warn' | 'idle'

const store = useWorkflowStore()
const toast = useToast()

const tab = ref<TabKey>('providers')
const tabs: {
  key: TabKey
  label: string
  en: string
  icon: string
  desc: string
}[] = [
  {
    key: 'providers',
    label: '媒体源',
    en: 'PROVIDERS',
    icon: 'sparkles',
    desc: '刮削与季集信息依赖媒体源 API，Key 仅保存在服务端。',
  },
  {
    key: 'openlist',
    label: 'OpenList',
    en: 'INSTANCES',
    icon: 'cloud',
    desc: '管理云盘实例，配置后即可在扫描页直接浏览远程目录。',
  },
  {
    key: 'template',
    label: '命名模板',
    en: 'TEMPLATE',
    icon: 'rename',
    desc: '定义重命名后的文件名结构，修改时可实时预览效果。',
  },
  {
    key: 'strm',
    label: 'STRM',
    en: 'STREAM LINKS',
    icon: 'film',
    desc: '为媒体生成指向数据源的 .strm 链接文件，供媒体服务器串流。',
  },
  {
    key: 'jellyfin',
    label: 'Jellyfin',
    en: 'INTEGRATION',
    icon: 'server',
    desc: '接入媒体服务器，在重命名与刮削完成后触发媒体库刷新。',
  },
  {
    key: 'general',
    label: '通用',
    en: 'ADVANCED',
    icon: 'settings',
    desc: '本地目录白名单与 OpenList 请求参数等高级选项。',
  },
]

const error = ref('')
const saving = ref(false)

const tmdbKey = ref('')

const instances = ref<OpenListInstance[]>([])
const instancesLoading = ref(false)
const testState = ref<Record<number, { ok: boolean; message: string }>>({})
const testingId = ref<number | null>(null)

const formOpen = ref(false)
const editing = ref<OpenListInstance | null>(null)
const formSaving = ref(false)
const form = ref({
  name: '',
  base_url: '',
  username: '',
  password: '',
  mount_path: '/',
  timeout: 30,
  concurrency: 3,
})

const deleteTarget = ref<OpenListInstance | null>(null)
const deleting = ref(false)

const templateDraft = ref('')
const sample = computed(() => store.parsedFiles[0] ?? null)

const allowedPaths = ref('')
const concurrency = ref(3)
const timeout = ref(30)
const retry = ref(0)
const strmTemplate = ref('')
const strmMode = ref<'alongside' | 'library' | 'mirror'>('alongside')
const strmTargetDir = ref('')
const strmRules = ref<StrmRule[]>([])
const jellyfinUrl = ref('')
const jellyfinKey = ref('')
const jellyfinTesting = ref(false)
const hydrated = ref(false)

const activeTab = computed(() => tabs.find((item) => item.key === tab.value) ?? tabs[0])
const activeIndex = computed(() =>
  String(tabs.findIndex((item) => item.key === tab.value) + 1).padStart(2, '0'),
)
const jellyfinConfigured = computed(
  () => Boolean(store.settings?.jellyfin_url && store.settings?.has_jellyfin_key),
)
const providerConnected = computed(() =>
  store.providers.some((provider) => provider.configured),
)
const saveLabel = computed(() => {
  if (tab.value === 'providers') return '保存 API Key'
  if (tab.value === 'template') return '保存模板'
  return '保存更改'
})

function tabState(key: TabKey): { label: string; tone: TabTone } {
  const s = store.settings
  if (key === 'providers') {
    return s?.has_tmdb_key
      ? { label: '已配置', tone: 'ok' }
      : { label: '未配置', tone: 'warn' }
  }
  if (key === 'openlist') {
    return instances.value.length
      ? { label: `${instances.value.length} 个实例`, tone: 'ok' }
      : { label: '未配置', tone: 'warn' }
  }
  if (key === 'template') {
    return { label: '模板', tone: 'idle' }
  }
  if (key === 'strm') {
    return { label: strmMode.value.toUpperCase(), tone: 'idle' }
  }
  if (key === 'jellyfin') {
    return s?.jellyfin_url && s?.has_jellyfin_key
      ? { label: '已配置', tone: 'ok' }
      : { label: '未配置', tone: 'warn' }
  }
  return { label: '高级', tone: 'idle' }
}

const readyCount = computed(
  () => tabs.filter((item) => tabState(item.key).tone === 'ok').length,
)
const readyPercent = computed(() => Math.round((readyCount.value / tabs.length) * 100))

const dirty = computed(() => {
  const s = store.settings
  if (!s) return false
  if (tab.value === 'providers') return tmdbKey.value.trim().length > 0
  if (tab.value === 'template') return templateDraft.value !== s.rename_template
  if (tab.value === 'strm') {
    if (strmTemplate.value.trim() !== s.strm_url_template) return true
    if (strmMode.value !== s.strm_output_mode) return true
    if (strmTargetDir.value.trim() !== s.strm_target_dir) return true
    return ruleKey(strmRules.value) !== ruleKey(s.strm_rules)
  }
  if (tab.value === 'jellyfin') {
    return (
      jellyfinUrl.value.trim() !== s.jellyfin_url || jellyfinKey.value.trim().length > 0
    )
  }
  if (tab.value === 'general') {
    const paths = allowedPaths.value
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
    if (paths.join('\n') !== s.allowed_paths.join('\n')) return true
    return (
      (Number(concurrency.value) || 1) !== s.openlist_concurrency ||
      (Number(timeout.value) || 30) !== s.openlist_timeout ||
      (Number(retry.value) || 0) !== s.openlist_retry
    )
  }
  return false
})

const pathCount = computed(
  () =>
    allowedPaths.value
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean).length,
)

function ruleKey(rules: StrmRule[]) {
  return rules
    .map((rule) => `${rule.source}|${rule.target_type}|${rule.target_id ?? ''}|${rule.target_dir}`)
    .join('\n')
}

function moveTab(delta: number) {
  const index = tabs.findIndex((item) => item.key === tab.value)
  const next = (index + delta + tabs.length) % tabs.length
  tab.value = tabs[next].key
}

function initial(name: string) {
  return name.trim().slice(0, 2).toUpperCase() || 'OL'
}

const version = __APP_VERSION__

const slate = computed<SlateRow[]>(() => [
  {
    label: 'TMDB',
    value: store.settings?.has_tmdb_key ? 'CONFIGURED' : 'MISSING',
    tone: store.settings?.has_tmdb_key ? 'green' : 'amber',
  },
  { label: 'OPENLIST', value: `${instances.value.length} INSTANCES` },
  {
    label: 'JELLYFIN',
    value:
      store.settings?.jellyfin_url && store.settings?.has_jellyfin_key
        ? 'CONFIGURED'
        : 'MISSING',
    tone:
      store.settings?.jellyfin_url && store.settings?.has_jellyfin_key ? 'green' : 'amber',
  },
  { label: 'VERSION', value: `v${version}` },
])

function hydrate(settings: Settings) {
  if (hydrated.value) return
  templateDraft.value = settings.rename_template
  allowedPaths.value = settings.allowed_paths.join('\n')
  concurrency.value = settings.openlist_concurrency
  timeout.value = settings.openlist_timeout
  retry.value = settings.openlist_retry
  strmTemplate.value = settings.strm_url_template
  strmMode.value = settings.strm_output_mode
  strmTargetDir.value = settings.strm_target_dir
  strmRules.value = settings.strm_rules.map((rule) => ({ ...rule }))
  jellyfinUrl.value = settings.jellyfin_url
  hydrated.value = true
}

watch(() => store.settings, (value) => {
  if (value) hydrate(value)
}, { immediate: true })

function messageOf(err: unknown) {
  return err instanceof Error ? err.message : '请求失败'
}

async function saveSettings(payload: Record<string, unknown>, text: string) {
  saving.value = true
  error.value = ''
  try {
    store.settings = await api.updateSettings(payload)
    toast.success(text)
    return true
  } catch (err) {
    error.value = messageOf(err)
    return false
  } finally {
    saving.value = false
  }
}

async function saveTmdbKey() {
  if (!tmdbKey.value.trim()) {
    error.value = '请输入 TMDB API Key'
    return
  }
  if (await saveSettings({ tmdb_api_key: tmdbKey.value.trim() }, 'API Key 已保存')) {
    tmdbKey.value = ''
    await store.refreshProviderState()
  }
}

async function loadInstances() {
  instancesLoading.value = true
  try {
    instances.value = await api.getOpenListInstances()
    error.value = ''
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    instancesLoading.value = false
  }
}

async function refreshSources() {
  try {
    store.datasources = await api.getDataSources()
  } catch {
    /* 忽略数据源刷新失败 */
  }
}

function openCreate() {
  editing.value = null
  form.value = {
    name: '',
    base_url: '',
    username: '',
    password: '',
    mount_path: '/',
    timeout: timeout.value,
    concurrency: concurrency.value,
  }
  error.value = ''
  formOpen.value = true
}

function openEdit(instance: OpenListInstance) {
  editing.value = instance
  form.value = {
    name: instance.name,
    base_url: instance.base_url,
    username: instance.username,
    password: '',
    mount_path: instance.mount_path || '/',
    timeout: instance.timeout,
    concurrency: instance.concurrency,
  }
  error.value = ''
  formOpen.value = true
}

async function saveInstance() {
  if (!form.value.name.trim() || !form.value.base_url.trim()) {
    error.value = '实例名称与服务地址不能为空'
    return
  }
  const payload: Record<string, unknown> = {
    name: form.value.name.trim(),
    base_url: form.value.base_url.trim(),
    username: form.value.username.trim(),
    mount_path: form.value.mount_path.trim() || '/',
    timeout: Number(form.value.timeout) || 30,
    concurrency: Number(form.value.concurrency) || 3,
  }
  if (form.value.password) payload.password = form.value.password

  formSaving.value = true
  error.value = ''
  try {
    if (editing.value) await api.updateOpenList(editing.value.id, payload)
    else await api.createOpenList(payload)
    formOpen.value = false
    toast.success(editing.value ? '实例已更新' : '实例已创建')
    await loadInstances()
    await refreshSources()
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    formSaving.value = false
  }
}

async function testConnection(instance: OpenListInstance) {
  testingId.value = instance.id
  try {
    const result = await api.testOpenList(instance.id)
    testState.value = { ...testState.value, [instance.id]: result }
    if (result.ok) toast.success(result.message || '连接成功')
    else toast.error(result.message || '连接失败')
  } catch (err) {
    const message = messageOf(err)
    testState.value = { ...testState.value, [instance.id]: { ok: false, message } }
    toast.error(message)
  } finally {
    testingId.value = null
  }
}

async function removeInstance() {
  if (!deleteTarget.value) return
  deleting.value = true
  error.value = ''
  try {
    await api.deleteOpenList(deleteTarget.value.id)
    toast.success('实例已删除')
    deleteTarget.value = null
    await loadInstances()
    await refreshSources()
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    deleting.value = false
  }
}

async function saveTemplate() {
  if (!templateDraft.value.trim()) {
    error.value = '命名模板不能为空'
    return
  }
  await saveSettings({ rename_template: templateDraft.value }, '命名模板已保存')
}

function addStrmRule() {
  strmRules.value.push({
    source: '',
    target_type: 'local',
    target_id: null,
    target_dir: '',
  })
}

function setStrmMode(value: string) {
  if (value === 'alongside' || value === 'library' || value === 'mirror') {
    strmMode.value = value
  }
}

function removeStrmRule(index: number) {
  strmRules.value.splice(index, 1)
}

async function saveStrm() {
  if (!strmTemplate.value.trim()) {
    error.value = 'STRM URL 模板不能为空'
    return
  }
  for (const rule of strmRules.value) {
    if (!rule.source.trim().startsWith('/')) {
      error.value = '规则的源路径必须以 / 开头'
      return
    }
    if (!rule.target_dir.trim().startsWith('/')) {
      error.value = '规则的目标目录必须以 / 开头'
      return
    }
    if (rule.target_type === 'openlist' && !rule.target_id) {
      error.value = '请为 OpenList 目标规则选择实例'
      return
    }
  }
  await saveSettings(
    {
      strm_url_template: strmTemplate.value.trim(),
      strm_output_mode: strmMode.value,
      strm_target_dir: strmTargetDir.value.trim(),
      strm_rules: strmRules.value.map((rule) => ({
        ...rule,
        source: rule.source.trim(),
        target_dir: rule.target_dir.trim(),
      })),
    },
    'STRM 设置已保存',
  )
}

async function saveJellyfin() {
  const payload: Record<string, unknown> = { jellyfin_url: jellyfinUrl.value.trim() }
  if (jellyfinKey.value.trim()) payload.jellyfin_api_key = jellyfinKey.value.trim()
  if (await saveSettings(payload, 'Jellyfin 设置已保存')) {
    jellyfinKey.value = ''
  }
}

async function testJellyfin() {
  jellyfinTesting.value = true
  error.value = ''
  try {
    const result = await api.testJellyfin()
    if (result.ok) toast.success(result.message || '连接成功')
    else toast.error(result.message || '连接失败')
  } catch (err) {
    toast.error(messageOf(err))
  } finally {
    jellyfinTesting.value = false
  }
}

async function saveGeneral() {
  const paths = allowedPaths.value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  await saveSettings(
    {
      allowed_paths: paths,
      openlist_concurrency: Number(concurrency.value) || 1,
      openlist_timeout: Number(timeout.value) || 30,
      openlist_retry: Number(retry.value) || 0,
    },
    '通用设置已保存',
  )
}

async function saveCurrent() {
  if (tab.value === 'providers') await saveTmdbKey()
  else if (tab.value === 'template') await saveTemplate()
  else if (tab.value === 'strm') await saveStrm()
  else if (tab.value === 'jellyfin') await saveJellyfin()
  else if (tab.value === 'general') await saveGeneral()
}

function resetCurrent() {
  const settings = store.settings
  if (!settings) return
  error.value = ''
  if (tab.value === 'providers') {
    tmdbKey.value = ''
  } else if (tab.value === 'template') {
    templateDraft.value = settings.rename_template
  } else if (tab.value === 'strm') {
    strmTemplate.value = settings.strm_url_template
    strmMode.value = settings.strm_output_mode
    strmTargetDir.value = settings.strm_target_dir
    strmRules.value = settings.strm_rules.map((rule) => ({ ...rule }))
  } else if (tab.value === 'jellyfin') {
    jellyfinUrl.value = settings.jellyfin_url
    jellyfinKey.value = ''
  } else if (tab.value === 'general') {
    allowedPaths.value = settings.allowed_paths.join('\n')
    concurrency.value = settings.openlist_concurrency
    timeout.value = settings.openlist_timeout
    retry.value = settings.openlist_retry
  }
}

watch(tab, () => {
  error.value = ''
})

onMounted(loadInstances)
</script>

<template>
  <div>
    <PageHeader
      ghost="07"
      kicker="CONFIG · SETTINGS"
      title="设置"
      title-en="SETTINGS"
      description="媒体源、OpenList 实例、命名模板、STRM 与 Jellyfin 集成配置。"
      :slate="slate"
    />

    <ErrorBanner v-if="error" class="mb-4" :message="error" />

    <div class="settings-grid">
      <nav
        class="panel settings-tabs"
        role="tablist"
        aria-orientation="vertical"
        aria-label="设置分组"
        @keydown.down.prevent="moveTab(1)"
        @keydown.right.prevent="moveTab(1)"
        @keydown.up.prevent="moveTab(-1)"
        @keydown.left.prevent="moveTab(-1)"
      >
        <div class="tabs-head">
          <span>CONFIG MAP</span>
          <b>{{ readyCount }}/{{ tabs.length }}</b>
        </div>
        <button
          v-for="item in tabs"
          :key="item.key"
          :id="`set-tab-${item.key}`"
          class="stab"
          :class="{ on: tab === item.key }"
          role="tab"
          aria-controls="set-panel"
          :aria-selected="tab === item.key"
          :tabindex="tab === item.key ? 0 : -1"
          @click="tab = item.key"
        >
          <span class="stab-ic"><AppIcon :name="item.icon" :size="15" /></span>
          <span class="stab-body">
            <b>{{ item.label }}</b>
            <small>{{ item.en }}</small>
          </span>
          <span
            class="stab-dot"
            :class="tabState(item.key).tone"
            :title="tabState(item.key).label"
          />
        </button>
        <div class="tabs-foot">
          <div class="tabs-foot-row"><span>SETUP</span><b>{{ readyPercent }}%</b></div>
          <div class="tabs-meter"><i :style="{ width: `${readyPercent}%` }" /></div>
        </div>
      </nav>

      <div class="min-w-0">
        <section
          id="set-panel"
          class="panel set-section"
          role="tabpanel"
          :aria-labelledby="`set-tab-${tab}`"
        >
          <header class="set-head">
            <span class="set-index">{{ activeIndex }}</span>
            <span class="set-ic"><AppIcon :name="activeTab.icon" :size="17" /></span>
            <div class="set-heading">
              <div class="set-kicker">{{ activeTab.en }}</div>
              <h3>{{ activeTab.label }}</h3>
              <p>{{ activeTab.desc }}</p>
            </div>
            <div class="set-side">
              <StatusTag
                v-if="tab === 'providers'"
                :status="providerConnected ? 'success' : 'pending'"
                :text="providerConnected ? 'CONNECTED' : 'MISSING'"
              />
              <StatusTag
                v-else-if="tab === 'openlist'"
                status="pending"
                :text="`${instances.length} 个实例`"
              />
              <span v-else-if="tab === 'strm'" class="mode-pill amber">
                {{ strmMode.toUpperCase() }}
              </span>
              <StatusTag
                v-else-if="tab === 'jellyfin'"
                :status="jellyfinConfigured ? 'success' : 'pending'"
                :text="jellyfinConfigured ? 'CONNECTED' : 'MISSING'"
              />
              <button v-if="tab === 'openlist'" class="btn btn-sm btn-amber" @click="openCreate">
                <AppIcon name="plus" :size="13" />
                新增实例
              </button>
            </div>
          </header>

          <Transition name="fade" mode="out-in">
            <div :key="tab" class="set-body">
              <template v-if="tab === 'providers'">
                <div class="set-block">
                  <div class="block-head">
                    <h4>可用媒体源</h4>
                    <span class="block-note">PROVIDER REGISTRY</span>
                  </div>
                  <div class="provider-list">
                    <div v-for="provider in store.providers" :key="provider.name" class="instance">
                      <span class="cloud-ic"><AppIcon name="sparkles" :size="15" /></span>
                      <span class="body">
                        <b>{{ provider.label }}</b>
                        <small>
                          {{ provider.configured ? '已连接 · 可用于搜索与匹配' : '尚未配置 API Key' }}
                        </small>
                      </span>
                      <StatusTag
                        :status="provider.configured ? 'success' : 'pending'"
                        :text="provider.configured ? '已配置' : '未配置'"
                      />
                    </div>
                    <div v-if="store.providers.length === 0" class="blank-note">暂无可用媒体源</div>
                  </div>
                </div>

                <div class="cred-card">
                  <div class="cred-head">
                    <span class="cred-ic"><AppIcon name="sparkles" :size="15" /></span>
                    <div class="cred-title">
                      <b>TMDB API Key</b>
                      <small>THE MOVIE DATABASE · v3</small>
                    </div>
                    <StatusTag
                      :status="store.settings?.has_tmdb_key ? 'success' : 'pending'"
                      :text="store.settings?.has_tmdb_key ? '已保存' : '未保存'"
                    />
                    <a
                      class="cred-link"
                      href="https://www.themoviedb.org/settings/api"
                      target="_blank"
                      rel="noreferrer"
                    >
                      获取 Key
                      <AppIcon name="external" :size="11" />
                    </a>
                  </div>
                  <div class="field mt-3">
                    <label>API Key <span>TMDB v3 · 服务端存储</span></label>
                    <div class="input-group">
                      <AppIcon name="eye" :size="14" />
                      <input
                        v-model="tmdbKey"
                        type="password"
                        :placeholder="
                          store.settings?.has_tmdb_key
                            ? '已保存，输入新 Key 可覆盖'
                            : '填写 TMDB API Key'
                        "
                        autocomplete="off"
                      />
                    </div>
                  </div>
                  <p class="hint-line">Key 仅保存在服务端，前端不会回显已保存的内容。</p>
                </div>
              </template>

              <template v-else-if="tab === 'openlist'">
                <div class="set-block">
                  <div class="block-head">
                    <h4>实例列表</h4>
                    <div class="block-actions">
                      <span class="block-note">
                        {{ store.datasources.filter((item) => item.type === 'openlist').length }} 个已接入扫描
                      </span>
                      <button
                        class="btn btn-xs btn-ghost"
                        :disabled="instancesLoading"
                        @click="loadInstances"
                      >
                        <AppIcon name="refresh" :size="12" :spin="instancesLoading" />
                        刷新
                      </button>
                    </div>
                  </div>

                  <div v-if="instancesLoading" class="ol-grid">
                    <div v-for="index in 2" :key="index" class="ol-card ol-skeleton">
                      <span class="h-8 w-8 animate-pulse rounded-lg bg-[var(--surface-2)]" />
                      <span class="h-3 flex-1 animate-pulse rounded bg-[var(--surface-2)]" />
                    </div>
                  </div>

                  <EmptyState
                    v-else-if="instances.length === 0"
                    icon="cloud"
                    title="还没有 OpenList 实例"
                    description="添加实例后即可在扫描页选择云盘目录。"
                  >
                    <button class="btn btn-amber" @click="openCreate">
                      <AppIcon name="plus" :size="14" />
                      新增实例
                    </button>
                  </EmptyState>

                  <div v-else class="ol-grid">
                    <article v-for="instance in instances" :key="instance.id" class="ol-card">
                      <header>
                        <span class="ol-mark">{{ initial(instance.name) }}</span>
                        <span class="ol-title">
                          <b>{{ instance.name }}</b>
                          <small>{{ instance.base_url }}</small>
                        </span>
                        <StatusTag
                          :status="testState[instance.id]?.ok ? 'success' : 'pending'"
                          :text="
                            testState[instance.id]
                              ? testState[instance.id].ok
                                ? '已连接'
                                : '连接失败'
                              : '未验证'
                          "
                        />
                      </header>

                      <div class="ol-meta">
                        <span><em>USER</em>{{ instance.username || '—' }}</span>
                        <span><em>TIMEOUT</em>{{ instance.timeout }}s</span>
                        <span><em>CONCURRENCY</em>{{ instance.concurrency }}</span>
                        <span><em>MOUNT</em>{{ instance.mount_path || '/' }}</span>
                      </div>

                      <p
                        v-if="testState[instance.id]"
                        class="ol-test"
                        :class="testState[instance.id].ok ? 'ok' : 'bad'"
                      >
                        <AppIcon
                          :name="testState[instance.id].ok ? 'check-circle' : 'alert'"
                          :size="12"
                        />
                        {{ testState[instance.id].message }}
                      </p>

                      <footer class="ol-foot">
                        <button
                          class="btn btn-xs"
                          :disabled="testingId === instance.id"
                          @click="testConnection(instance)"
                        >
                          <AppIcon name="refresh" :size="12" :spin="testingId === instance.id" />
                          测试连接
                        </button>
                        <button class="btn btn-xs btn-ghost" @click="openEdit(instance)">编辑</button>
                        <button class="btn btn-xs btn-danger" @click="deleteTarget = instance">
                          删除
                        </button>
                      </footer>
                    </article>
                  </div>

                  <div class="warn-note mt-3">
                    <AppIcon name="alert" :size="14" />
                    <span>删除实例前需确认无任务引用；密码字段仅提交，不回显。</span>
                  </div>
                </div>
              </template>

              <template v-else-if="tab === 'template'">
                <div class="tpl-grid">
                  <div class="set-block">
                    <div class="block-head">
                      <h4>模板编辑器</h4>
                      <span class="block-note">RENAME PATTERN</span>
                    </div>
                    <TemplateEditor v-model="templateDraft" :sample="sample" />
                    <p class="hint-line mt-2">
                      数字变量支持 {season:02d} 形式的补零，点击变量即可插入到光标位置。
                    </p>
                  </div>

                  <aside class="var-panel">
                    <div class="block-head">
                      <h4>变量参考</h4>
                      <span class="block-note">TOKENS</span>
                    </div>
                    <div class="var-list">
                      <div
                        v-for="row in [
                          { key: '{title}', text: '剧名', demo: 'Breaking Bad' },
                          { key: '{year}', text: '年份', demo: '2008' },
                          { key: '{season:02d}', text: '季（两位）', demo: '01' },
                          { key: '{episode:02d}', text: '集（两位）', demo: '03' },
                          { key: '{episode_title}', text: '集标题', demo: 'Pilot' },
                          { key: '{resolution}', text: '分辨率', demo: '1080p' },
                          { key: '{codec}', text: '视频编码', demo: 'x264' },
                          { key: '{release_group}', text: '发布组', demo: 'DEMAND' },
                        ]"
                        :key="row.key"
                        class="var-row"
                      >
                        <code>{{ row.key }}</code>
                        <span>{{ row.text }}</span>
                        <em>{{ row.demo }}</em>
                      </div>
                    </div>
                  </aside>
                </div>
              </template>

              <template v-else-if="tab === 'strm'">
                <div class="set-block">
                  <div class="block-head">
                    <h4>链接模板</h4>
                    <span class="block-note">URL TEMPLATE</span>
                  </div>
                  <div class="field">
                    <label>
                      播放地址
                      <span>{base_url} · {path} · {raw_path} · {filename}</span>
                    </label>
                    <input
                      v-model="strmTemplate"
                      class="input mono"
                      spellcheck="false"
                      placeholder="{base_url}/d/{path}"
                    />
                    <p class="hint-line">
                      变量：{base_url} 数据源地址、{path} 视频路径（URL 编码）、{raw_path} 原始路径、{filename} 文件名。
                    </p>
                  </div>
                </div>

                <div class="set-block">
                  <div class="block-head">
                    <h4>输出方式</h4>
                    <span class="block-note">OUTPUT MODE</span>
                  </div>
                  <div class="mode-grid">
                    <button
                      v-for="(mode, index) in [
                        { value: 'alongside', title: 'ALONGSIDE', desc: '与视频同目录生成 STRM' },
                        { value: 'library', title: 'LIBRARY', desc: '输出到统一媒体库目录' },
                        { value: 'mirror', title: 'MIRROR', desc: '按源路径镜像到目标目录' },
                      ]"
                      :key="mode.value"
                      type="button"
                      class="mode"
                      :class="{ on: strmMode === mode.value }"
                      @click="setStrmMode(mode.value)"
                    >
                      <span class="mode-top">
                        <span class="mode-idx">0{{ index + 1 }}</span>
                        <i class="mode-radio" />
                      </span>
                      <b>{{ mode.title }}</b>
                      <small>{{ mode.desc }}</small>
                    </button>
                  </div>

                  <div class="field mt-3">
                    <label>目标目录 <span>TARGET DIR · 非 ALONGSIDE 模式生效</span></label>
                    <input
                      v-model="strmTargetDir"
                      class="input mono"
                      :disabled="strmMode === 'alongside'"
                      placeholder="/data/media/strm"
                      spellcheck="false"
                    />
                  </div>
                  <p class="hint-line">
                    本地视频的 STRM 内容为视频绝对路径；OpenList 视频按上方 URL 模板生成。
                  </p>
                </div>

                <div class="set-block">
                  <div class="block-head">
                    <div>
                      <h4>路径映射规则</h4>
                      <p class="block-desc">
                        按源路径最长前缀匹配，命中后按相对目录结构写入目标位置，未命中时使用上方默认方式。
                      </p>
                    </div>
                    <button class="btn btn-xs btn-ghost" type="button" @click="addStrmRule">
                      <AppIcon name="plus" :size="12" />
                      新增规则
                    </button>
                  </div>

                  <div v-if="!strmRules.length" class="rule-empty">
                    <AppIcon name="filter" :size="15" />
                    <span>暂无规则，所有路径都将使用上方默认输出方式。</span>
                  </div>

                  <div v-else class="rule-list">
                    <div v-for="(rule, index) in strmRules" :key="index" class="rule-card">
                      <div class="rule-head">
                        <span class="rule-idx">RULE {{ String(index + 1).padStart(2, '0') }}</span>
                        <button
                          class="btn btn-xs btn-ghost text-danger"
                          type="button"
                          @click="removeStrmRule(index)"
                        >
                          <AppIcon name="trash" :size="12" />
                          删除
                        </button>
                      </div>
                      <div class="rule-fields">
                        <div class="field">
                          <label>源路径前缀 <span>SOURCE</span></label>
                          <input
                            v-model="rule.source"
                            class="input mono"
                            placeholder="/cloud/美剧"
                            spellcheck="false"
                          />
                        </div>
                        <span class="rule-arrow"><AppIcon name="arrow-right" :size="14" /></span>
                        <div class="field">
                          <label>目标类型 <span>TARGET</span></label>
                          <SelectMenu
                            v-model="rule.target_type"
                            class="h-9"
                            :options="[
                              { value: 'local', label: '本地目录' },
                              { value: 'openlist', label: 'OpenList' },
                            ]"
                          />
                          <SelectMenu
                            v-if="rule.target_type === 'openlist'"
                            v-model="rule.target_id"
                            class="mt-1.5 h-9"
                            :options="instances.map((i) => ({ value: i.id, label: i.name }))"
                            placeholder="选择实例"
                          />
                        </div>
                        <div class="field">
                          <label>目标目录 <span>DEST</span></label>
                          <input
                            v-model="rule.target_dir"
                            class="input mono"
                            placeholder="/strm/美剧"
                            spellcheck="false"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

              <template v-else-if="tab === 'jellyfin'">
                <div class="conn-card" :class="{ ok: jellyfinConfigured }">
                  <span class="conn-orb"><i /></span>
                  <span class="conn-copy">
                    <b>{{ jellyfinConfigured ? '已配置服务器' : '尚未配置服务器' }}</b>
                    <small>
                      {{ store.settings?.jellyfin_url || '填写下方服务器地址与 API Key' }}
                    </small>
                  </span>
                  <button
                    class="btn btn-sm"
                    :disabled="jellyfinTesting || !jellyfinConfigured"
                    title="使用已保存的配置测试连接"
                    @click="testJellyfin"
                  >
                    <AppIcon name="refresh" :size="13" :spin="jellyfinTesting" />
                    测试连接
                  </button>
                </div>

                <div class="set-block mt-4">
                  <div class="block-head">
                    <h4>服务器接入</h4>
                    <span class="block-note">CONNECTION</span>
                  </div>
                  <div class="form-row">
                    <div class="field">
                      <label>服务器地址 <span>BASE URL</span></label>
                      <input
                        v-model="jellyfinUrl"
                        class="input mono"
                        placeholder="http://192.168.1.10:8096"
                        spellcheck="false"
                      />
                    </div>
                    <div class="field">
                      <label>API Key <span>API KEY</span></label>
                      <div class="input-group">
                        <AppIcon name="eye" :size="14" />
                        <input
                          v-model="jellyfinKey"
                          type="password"
                          :placeholder="
                            store.settings?.has_jellyfin_key
                              ? '已保存，输入新 Key 可覆盖'
                              : '在 Jellyfin 控制台 → API 密钥中创建'
                          "
                          autocomplete="off"
                        />
                      </div>
                    </div>
                  </div>
                  <p class="hint-line mt-2">
                    配置后可在「刷新」步骤中刷新指定的媒体库；Key 仅保存在服务端。
                  </p>
                </div>
              </template>

              <template v-else>
                <div class="set-block">
                  <div class="block-head">
                    <h4>本地目录白名单</h4>
                    <span class="block-note">{{ pathCount }} 条路径</span>
                  </div>
                  <div class="field">
                    <label>允许扫描的目录 <span>ALLOWED PATHS · 每行一个</span></label>
                    <textarea
                      v-model="allowedPaths"
                      class="textarea"
                      rows="5"
                      placeholder="/data/media/tv"
                      spellcheck="false"
                    />
                    <p class="hint-line">扫描页的本地路径只能位于白名单目录之内。</p>
                  </div>
                </div>

                <div class="set-block">
                  <div class="block-head">
                    <h4>OpenList 请求参数</h4>
                    <span class="block-note">NETWORK</span>
                  </div>
                  <div class="num-grid">
                    <div class="num-card">
                      <span class="k">并发数 <em>CONCURRENCY</em></span>
                      <input
                        v-model.number="concurrency"
                        type="number"
                        min="1"
                        max="16"
                        class="input mono"
                      />
                      <span class="num-range">RANGE 1 – 16</span>
                    </div>
                    <div class="num-card">
                      <span class="k">请求超时 <em>TIMEOUT</em></span>
                      <input
                        v-model.number="timeout"
                        type="number"
                        min="5"
                        max="300"
                        class="input mono"
                      />
                      <span class="num-range">RANGE 5 – 300 秒</span>
                    </div>
                    <div class="num-card">
                      <span class="k">失败重试 <em>RETRY</em></span>
                      <input
                        v-model.number="retry"
                        type="number"
                        min="0"
                        max="5"
                        class="input mono"
                      />
                      <span class="num-range">RANGE 0 – 5 次</span>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </Transition>
        </section>

        <footer v-if="tab !== 'openlist'" class="save-bar" :class="{ dirty }">
          <span class="save-state"><i />{{ dirty ? '有未保存的更改' : '已与服务器同步' }}</span>
          <span class="save-tip">{{ dirty ? '保存后立即生效' : '修改任意选项以启用保存' }}</span>
          <span class="save-spacer" />
          <button class="btn btn-sm btn-ghost" :disabled="!dirty || saving" @click="resetCurrent">
            重置
          </button>
          <button class="btn btn-sm btn-amber" :disabled="!dirty || saving" @click="saveCurrent">
            <AppIcon v-if="saving" name="loader" :size="13" spin />
            {{ saving ? '保存中…' : saveLabel }}
          </button>
        </footer>
      </div>
    </div>

    <BaseModal
      :open="formOpen"
      :title="editing ? '编辑 OpenList 实例' : '新增 OpenList 实例'"
      :width="520"
      @close="formOpen = false"
    >
      <div class="grid gap-3 sm:grid-cols-2">
        <div class="sm:col-span-2">
          <label class="label">实例名称</label>
          <input v-model="form.name" class="input" placeholder="家庭云盘" />
        </div>
        <div class="sm:col-span-2">
          <label class="label">服务地址</label>
          <input v-model="form.base_url" class="input font-mono text-xs" placeholder="https://fox.oplist.org" spellcheck="false" />
        </div>
        <div class="sm:col-span-2">
          <label class="label">挂载路径</label>
          <input
            v-model="form.mount_path"
            class="input font-mono text-xs"
            placeholder="/媒体/剧集"
            spellcheck="false"
          />
          <p class="mt-1 text-[11px] text-faint">
            云盘浏览与扫描的默认根目录，留空默认 /。填写后将只能访问此目录及以下。
          </p>
        </div>
        <div>
          <label class="label">用户名</label>
          <input v-model="form.username" class="input" placeholder="admin" autocomplete="off" />
        </div>
        <div>
          <label class="label">密码</label>
          <input
            v-model="form.password"
            type="password"
            class="input"
            :placeholder="editing ? '留空表示不修改' : '••••••••'"
            autocomplete="new-password"
          />
        </div>
        <div>
          <label class="label">超时（秒）</label>
          <input v-model.number="form.timeout" type="number" min="5" max="300" class="input font-mono" />
        </div>
        <div>
          <label class="label">并发</label>
          <input v-model.number="form.concurrency" type="number" min="1" max="16" class="input font-mono" />
        </div>
      </div>
      <p class="mt-3 text-[11.5px] text-faint">保存后可在列表中测试连接。</p>

      <template #footer>
        <button class="btn btn-ghost" :disabled="formSaving" @click="formOpen = false">取消</button>
        <button class="btn btn-primary" :disabled="formSaving" @click="saveInstance">
          <AppIcon v-if="formSaving" name="loader" :size="14" spin />
          保存
        </button>
      </template>
    </BaseModal>

    <ConfirmDialog
      :open="Boolean(deleteTarget)"
      title="删除 OpenList 实例"
      :message="deleteTarget ? `确定删除「${deleteTarget.name}」？引用该实例的任务历史不会被删除，但后续扫描将不可用。` : ''"
      confirm-text="删除"
      danger
      :loading="deleting"
      @confirm="removeInstance"
      @cancel="deleteTarget = null"
    />
  </div>
</template>
