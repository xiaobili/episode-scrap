<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { api } from '@/api/client'
import AppIcon from '@/components/AppIcon.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import StatusTag from '@/components/StatusTag.vue'
import TemplateEditor from '@/components/TemplateEditor.vue'
import { useToast } from '@/composables/useToast'
import { useWorkflowStore } from '@/stores/workflow'
import type { OpenListInstance, Settings, StrmRule } from '@/types'

type TabKey = 'providers' | 'openlist' | 'template' | 'strm' | 'general'

const store = useWorkflowStore()
const toast = useToast()

const tab = ref<TabKey>('providers')
const tabs: { key: TabKey; label: string; icon: string }[] = [
  { key: 'providers', label: '媒体源', icon: 'sparkles' },
  { key: 'openlist', label: 'OpenList', icon: 'cloud' },
  { key: 'template', label: '命名模板', icon: 'rename' },
  { key: 'strm', label: 'STRM', icon: 'file' },
  { key: 'general', label: '通用', icon: 'settings' },
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
const hydrated = ref(false)

const selected = computed(() => tabs.find((item) => item.key === tab.value))

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

onMounted(loadInstances)
</script>

<template>
  <div>
    <header class="mb-5">
      <h1 class="text-2xl font-semibold leading-8 tracking-tight text-ink">设置</h1>
      <p class="mt-1 text-[13px] text-muted">配置媒体源、云盘实例与命名规则</p>
    </header>

    <ErrorBanner v-if="error" class="mb-4" :message="error" />

    <div class="grid items-start gap-5 lg:grid-cols-[190px_minmax(0,1fr)]">
      <nav class="panel flex gap-1 overflow-x-auto p-1.5 lg:flex-col lg:overflow-visible">
        <button
          v-for="item in tabs"
          :key="item.key"
          class="flex h-9 flex-none items-center gap-2 whitespace-nowrap rounded px-2.5 text-[13px] transition lg:w-full"
          :class="
            tab === item.key
              ? 'bg-[var(--accent-soft)] font-medium text-ink'
              : 'text-muted hover:bg-[var(--bg-elevated)] hover:text-ink'
          "
          @click="tab = item.key"
        >
          <AppIcon :name="item.icon" :size="15" class="opacity-80" />
          {{ item.label }}
        </button>
      </nav>

      <div class="min-w-0">
        <section v-if="tab === 'providers'" class="panel p-4 md:p-5">
          <h2 class="text-lg font-semibold text-ink">媒体源</h2>
          <p class="mt-1 text-xs text-muted">刮削与季集信息依赖媒体源 API。</p>

          <div class="mt-4 divide-y divide-line rounded-lg border border-line">
            <div
              v-for="provider in store.providers"
              :key="provider.name"
              class="flex flex-wrap items-center gap-3 px-3.5 py-3"
            >
              <span class="flex h-8 w-8 flex-none items-center justify-center rounded-md bg-[var(--bg-elevated)] text-accent">
                <AppIcon name="sparkles" :size="15" />
              </span>
              <div class="min-w-0 flex-1">
                <p class="text-[13px] font-medium text-ink">{{ provider.label }}</p>
                <p class="text-[11.5px] text-faint">
                  {{ provider.configured ? '已配置，可用于搜索与匹配' : '未配置 API Key' }}
                </p>
              </div>
              <StatusTag :status="provider.configured ? 'success' : 'pending'" :text="provider.configured ? '已配置' : '未配置'" />
            </div>

            <div v-if="store.providers.length === 0" class="px-3.5 py-6 text-center text-xs text-faint">
              暂无可用媒体源
            </div>
          </div>

          <div class="mt-4">
            <label class="label">TMDB API Key</label>
            <div class="flex gap-2">
              <input
                v-model="tmdbKey"
                type="password"
                class="input font-mono text-xs"
                :placeholder="
                  store.settings?.has_tmdb_key ? '已保存，输入新 Key 可覆盖' : '填写 TMDB API Key'
                "
                autocomplete="off"
              />
              <button class="btn btn-primary flex-none" :disabled="saving" @click="saveTmdbKey">
                保存
              </button>
            </div>
            <p class="mt-1.5 text-[11.5px] text-faint">
              Key 仅保存在服务端，前端不会回显已保存的内容。
            </p>
          </div>
        </section>

        <section v-else-if="tab === 'openlist'" class="panel p-4 md:p-5">
          <div class="flex flex-wrap items-center gap-2">
            <div class="min-w-0 flex-1">
              <h2 class="text-lg font-semibold text-ink">OpenList 数据源</h2>
              <p class="mt-1 text-xs text-muted">管理云盘实例，扫描与重命名将通过这些实例执行。</p>
            </div>
            <button class="btn btn-primary" @click="openCreate">
              <AppIcon name="plus" :size="14" />
              新增实例
            </button>
          </div>

          <div v-if="instancesLoading" class="mt-4 space-y-2">
            <div v-for="index in 2" :key="index" class="h-[86px] animate-pulse rounded-lg border border-line bg-[var(--bg-elevated)]" />
          </div>

          <div v-else-if="instances.length === 0" class="mt-4 rounded-lg border border-dashed border-line-strong">
            <EmptyState
              icon="cloud"
              title="还没有 OpenList 实例"
              description="添加实例后即可在扫描页选择云盘目录。"
            >
              <button class="btn btn-primary" @click="openCreate">
                <AppIcon name="plus" :size="14" />
                新增实例
              </button>
            </EmptyState>
          </div>

          <div v-else class="mt-4 grid gap-2.5 xl:grid-cols-2">
            <div
              v-for="instance in instances"
              :key="instance.id"
              class="rounded-lg border border-line bg-base/40 px-3.5 py-3"
            >
              <div class="flex items-start gap-2">
                <div class="min-w-0 flex-1">
                  <p class="truncate text-[13px] font-medium text-ink">{{ instance.name }}</p>
                  <p class="mt-0.5 truncate font-mono text-[11.5px] text-muted">
                    {{ instance.base_url }}
                  </p>
                  <p class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-faint">
                    <span>用户 {{ instance.username || '—' }}</span>
                    <span>超时 {{ instance.timeout }}s</span>
                    <span>并发 {{ instance.concurrency }}</span>
                  </p>
                </div>
                <StatusTag :status="testState[instance.id]?.ok ? 'success' : 'pending'" :text="testState[instance.id] ? (testState[instance.id].ok ? '已连接' : '连接失败') : '未验证'" />
              </div>

              <p
                v-if="testState[instance.id] && !testState[instance.id].ok"
                class="mt-1.5 break-words text-[11px] text-danger"
              >
                {{ testState[instance.id].message }}
              </p>

              <div class="mt-2.5 flex items-center gap-1.5 border-t border-line pt-2.5">
                <button
                  class="btn btn-xs"
                  :disabled="testingId === instance.id"
                  @click="testConnection(instance)"
                >
                  <AppIcon name="refresh" :size="12" :spin="testingId === instance.id" />
                  测试连接
                </button>
                <button class="btn btn-xs btn-ghost" @click="openEdit(instance)">编辑</button>
                <button class="btn btn-xs btn-danger ml-auto" @click="deleteTarget = instance">
                  删除
                </button>
              </div>
            </div>
          </div>
        </section>

        <section v-else-if="tab === 'template'" class="panel p-4 md:p-5">
          <div class="flex flex-wrap items-start gap-2">
            <div class="min-w-0 flex-1">
              <h2 class="text-lg font-semibold text-ink">命名模板</h2>
              <p class="mt-1 text-xs text-muted">
                用于生成最终文件名，数字变量支持 {season:02d} 形式的补零。
              </p>
            </div>
            <button class="btn btn-primary" :disabled="saving" @click="saveTemplate">保存模板</button>
          </div>

          <div class="mt-4">
            <TemplateEditor v-model="templateDraft" :sample="sample" />
          </div>

          <div class="mt-4 overflow-hidden rounded-lg border border-line">
            <table class="w-full border-collapse text-xs">
              <thead class="bg-[var(--bg-elevated)] text-left text-faint">
                <tr>
                  <th class="h-9 px-3 font-medium">变量</th>
                  <th class="h-9 px-3 font-medium">说明</th>
                  <th class="h-9 px-3 font-medium">示例</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-line/60">
                <tr v-for="row in [
                  { key: '{title}', text: '剧名', demo: 'Breaking Bad' },
                  { key: '{year}', text: '年份', demo: '2008' },
                  { key: '{season:02d}', text: '季（两位）', demo: '01' },
                  { key: '{episode:02d}', text: '集（两位）', demo: '03' },
                  { key: '{episode_title}', text: '集标题', demo: 'Pilot' },
                  { key: '{resolution}', text: '分辨率', demo: '1080p' },
                  { key: '{codec}', text: '视频编码', demo: 'x264' },
                  { key: '{release_group}', text: '发布组', demo: 'DEMAND' },
                ]" :key="row.key">
                  <td class="h-9 px-3 font-mono text-accent">{{ row.key }}</td>
                  <td class="h-9 px-3 text-muted">{{ row.text }}</td>
                  <td class="h-9 px-3 font-mono text-faint">{{ row.demo }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-else-if="tab === 'strm'" class="panel p-4 md:p-5">
          <div class="flex flex-wrap items-start gap-2">
            <div class="min-w-0 flex-1">
              <h2 class="text-lg font-semibold text-ink">STRM</h2>
              <p class="mt-1 text-xs text-muted">
                重命名时勾选「生成 STRM」，为每个视频生成指向媒体源的 .strm 文件。
              </p>
            </div>
            <button class="btn btn-primary" :disabled="saving" @click="saveStrm">保存设置</button>
          </div>

          <div class="mt-4">
            <label class="label">URL 模板</label>
            <input
              v-model="strmTemplate"
              class="input font-mono text-xs"
              spellcheck="false"
              placeholder="{base_url}/d/{path}"
            />
            <p class="mt-1.5 text-[11.5px] text-faint">
              变量：{base_url} 数据源地址、{path} 视频路径（URL 编码）、{raw_path} 原始路径、{filename} 文件名。
            </p>
          </div>

          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <div>
              <label class="label">输出方式</label>
              <select v-model="strmMode" class="select h-9">
                <option value="alongside">与视频同目录</option>
                <option value="library">本地媒体库（剧名 / Season）</option>
                <option value="mirror">独立目录镜像</option>
              </select>
            </div>
            <div>
              <label class="label">目标目录（绝对路径）</label>
              <input
                v-model="strmTargetDir"
                class="input font-mono text-xs"
                :disabled="strmMode === 'alongside'"
                placeholder="/data/media/strm"
                spellcheck="false"
              />
            </div>
          </div>
          <p class="mt-1.5 text-[11.5px] text-faint">
            本地视频的 STRM 内容为视频绝对路径；OpenList 视频按上方 URL 模板生成。
          </p>

          <div class="mt-5 border-t border-line pt-4">
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 class="text-sm font-semibold text-ink">路径映射规则</h3>
                <p class="mt-0.5 text-[11.5px] text-faint">
                  按源路径最长前缀匹配，命中后按相对目录结构写入目标位置（目录不存在会自动创建），未命中时使用上方默认方式。
                </p>
              </div>
              <button class="btn btn-xs btn-ghost" type="button" @click="addStrmRule">
                新增规则
              </button>
            </div>

            <div
              v-if="!strmRules.length"
              class="mt-3 rounded-lg border border-dashed border-line-strong px-3 py-4 text-center text-xs text-faint"
            >
              暂无规则
            </div>

            <div v-else class="mt-3 space-y-2">
              <div
                v-for="(rule, index) in strmRules"
                :key="index"
                class="grid gap-2 rounded-lg border border-line p-2.5 md:grid-cols-[1.2fr_0.9fr_1.2fr_auto]"
              >
                <div>
                  <label class="label">源路径前缀</label>
                  <input
                    v-model="rule.source"
                    class="input font-mono text-xs"
                    placeholder="/cloud/美剧"
                    spellcheck="false"
                  />
                </div>
                <div>
                  <label class="label">目标</label>
                  <select v-model="rule.target_type" class="select h-9">
                    <option value="local">本地目录</option>
                    <option value="openlist">OpenList</option>
                  </select>
                  <select
                    v-if="rule.target_type === 'openlist'"
                    v-model="rule.target_id"
                    class="select mt-1.5 h-9"
                  >
                    <option :value="null" disabled>选择实例</option>
                    <option v-for="instance in instances" :key="instance.id" :value="instance.id">
                      {{ instance.name }}
                    </option>
                  </select>
                </div>
                <div>
                  <label class="label">目标目录</label>
                  <input
                    v-model="rule.target_dir"
                    class="input font-mono text-xs"
                    placeholder="/strm/美剧"
                    spellcheck="false"
                  />
                </div>
                <button
                  class="btn btn-xs btn-ghost self-end text-danger"
                  type="button"
                  @click="removeStrmRule(index)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </section>

        <section v-else class="panel p-4 md:p-5">
          <h2 class="text-lg font-semibold text-ink">通用</h2>
          <p class="mt-1 text-xs text-muted">本地目录白名单与 OpenList 请求参数。</p>

          <div class="mt-4">
            <label class="label">允许访问的本地目录（每行一个绝对路径）</label>
            <textarea
              v-model="allowedPaths"
              class="textarea font-mono text-xs"
              rows="5"
              placeholder="/data/media/tv"
              spellcheck="false"
            />
            <p class="mt-1.5 text-[11.5px] text-faint">
              扫描页的本地路径只能位于白名单目录之内。
            </p>
          </div>

          <div class="mt-4 grid gap-3 sm:grid-cols-3">
            <div>
              <label class="label">OpenList 并发</label>
              <input v-model.number="concurrency" type="number" min="1" max="16" class="input font-mono" />
            </div>
            <div>
              <label class="label">请求超时（秒）</label>
              <input v-model.number="timeout" type="number" min="5" max="300" class="input font-mono" />
            </div>
            <div>
              <label class="label">失败重试次数</label>
              <input v-model.number="retry" type="number" min="0" max="5" class="input font-mono" />
            </div>
          </div>

          <div class="mt-5 flex justify-end">
            <button class="btn btn-primary" :disabled="saving" @click="saveGeneral">保存设置</button>
          </div>
        </section>

        <p class="mt-3 text-[11px] text-faint">
          当前分组 · <span class="text-muted">{{ selected?.label }}</span>
        </p>
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
