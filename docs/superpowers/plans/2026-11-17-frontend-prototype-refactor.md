# 前端按原型重构 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 subagent-driven-development（推荐）或 executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在不改变业务行为与 API 的前提下，把 `frontend/` 的视觉与布局重构为 `prototype/index.html` 的暖色暗房工作台。

**架构：** 以 `style.css` 的 Token + 组件类为唯一视觉来源，Tailwind 继续负责布局；AppShell 改为 Topbar + 编号 Rail；新增 5 个展示组件，其余共享组件只改模板与 class；7 个视图逐页替换标记，脚本逻辑保持不变。

**技术栈：** Vue 3.5、TypeScript strict、Vite 7、Tailwind CSS 4、Pinia、vue-router。

**规格：** `docs/superpowers/specs/2026-11-17-frontend-prototype-refactor-design.md`

## 全局约束

- 只保留深色主题：移除主题切换、`data-theme`、`prefers-color-scheme` 初始化与 localStorage 主题键。
- 不修改后端、数据库、API 契约与 WebSocket 协议。
- 不新增 npm 依赖；字体通过 `frontend/index.html` 的 Google Fonts 引入，失败时回退系统字体。
- 不引入原型中的示例假数据；无真实来源的数据显示 `—` 或整块省略。
- 保持现有组件的对外 props / emits 不变；仅在确有必要时新增可选 props。
- 所有命令在 `frontend/` 下运行：`npm run typecheck`、`npm run build`、`npm run dev`。
- 本仓库没有前端测试框架，因此每个任务的验证 = 类型检查 + 构建 + 针对该任务的浏览器检查。
- 不自动创建 git commit；完成与否由用户决定是否提交。

## 文件结构

```
frontend/index.html                         # 字体、移除 data-theme
frontend/vite.config.ts                     # 注入 __APP_VERSION__
frontend/src/env.d.ts                       # 新增：全局常量声明
frontend/src/main.ts                        # 移除主题初始化
frontend/src/App.vue                        # 新增环境氛围层
frontend/src/style.css                      # 重写：token + 组件类 + 动画
frontend/src/composables/useClock.ts        # 新增：24fps timecode
frontend/src/composables/useRecentSearches.ts # 新增：最近搜索
frontend/src/components/AppShell.vue        # 重写：Topbar + Rail
frontend/src/components/PageHeader.vue      # 新增
frontend/src/components/ui-types.ts         # 新增：SlateRow / StatItem / SegValue 等 UI 类型
frontend/src/components/StatStrip.vue       # 新增
frontend/src/components/ToggleSwitch.vue    # 新增
frontend/src/components/SegmentedControl.vue # 新增
frontend/src/components/ConfidenceGauge.vue # 新增
frontend/src/components/AppIcon.vue         # 补图标
frontend/src/components/BatchBar.vue        # 改样式 + chips
frontend/src/components/ToastHost.vue       # 改样式
frontend/src/components/{FileTable,Pager,StatusTag,ConfidenceBadge,TaskProgress,DiffText,TemplateEditor,EmptyState,ErrorBanner}.vue
                                            # 只改模板与 class
frontend/src/components/{BaseModal,BaseDrawer,ConfirmDialog,SelectMenu,DirectoryBrowser,PathPicker,DataSourceSwitch,ShowCard,EpisodeMapper}.vue
                                            # 只改模板与 class
frontend/src/views/ScanView.vue             # 扫描页
frontend/src/views/ParseView.vue            # 解析页
frontend/src/views/ScrapeView.vue           # 刮削页
frontend/src/views/RenameView.vue           # 重命名页
frontend/src/views/TasksView.vue            # 任务中心
frontend/src/views/RefreshView.vue          # 刷新媒体库
frontend/src/views/SettingsView.vue         # 设置
```

### 新增组件接口契约

`frontend/src/components/ui-types.ts`（`<script setup>` 不能直接导出类型，因此单独放一个类型文件）：

```ts
export type SlateTone = 'amber' | 'green' | 'red'
export interface SlateRow { label: string; value: string; tone?: SlateTone }
export interface StatItem { label: string; value: string | number; unit?: string; tone?: SlateTone }
export type SegValue = string | number
```

```ts
// PageHeader.vue
// props: ghost: string; kicker: string; title: string; titleEn?: string;
//        description?: string; slate?: SlateRow[]
// slot: #actions（渲染在标题/描述下方）；#slate 可选覆盖右侧场记板

// StatStrip.vue
// props: items: StatItem[]

// ToggleSwitch.vue
// props: modelValue: boolean; label?: string; size?: 'md' | 'sm'; disabled?: boolean
// emits: update:modelValue [boolean]

// SegmentedControl.vue
// props: modelValue: SegValue; options: { value: SegValue; label: string; disabled?: boolean }[];
//        size?: 'md' | 'sm'; ariaLabel?: string
// emits: update:modelValue [SegValue]

// ConfidenceGauge.vue
// props: value: number（0–100）

// composables/useClock.ts
export function useTimecode(fps = 24): Ref<string> // "HH:MM:SS:FF"

// composables/useRecentSearches.ts
export function useRecentSearches(max = 4): { items: Ref<string[]>; push: (query: string) => void }
```

---

## 审查重点（Review Focus）

1. **浅色主题残留**：移除 `data-theme` 后，仍走浅色分支或硬编码 `#fff` 背景的组件在暗色下不可读。期望：全站文本与边框在暗色可读，`grep -rn "data-theme\\|prefers-color-scheme\\|episode-scrap-theme" frontend/src` 无结果。
2. **原型全局选择器污染**：原型的 `table`、`thead th`、`tbody td`、`h1`、`input` 规则若不加作用域，会影响 `SelectMenu` 浮层、弹窗与目录浏览。期望：这些规则都限定在 `.panel table` 或具体容器内。
3. **定时器与 WebSocket 泄漏**：timecode 定时器、任务 WebSocket 在切页后未清理。期望：离开页面后无继续更新、无控制台告警。
4. **localStorage 损坏**：最近搜索内容不是合法 JSON 时刮削页白屏。期望：解析失败时返回空数组并继续渲染。
5. **窄屏布局**：Rail 收为 76px 后 BatchBar 定位、刮削三栏堆叠、表格横向溢出。期望：1180 与 900 两档宽度无横向溢出、无重叠。
6. **任务详情内联后的实时状态**：从抽屉改为右栏后，WebSocket 连接状态、重试与轮询仍工作。期望：打开详情后进度实时变化，关闭后连接断开。

---

## 任务 1：设计 Token 与全局样式基础

**文件：**
- 修改：`frontend/index.html`
- 修改：`frontend/src/style.css`
- 修改：`frontend/src/main.ts`
- 修改：`frontend/src/App.vue`
- 修改：`frontend/vite.config.ts`
- 创建：`frontend/src/env.d.ts`
- 参考：`prototype/index.html:16-198`、`200-356`、`358-780`

- [ ] **步骤 1：在 `frontend/index.html` 引入字体并移除主题属性**

保留 `lang="zh-CN"`，删除 `<html data-theme="dark">` 中的 `data-theme`。在 `<head>` 中加入：

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300..800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap"
  rel="stylesheet"
/>
```

- [ ] **步骤 2：重写 `frontend/src/style.css` 的 Token**

用以下内容替换现有 `:root` 与 `[data-theme="light"]` 块，并保留旧变量名作为别名，避免逐个组件改类名：

```css
:root {
  --bg: #0a0807;
  --surface: #12100e;
  --surface-2: #191512;
  --elev: #211b17;
  --line: #292420;
  --line-2: #3d342d;
  --ink: #f3ebdf;
  --muted: #a2968a;
  --faint: #6c6258;
  --amber: #f0a02c;
  --amber-2: #ffc873;
  --amber-soft: rgba(240, 160, 44, 0.09);
  --green: #86c98d;
  --red: #e2654f;
  --blue: #7fa8cf;

  /* 旧变量别名：现有组件继续可用 */
  --bg-base: var(--bg);
  --bg-surface: var(--surface);
  --bg-elevated: var(--elev);
  --border: var(--line);
  --border-strong: var(--line-2);
  --text-primary: var(--ink);
  --text-secondary: var(--muted);
  --text-tertiary: var(--faint);
  --accent: var(--amber);
  --accent-soft: var(--amber-soft);
  --success: var(--green);
  --warning: var(--amber);
  --danger: var(--red);
  --info: var(--blue);
  --shadow-float: 0 8px 24px rgba(0, 0, 0, 0.32);

  --display: "Bricolage Grotesque", "PingFang SC", "Microsoft YaHei", sans-serif;
  --sans: "IBM Plex Sans", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --mono: "IBM Plex Mono", "PingFang SC", ui-monospace, monospace;
}
```

`@theme inline` 保持现有键位，新增 `--color-surface-2: var(--surface-2)`、`--color-amber-2: var(--amber-2)`，并把 `--font-sans/--font-mono` 指向 `--sans/--mono`。

- [ ] **步骤 3：移植全局氛围与基础组件类**

删除 `body::before` 网格背景与 `[data-theme="light"]` 块，加入 `.ambient`、`.scanlines`、`.grain`（照抄 `prototype/index.html:57-66`）。从原型移植并作用域化以下类：

- 基础：`body`、`::selection`、`:focus-visible`、滚动条、`.mono`、`.dim`、`.amber`、`.green`、`.red`
- 外壳：`.topbar`、`.brand`、`.reel`、`.brand-name`、`.brand-sub`、`.topbar-mid`、`.rec`、`.tc`、`.tc-sub`、`.mid-line`、`.source-pill`、`.topbar-actions`、`.icon-btn`、`.bubble`
- Rail：`.rail`、`.rail-label`、`.steps`、`.step`、`.step .num`、`.step b`、`.step small`、`.step .count`、`.step-ic`、`.step.on`、`.rail-sep`、`.rail-link`、`.rail-spacer`、`.rail-meta`、`.meta-row`、`.film-strip`、`.meta-note`、`.rail-nav`
- 主区：`main`、`.page-wrap`、`.page-head`、`.kicker`、`h1`（限定 `.page-head h1`）、`.h1-en`、`.head-desc`、`.ghost-num`、`.slate`、`.slate-stripe`、`.slate-body`、`.slate-row`
- 基础件：`.panel`、`.panel-head`、`.panel-title`、`.panel-side`、`.btn*`、`.tag*`、`.dot`、`.kbd`、`.legend`、`.hr`、`.seg`、`.seg-btn`、`.toggle`、`.bar`、`.input`、`.input-group`、`.textarea`、`.field`、`.hint-low`、`.stats`、`.stat`
- 页面：`.scan-controls`、`.controls-top`、`.controls-main`、`.scan-line`、`.table-toolbar`、`.toolbar-title`、`.toolbar-right`、`.search-mini`、`.file-cell`、`.file-sub`、`.table-foot`、`.pager`、`.batchbar`、`.batch-count`、`.batch-chips`、`.batch-actions`、`.split-parse`、`.tabs-line`、`.tab`、`.roll`、`.roll-item`、`.conf`、`.roll-foot`、`.shot-head`、`.shot-id`、`.raw-block`、`.detail-grid`、`.form-grid`、`.conf-card`、`.gauge*`、`.conf-*`、`.action-bar`、`.push`、`.scrape-grid`、`.pick-row`、`.show-grid`、`.show-card`、`.poster*`、`.show-info`、`.show-meta`、`.recent-searches`、`.map-*`、`.select-inline`、`.tpl-panel`、`.tpl-row`、`.tpl-input`、`.vars`、`.var-chip`、`.sample-line`、`.diff-old`、`.diff-new`、`.exec-bar`、`.exec-info`、`.exec-toggles`、`.tasks-grid`、`.task-type`、`.progress-cell`、`.progress-top`、`.detail-head`、`.detail-progress`、`.detail-meta`、`.task-items`、`.task-item`、`.detail-foot`、`.lib-grid`、`.lib-card`、`.log-panel`、`.log-list`、`.log-line`、`.settings-grid`、`.settings-tabs`、`.stab`、`.pane`、`.set-section`、`.set-title`、`.form-row`、`.instance`、`.mode-grid`、`.mode`、`.modal`、`.dialog*`、`.crumbs`、`.folder-grid`、`.folder`、`.summary*`、`.warn-note`、`.toasts`、`.toast`
- 动画：`rise`、`fadeIn`、`toastIn`、`pulse`、`spin`、`sweep`；保留现有 `.fade-*`、`.modal-*`、`.drawer-*` 过渡

作用域要求：把原型中的 `table`、`thead th`、`tbody td`、`h1`、`input` 改为 `.panel table`、`.panel thead th`、`.panel tbody td`、`.page-head h1`、`.input-group input` 等限定选择器。

兼容要求：保留现有 `.btn-primary`（与 `.btn-amber` 同款样式）、`.tag-success`/`.tag-warning`/`.tag-danger`/`.tag-accent`（映射到新的 `tag-ok`/`tag-warn`/`tag-bad`/`tag-amber` 配色）、`.divider`、`.scroll-thin`，避免现有组件失效。

- [ ] **步骤 4：`frontend/src/App.vue` 增加氛围层**

在 `AppShell` 之前加入：

```html
<div class="ambient" aria-hidden="true" />
<div class="scanlines" aria-hidden="true" />
<div class="grain" aria-hidden="true" />
```

- [ ] **步骤 5：`frontend/src/main.ts` 移除主题初始化**

删除 `storedTheme`、`theme`、`document.documentElement.dataset.theme` 与相关 localStorage/matchMedia 逻辑，保留 `createApp(App).use(createPinia()).use(router).mount('#app')`。

- [ ] **步骤 6：注入版本号**

`frontend/vite.config.ts` 中 `import pkg from './package.json'`，在配置对象加入：

```ts
define: { __APP_VERSION__: JSON.stringify(pkg.version) },
```

创建 `frontend/src/env.d.ts`：

```ts
declare const __APP_VERSION__: string
```

- [ ] **步骤 7：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：两条命令均通过。

运行 `npm run dev`，打开任一页面，确认背景为暖黑、强调色为琥珀、控制台无报错。

---

## 任务 2：AppShell 外壳重写与 timecode

**文件：**
- 修改：`frontend/src/components/AppShell.vue`
- 创建：`frontend/src/composables/useClock.ts`
- 参考：`prototype/index.html:817-905`

- [ ] **步骤 1：创建 `useClock.ts`**

```ts
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
```

- [ ] **步骤 2：重写 `AppShell.vue` 的脚本**

删除 `theme`、`toggleTheme`、`collapsed`、`toggleCollapsed`、`mobileOpen` 与移动端抽屉逻辑。保留 `store.init()`、`loadTaskBadge()`、`runningTasks` 与路由 watch。新增：

```ts
const timecode = useTimecode(24)
const sourceLabel = computed(() =>
  store.sourceType === 'openlist' ? 'OPENLIST' : 'LOCAL',
)
const sourceValue = computed(() => store.scanPath || '—')
const inQueue = computed(() =>
  store.parsedFiles.filter((f) => f.status !== 'matched' && f.status !== 'renamed').length,
)
const stepList = computed(() => [
  { name: 'scan', label: '扫描', en: 'INGEST', count: store.stepCounts.scan, num: '01' },
  { name: 'parse', label: '解析', en: 'PARSE', count: store.stepCounts.parse, num: '02' },
  { name: 'scrape', label: '刮削', en: 'SCRAPE', count: store.stepCounts.scrape, num: '03' },
  { name: 'rename', label: '重命名', en: 'RENAME', count: store.stepCounts.rename, num: '04' },
])
const highlights = computed(() => {
  const done = stepList.value.filter((s) => s.count > 0).length
  return Math.round((done / 4) * 12)
})
```

保留步骤禁用规则：`parse` 需 `scan > 0`，`scrape` 与 `rename` 需 `parse > 0`。

- [ ] **步骤 3：重写模板结构**

```html
<div class="app">
  <header class="topbar">…品牌 / 中段 / 任务与设置…</header>
  <aside class="rail">
    <div class="rail-label">WORKFLOW / 工作流</div>
    <nav class="steps">…四步…</nav>
    <div class="rail-sep">UTILITIES</div>
    <button class="rail-link" …>刷新媒体库</button>
    <div class="rail-spacer" />
    <div class="rail-meta">LIBRARY / IN QUEUE / film-strip / meta-note</div>
    <nav class="rail-nav">任务中心 / 设置</nav>
  </aside>
  <main>
    <div class="page-wrap">
      <router-view v-slot="{ Component }">
        <Transition name="fade" mode="out-in"><component :is="Component" /></Transition>
      </router-view>
    </div>
  </main>
</div>
```

Topbar 中段：`LIVE` 点、`{{ timecode }}`、`24 FPS · REC.709`、`.mid-line`、`.source-pill`（`SOURCE` + `sourceLabel + ' · ' + sourceValue`）。右侧任务按钮带 `runningTasks` 气泡，设置按钮。品牌使用 `.reel` + `AppIcon name="clap"`。

Rail 中每一步用 `<button class="step">`，内含 `.num`、`AppIcon`（`.step-ic`）、中文 + 英文小字、`.count`。METa 中 `LIBRARY = store.files.length`、`IN QUEUE = inQueue`，film-strip 渲染 12 个 `<i>`，前 `highlights` 个加 `style="background:…amber"`，整体 `aria-hidden="true"`。

- [ ] **步骤 4：响应式**

在 `style.css` 中加入原型 `727-751` 的 Rail 收起规则：`@media (max-width:1180px)` 时 `.app` 列宽 76px，隐藏 `.rail-label`、`.step b/small/.num`、`.rail-meta`、`.rail-link span`、`.step .count`，`.step-ic` 显示；`@media (max-width:900px)` 隐藏 `.topbar-mid`。

- [ ] **步骤 5：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：顶部 timecode 每秒变化；SOURCE 显示真实路径；Rail 四步可点击且禁用规则生效；缩到 1180px 以下 Rail 变为图标条；切走再回到页面时控制台无定时器相关告警。

---

## 任务 3：基础展示组件

**文件：**
- 创建：`frontend/src/components/ui-types.ts`
- 创建：`frontend/src/components/PageHeader.vue`
- 创建：`frontend/src/components/StatStrip.vue`
- 创建：`frontend/src/components/ToggleSwitch.vue`
- 创建：`frontend/src/components/SegmentedControl.vue`
- 创建：`frontend/src/components/ConfidenceGauge.vue`
- 修改：`frontend/src/components/AppIcon.vue`
- 修改：`frontend/src/components/BatchBar.vue`
- 修改：`frontend/src/components/ToastHost.vue`
- 参考：`prototype/index.html:176-198`、`246-258`、`279-290`、`343-356`、`406-427`、`669-717`

- [ ] **步骤 1：创建 `ui-types.ts`**

按上文「新增组件接口契约」写入 `SlateTone`、`SlateRow`、`StatItem`、`SegValue`。后续页面通过 `import type { SlateRow } from '@/components/ui-types'` 使用。

- [ ] **步骤 2：实现 `PageHeader.vue`**

按接口契约渲染：

```html
<header class="page-head">
  <span class="ghost-num">{{ ghost }}</span>
  <div class="head-copy">
    <div class="kicker">{{ kicker }}</div>
    <h1>{{ title }}<span class="h1-en">{{ titleEn }}</span></h1>
    <p v-if="description" class="head-desc">{{ description }}</p>
    <div v-if="$slots.actions" class="head-actions"><slot name="actions" /></div>
  </div>
  <div v-if="slate?.length" class="slate">
    <div class="slate-stripe" />
    <div class="slate-body">
      <div v-for="row in slate" :key="row.label" class="slate-row">
        <span>{{ row.label }}</span>
        <b :class="row.tone">{{ row.value }}</b>
      </div>
    </div>
  </div>
  <slot name="slate" />
</header>
```

在 `style.css` 增加 `.head-actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px }`。

- [ ] **步骤 3：实现 `StatStrip.vue`**

按 `prototype/index.html:246-258` 输出 `.stats > .stat`，每项 `.k` + `b`（value + 可选 `em` 单位）+ 固定 5 段 `.spark`。`tone` 映射为 `amber/green/red` 类。

- [ ] **步骤 4：实现 `ToggleSwitch.vue`**

使用 `.toggle`/`.track` 结构，`input` 隐藏，`:checked="modelValue"`，`@change` 发出布尔值。`size="sm"` 时加 `.sm`。

- [ ] **步骤 5：实现 `SegmentedControl.vue`**

输出 `.seg` + 多个 `.seg-btn`，`on` 类由 `modelValue === option.value` 决定，`disabled` 透传。`size="sm"` 时用内联高度 24px。

- [ ] **步骤 6：实现 `ConfidenceGauge.vue`**

使用 SVG 圆环（`r=36`、`stroke-dasharray=226.2`），`dashoffset = 226.2 * (1 - value/100)`。颜色：`>=85 var(--green)`、`>=60 var(--amber)`、否则 `var(--red)`。中间显示数值与 `%`，下方显示「高置信度 / 中置信度 / 低置信度」。

- [ ] **步骤 7：补齐 `AppIcon` 图标**

在 `paths` 中新增：

```ts
clap: ['M3 9h18v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9Z', 'M3 9l2-5h14l2 5', 'M9 4L7 9', 'M14.5 4L12.5 9'],
eye: ['M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12Z', 'M12 9.4a2.6 2.6 0 1 0 0 5.2 2.6 2.6 0 0 0 0-5.2'],
radio: ['M12 4a8 8 0 1 0 0 16 8 8 0 1 0 0-16', 'M12 10a2 2 0 1 0 0 4 2 2 0 1 0 0-4'],
```

- [ ] **步骤 8：改造 `BatchBar.vue`**

新增可选 props：`chips?: string[]`、`total?: number`。模板改为 `.batchbar` 胶囊：`.batch-count`（`count / (total ?? count)`）、`.batch-chips`（最多 4 个）、`.batch-actions`（清空、默认插槽、下一步）。保留原有 `count / nextLabel / nextDisabled / showNext` 与 `clear/next` emits。

- [ ] **步骤 9：改造 `ToastHost.vue`**

容器改为 `.toasts`，每条改为 `.toast` + `ok/err` 类；图标颜色随类型。

- [ ] **步骤 10：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

---

## 任务 4：数据展示组件样式

**文件：**
- 修改：`frontend/src/components/FileTable.vue`
- 修改：`frontend/src/components/Pager.vue`
- 修改：`frontend/src/components/StatusTag.vue`
- 修改：`frontend/src/components/ConfidenceBadge.vue`
- 修改：`frontend/src/components/TaskProgress.vue`
- 修改：`frontend/src/components/DiffText.vue`
- 修改：`frontend/src/components/TemplateEditor.vue`
- 修改：`frontend/src/components/EmptyState.vue`
- 修改：`frontend/src/components/ErrorBanner.vue`
- 参考：`prototype/index.html:307-340`、`358-427`、`523-558`、`560-599`

- [ ] **步骤 1：`FileTable` 改为原型文件行**

表头：勾选、`文件名 / FILENAME`、大小、修改时间、来源、空操作列。文件名单元拆成两行：`.file-cell`（状态点 + 文件名，扩展名放 `.ext`）与 `.file-sub`（季集 tag、剧名、分辨率、编码）。保留现有 props：`files/allFiles/selected/selectable/showSource/showParsed` 与 `update:selected/open` emits。行点击、全选、半选逻辑不变。

- [ ] **步骤 2：`Pager` 改为 `.table-foot` + `.pager`**

容器 `class="table-foot"`；左侧统计文本，右侧 `.pager` 按钮组。保留页码、上一页/下一页与每页条数 `SelectMenu`。

- [ ] **步骤 3：状态标签统一**

`StatusTag` 继续输出 `.tag`，tone 映射改为：`success→tag-ok`、`warning→tag-warn`、`danger→tag-bad`、`info→tag-info`、`accent→tag-amber`、`muted→tag-mute`。`ConfidenceBadge` 同样使用 `.tag-ok/tag-warn/tag-bad`。

- [ ] **步骤 4：`TaskProgress` 改为 `.bar`**

进度文本用 `.progress-top`（`done/total` 与百分比），条用 `.bar > i`，`failed>0` 保持琥珀，完成用 `.bar.green`。保留 `role="progressbar"` 与 aria 属性。

- [ ] **步骤 5：`DiffText` 改为 `.diff-new`**

保留现有 diff 计算逻辑与 `before/after` props，只替换渲染：外层先渲染 `.diff-old`（`before`，删除线），再渲染 `.diff-new`（箭头 `.arw` + 文本 `.txt`，变更片段用 `<mark>`）。不再新增 props。

- [ ] **步骤 6：`TemplateEditor` 改为 `tpl-panel` 结构**

外层 `.tpl-panel`；第一行 `.tpl-row`（`TEMPLATE` + `.tpl-input`）；第二行 `.vars`（变量 chips）；第三行 `.sample-line`（`PREVIEW` + 示例）。保留 `modelValue/sample/disabled` 与 `update:modelValue`，保留未知变量提示。

- [ ] **步骤 7：`EmptyState` 与 `ErrorBanner` 换色**

EmptyState 图标容器改为 `.panel` 风格暖色边框；ErrorBanner 使用 `--red` 边框/底色，保留 `role="alert"` 与重试。

- [ ] **步骤 8：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：现有扫描页表格、重命名页表格、任务进度条在暗色下可读，无 `<table>` 样式泄漏到下拉浮层（打开任意 SelectMenu 检查）。

---

## 任务 5：交互与弹层组件样式

**文件：**
- 修改：`frontend/src/components/BaseModal.vue`
- 修改：`frontend/src/components/BaseDrawer.vue`
- 修改：`frontend/src/components/ConfirmDialog.vue`
- 修改：`frontend/src/components/SelectMenu.vue`
- 修改：`frontend/src/components/DirectoryBrowser.vue`
- 修改：`frontend/src/components/PathPicker.vue`
- 修改：`frontend/src/components/DataSourceSwitch.vue`
- 修改：`frontend/src/components/ShowCard.vue`
- 修改：`frontend/src/components/EpisodeMapper.vue`
- 参考：`prototype/index.html:200-245`、`440-521`、`669-705`

- [ ] **步骤 1：`BaseModal` 改为 `.modal/.dialog`**

外层遮罩 `.modal.open`，内容 `.dialog`，头部 `.dialog-head` + `.dialog-title`，正文 `.dialog-body`，底部 `.dialog-foot`。保留 `open/title/subtitle/width/close`、Esc 关闭与 body overflow 锁定。

- [ ] **步骤 2：`BaseDrawer` 换色**

保留抽屉结构与过渡，把类名换成 `bg-elevated / border-line` 对应的新 token（别名已生效），头部按钮用 `.icon-btn`。

- [ ] **步骤 3：`ConfirmDialog` 适配新按钮**

确认按钮 `danger ? 'btn btn-danger' : 'btn btn-amber'`，取消 `btn btn-ghost`；保留 loading 文案。

- [ ] **步骤 4：`SelectMenu` 触发器与浮层换色**

触发器继续使用 `.select`，浮层背景 `var(--surface-2)`、边框 `var(--line-2)`、选中项 `var(--amber)`；保留现有键盘、定位与 `aria` 逻辑。

- [ ] **步骤 5：`DirectoryBrowser` 改为 dialog 结构**

面包屑 `.crumbs`，目录区 `.folder-grid` + `.folder`，底部按钮与当前路径保留；内部继续复用 `BaseModal`。

- [ ] **步骤 6：`PathPicker` 改为 `input-group`**

标签改为 `.field label`（中文 + 英文小字）；输入与浏览按钮放进 `.input-group`；递归使用 `ToggleSwitch`。保留 `modelValue/recursive/sourceType/openlistId/allowedRoots` 与两个 `update:` emits。

- [ ] **步骤 7：`DataSourceSwitch` 改为 `.seg`**

保留本地/OpenList 的可选状态与禁用逻辑，外观改为 `.seg` + `.seg-btn`。

- [ ] **步骤 8：`ShowCard` 改为海报卡片**

结构改为 `.show-card` > `.poster`（真实 `img`；无图或加载失败时用 `.poster-art` 字体海报，取标题首字母） + `.show-info`（标题、原名、`.show-meta`：评分/年份/季数）。保留 `show/selected` 与 `select` emit。

- [ ] **步骤 9：`EpisodeMapper` 改为 `.map-row`**

保留 `files/episodesBySeason/season` props 与全部匹配计算，只替换渲染为 `.map-row`（`.from`、`.arw`、`.to`），未匹配行加 `.warn`，底部提示保留。

- [ ] **步骤 10：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：打开目录浏览弹窗、SelectMenu、确认弹窗，确认无表格样式泄漏、焦点描边为琥珀色、Esc 可关闭。

---

## 任务 6：扫描页

**文件：**
- 修改：`frontend/src/views/ScanView.vue`
- 参考：`prototype/index.html:909-1117`

- [ ] **步骤 1：替换页头**

先 `import PageHeader from '@/components/PageHeader.vue'` 与 `import type { SlateRow } from '@/components/ui-types'`，然后使用 `PageHeader`：

```html
<PageHeader
  ghost="01"
  kicker="STEP 01 · INGEST"
  title="扫描"
  title-en="SCAN"
  description="选择剧集所在位置，扫描后自动解析文件名。支持本地白名单目录与 OpenList 云盘。"
  :slate="slate"
/>
```

`slate` 计算：

```ts
const slate = computed<SlateRow[]>(() => [
  { label: 'SOURCE', value: store.sourceType === 'openlist' ? 'OPENLIST' : 'LOCAL' },
  { label: 'ROOT', value: store.scanPath || '—' },
  { label: 'TAKE', value: `${store.files.length} ITEMS` },
  {
    label: 'STATUS',
    value: store.scanning ? 'SCANNING' : store.files.length ? 'READY' : 'IDLE',
    tone: store.scanning ? 'amber' : store.files.length ? 'green' : undefined,
  },
])
```

- [ ] **步骤 2：控制面板**

外壳 `.panel > .scan-controls`。顶部 `.controls-top`：`DataSourceSwitch` 与真实提示（白名单目录数量 + 递归状态）。中部 `.controls-main`：`PathPicker`、扫描按钮 `.btn.btn-amber.scan-btn`。扫描中在面板底部渲染 `.scan-line.on`。

- [ ] **步骤 3：统计条**

在控制面板后加入 `StatStrip`，items 为 `TOTAL ITEMS`、`VIDEO FILES`、`OTHER`、`ELAPSED`（`lastScan ? (elapsed_ms/1000).toFixed(2) : '—'`，单位 `s`）。

- [ ] **步骤 4：文件面板**

`panel` > `.table-toolbar`（左侧 `FILE INDEX` + `rangeStart–rangeEnd / total` + `SCAN OK` 标签；右侧 `ToggleSwitch` 仅看视频 + `.search-mini` 搜索）> `FileTable` > `Pager`。需要从 `usePagination` 解构 `rangeStart`、`rangeEnd`。保留扫描中骨架屏、空态、错误条与行点击进入解析。

- [ ] **步骤 5：BatchBar**

传入 `:chips="store.selectedFiles.slice(0, 4).map(chipLabel)"` 与 `:total="store.files.length"`，保留下一步与清空。新增：

```ts
function chipLabel(file: MediaFile): string {
  const p = file.parsed
  if (!p || p.episode === null) return file.original_name
  return `S${String(p.season ?? 1).padStart(2, '0')}E${String(p.episode).padStart(2, '0')}`
}
```

- [ ] **步骤 6：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：扫描按钮 loading、扫描线动画、统计数字、筛选、分页、多选与 BatchBar；Ctrl/Cmd+Enter 可触发扫描。

---

## 任务 7：解析页

**文件：**
- 修改：`frontend/src/views/ParseView.vue`
- 参考：`prototype/index.html:1120-1269`

- [ ] **步骤 1：页头与操作区**

`PageHeader`：ghost `02`、`STEP 02 · PARSE`、`解析 / PARSE`；slate：

- `FILES` = `files.length`
- `PENDING` = `counts.todo`
- `AVG CONF.` = 已解析文件的平均置信度（无则 `—`），带 `%`
- `MODE` = `MANUAL REVIEW`

`#actions` 放「批量自动解析」「全部接受」两个按钮。

- [ ] **步骤 2：左栏 FILE ROLL**

外层 `.panel` + `.panel-head`（`FILE ROLL / 文件卷` + 数量）。`.tabs-line` 渲染全部/待确认/未解析（保留 `filter` 与计数）。列表项从 `<button>` 改为 `.roll-item`，内部状态点（`.dot ok/warn/bad`）、`SxxExx`、集标题、`.conf` 百分比；选中项 `.on`。底部 `.roll-foot` 放 J/K 快捷键提示，再放 `Pager`。

- [ ] **步骤 3：右栏 SHOT DETAIL**

外层 `.panel`；`.shot-head`（`.shot-id` 徽标 `episodeLabel(active)` + `SHOT DETAIL / 解析详情`；右侧「重新自动解析」「跳过」）。`.raw-block` 展示原始文件名与复制按钮。`.detail-grid` 内左侧 `.form-grid`、右侧 `ConfidenceGauge`（传入 `active.confidence`，未解析时显示 `—` 状态卡片）。

- [ ] **步骤 4：表单与校验**

字段顺序：剧名（span-2）、年份、季/集、集标题（span-2）、分辨率、编码、发布组（span-2）、结束集。保留现有 `draft`、校验与错误提示。低置信度（`confidence < 60`）或剧名为空时给字段容器加 `.low` 并显示 `.hint-low`。

- [ ] **步骤 5：操作条**

`.action-bar`：重新解析（ghost）、保存并下一项（`.btn.btn-amber.push`）。保留 `reparse`、`save`、`move` 全部逻辑。

- [ ] **步骤 6：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：J/K 切换、Tab 筛选、复制文件名、保存后自动下一项、低置信度高亮、分页与选中联动。

---

## 任务 8：刮削页

**文件：**
- 修改：`frontend/src/views/ScrapeView.vue`
- 创建：`frontend/src/composables/useRecentSearches.ts`
- 参考：`prototype/index.html:1272-1415`

- [ ] **步骤 1：创建 `useRecentSearches.ts`**

```ts
import { ref, type Ref } from 'vue'

const KEY = 'episode-scrap-recent-searches'

export function useRecentSearches(max = 4): { items: Ref<string[]>; push: (query: string) => void } {
  const items = ref<string[]>([])
  try {
    const raw = localStorage.getItem(KEY)
    const parsed = raw ? (JSON.parse(raw) as unknown) : []
    if (Array.isArray(parsed)) {
      items.value = parsed.filter((v): v is string => typeof v === 'string').slice(0, max)
    }
  } catch {
    items.value = []
  }
  const push = (query: string) => {
    const value = query.trim()
    if (!value) return
    items.value = [value, ...items.value.filter((item) => item !== value)].slice(0, max)
    localStorage.setItem(KEY, JSON.stringify(items.value))
  }
  return { items, push }
}
```

- [ ] **步骤 2：页头**

`PageHeader`：ghost `03`、`STEP 03 · SCRAPE`、`刮削 / SCRAPE`；slate：`PROVIDER`（`provider.toUpperCase()`）、`MATCHED`（`mappingCount/targetFiles.length`）、`SEASON`（`season ?? '—'`）、`STATUS`（`targetFiles.length - mappingCount` > 0 ? `${n} NEED REVIEW` : 'READY'）。

- [ ] **步骤 3：搜索条**

`.panel > .scan-controls > .controls-main`：搜索 `.input-group`（search 图标）、来源 `SelectMenu`（包在 `.input-group` 中）、搜索按钮、`自动匹配全部` 琥珀按钮。搜索成功后调用 `recent.push(keyword)`。

- [ ] **步骤 4：三栏**

外层 `.scrape-grid`。

- 左 `panel`：`.panel-head`（`PENDING / 待匹配` + 数量）、`.pick-row` 列表（checkbox + `SxxExx` + 集标题 + `StatusTag`）、`Pager`。
- 中 `panel`：`.panel-head`（`CANDIDATES / 候选剧集` + 结果数）、`.show-grid` 渲染 `ShowCard`、`.recent-searches`（`items.length > 0` 时显示）、`.legend`。
- 右 `panel`：`.panel-head`（`MAPPING / 匹配关系` + `mappingCount/targetFiles`）、`.map-head`（海报 + 标题 + 原名 + 年份/评分/季数 + 季 `SelectMenu` 包在 `.select-inline`）、`.map-list` 包 `EpisodeMapper`、`.map-foot` 确认匹配按钮。

保留未选择剧集/该季无剧集/加载骨架等状态。

- [ ] **步骤 5：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：搜索、选择剧集、切换季、映射关系、确认匹配、RECENT 显示与持久化（刷新页面仍在）；手动把 localStorage 的该键改成非法 JSON 后刷新页面，刮削页仍正常渲染且 RECENT 隐藏。

---

## 任务 9：重命名页

**文件：**
- 修改：`frontend/src/views/RenameView.vue`
- 参考：`prototype/index.html:1418-1559`

- [ ] **步骤 1：页头**

`PageHeader`：ghost `04`、`STEP 04 · RENAME`、`重命名 / RENAME`；slate：`READY`、`CONFLICT`、`SKIPPED`（来自 `preview`，无预览为 `—`）、`OUTPUT`（`写入 NFO` / `NFO + POSTER` / `—`，按开关组合）。

- [ ] **步骤 2：模板面板**

`.panel > .tpl-panel`，内含 `TemplateEditor` 与「恢复默认」按钮（点击把 `template` 设为 `store.settings?.rename_template ?? ''`）。保留变量说明。

- [ ] **步骤 3：DIFF PREVIEW 面板**

`.panel` > `.table-toolbar`（`DIFF PREVIEW` + 总数 + 冲突标签；右侧冲突策略 `SegmentedControl`）> 表格（勾选、原→新 diff、状态、说明）> `Pager`。表格行类 `.sel` 用于冲突行；`DiffText` 传入 `:before="item.original_name"` 与 `:after="item.new_name ?? '—'"`。

- [ ] **步骤 4：执行条**

`.exec-bar`：`.exec-info`（已选/总数）、`.exec-toggles`（三个 `ToggleSwitch`：写入 NFO、下载海报、生成 STRM）、右侧仅预览、撤销上次（danger）、执行重命名（amber）。执行中在其上方保留任务进度行。

- [ ] **步骤 5：确认弹窗**

保留两个 `ConfirmDialog`，只改按钮样式；不动 `execute`/`rollback` 逻辑。

- [ ] **步骤 6：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：仅预览生成 diff、冲突策略切换、勾选合计、执行确认、撤销确认、执行中实时进度。

---

## 任务 10：任务中心

**文件：**
- 修改：`frontend/src/views/TasksView.vue`
- 参考：`prototype/index.html:1562-1703`

- [ ] **步骤 1：页头**

`PageHeader`：ghost `05`、`OPERATIONS · TASKS`、`任务中心 / TASKS`；slate：`RUNNING`、`QUEUED`、`DONE TODAY`（`status === 'completed'` 且 `created_at` 为今天）、`SOCKET`（`socketConnected ? 'CONNECTED' : 'IDLE'`）。

- [ ] **步骤 2：跟踪 WebSocket 状态**

新增 `const socketConnected = ref(false)`；`connect` 中 `ws.onopen = () => (socketConnected.value = true)`，`ws.onclose`/`onerror` 置 `false`；`disconnect` 同样置 `false`。

- [ ] **步骤 3：两栏布局**

外层 `.tasks-grid`。左栏 `.panel`：`.table-toolbar`（`TASK LOG` + 记录数；右侧状态 `SegmentedControl` + 刷新 `icon-btn`）+ 任务表（类型图标 + 标题 + ID、数据源 tag、`TaskProgress`、`StatusTag`、开始时间）。选中行加 `.on`。

右栏 `.panel`：`.panel-head`（`DETAIL / 任务详情` + 关闭按钮）；无选中时显示 EmptyState「选择左侧任务」。有选中时渲染 `.detail-head`（ID、标题、数据源 + 启动时间）、`.detail-progress`（大号百分比 + 计数 + `.bar`）、`.detail-meta`（模板、并发、NFO、海报）、`.task-items`（逐项状态）、`.detail-foot`（复制 ID、重试失败项）。

- [ ] **步骤 4：移除 BaseDrawer 用法**

删除 `drawerOpen` 与 `BaseDrawer` 模板。`open(task)` 只设置 `detail`；关闭按钮清空 `detail` 并 `disconnect()`。保持轮询、WS、`retry` 逻辑。

- [ ] **步骤 5：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：筛选状态、刷新、点击任务后右栏展示详情、运行中任务进度实时更新、关闭后 WS 断开、重试失败项可用；窄屏时详情堆叠在任务表下方。

---

## 任务 11：刷新媒体库

**文件：**
- 修改：`frontend/src/views/RefreshView.vue`
- 参考：`prototype/index.html:1706-1762`

- [ ] **步骤 1：页头**

`PageHeader`：ghost `06`、`MAINTENANCE · REFRESH`、`刷新媒体库 / REFRESH`；slate：`JELLYFIN`（`store.settings?.jellyfin_url || '—'`）、`LIBRARIES`（`libraries.length`）、`LAST RUN`（本次会话最近刷新时间或 `—`）、`STATE`（`configured ? 'CONNECTED' : 'UNCONFIGURED'`，tone green/amber）。

- [ ] **步骤 2：媒体库卡片**

已配置时渲染 `.lib-grid`，每个库一张 `.panel.lib-card`：`.k` 显示类型（剧集/电影/音乐/混合）、`h3` 库名、真实刷新状态 tag、单库「刷新媒体库」按钮。卡片可点击切换 `selected`。

保留工具栏「重新加载」「全选」「刷新选中」。

- [ ] **步骤 3：刷新日志**

新增 `logs` ref，类型 `{ time: string; ok: boolean; message: string }[]`。`refresh(ids)` 成功后把每个结果 push 进日志（时间用 `new Date().toLocaleTimeString()`，失败带 `error`），并更新 `lastRun`。`.log-panel` 渲染日志；无日志显示空态文本。

- [ ] **步骤 4：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：未配置时显示 EmptyState；已配置时库卡片、单库刷新、全选刷新、成功/失败反馈与日志正确；不出现伪造的条目数与上次扫描时间。

---

## 任务 12：设置页

**文件：**
- 修改：`frontend/src/views/SettingsView.vue`
- 参考：`prototype/index.html:1765-1985`

- [ ] **步骤 1：页头**

`PageHeader`：ghost `07`、`CONFIG · SETTINGS`、`设置 / SETTINGS`；slate：`TMDB`（`has_tmdb_key ? 'CONFIGURED' : 'MISSING'`）、`OPENLIST`（`instances.length`）、`JELLYFIN`（已配置/未配置）、`VERSION`（`__APP_VERSION__`）。

- [ ] **步骤 2：Tabs**

外层 `.settings-grid`；左栏 `.panel.settings-tabs`，每个 tab 用 `.stab`（`.num` 01–06 + 标签），选中 `.on`；窄屏横向滚动。

- [ ] **步骤 3：各 Tab 面板**

右栏 `.panel`，各 pane 使用 `.pane.on` + `.set-section` + `.set-title` + `.form-row` / `.form-row.three` + `.form-actions`：

- 媒体源：TMDB Key 输入（`.input-group` + eye 图标）、语言说明、集成状态 `.instance` 列表。
- OpenList：`.instance` 列表 + 测试/编辑/删除按钮，`.warn-note`；新增/编辑弹窗与删除确认保持不变。
- 命名模板：`TemplateEditor` + 变量说明表。
- STRM：`.mode-grid` 三模式卡片 + 链接模板 + 目标目录 + 规则列表。
- Jellyfin：地址/Key + 测试/保存。
- 通用：白名单 textarea + 三个数字输入 + 保存。

所有 `v-model`、保存函数、校验与弹窗逻辑不变。

- [ ] **步骤 4：验证**

运行：`cd frontend && npm run typecheck && npm run build`
预期：通过。

浏览器检查：六个 Tab 切换、TMDB Key 保存、OpenList 新增/编辑/测试/删除、模板保存、STRM 模式切换与规则增删、Jellyfin 测试、通用保存。

---

## 任务 13：清理与全站验证

**文件：**
- 修改：`frontend/src/style.css`（删除确认无用的旧类）
- 修改：可能存在旧主题引用的视图/组件

- [ ] **步骤 1：搜索残留**

运行：`cd frontend && grep -rn "data-theme\|prefers-color-scheme\|episode-scrap-theme\|--sidebar-width\|mobileOpen\|toggleCollapsed" src`
预期：无结果；若有，删除或替换。

- [ ] **步骤 2：搜索死类**

在 `style.css` 中确认以下旧类要么仍被使用、要么删除：`.btn-primary`（保留为琥珀别名）、`.tag-success/tag-warning/tag-danger`（保留别名）、`.divider`、`.scroll-thin`、`.row-striped`。删除无人引用的类。

- [ ] **步骤 3：类型检查与构建**

运行：`cd frontend && npm run typecheck && npm run build`
预期：均通过，无 TS 错误。

- [ ] **步骤 4：全站浏览器检查**

运行：`cd frontend && npm run dev`，逐页检查 `/`、`/parse`、`/scrape`、`/rename`、`/tasks`、`/refresh`、`/settings`：

- 1440px：完整布局，内容居中。
- 1180px：Rail 图标模式，三栏仍可用。
- 900px：Topbar 中段隐藏，页面不横向溢出，BatchBar 不遮挡内容。
- 控制台无报错。
- 键盘 Tab 焦点可见（琥珀色 2px 描边）；弹窗 Esc 可关闭；装饰层 `aria-hidden="true"`。

- [ ] **步骤 5：主链路检查（后端可用时）**

扫描 → 解析 → 搜索/匹配 → 仅预览 → 执行 → 任务中心查看进度 → 刷新媒体库。检查空态、加载态、错误条、未配置 TMDB/Jellyfin、低置信度、冲突行。

---

## 自检记录

- 规格覆盖：Token/字体/氛围（任务 1）、AppShell（任务 2）、共享组件（任务 3–5）、7 个页面（任务 6–12）、真实数据映射（分散在 2/6/8/10/11/12）、响应式与清理（任务 13）。
- 类型一致性：`SlateRow`、`StatItem`、`SegValue` 在任务 3 定义，任务 6–12 直接引用；`useRecentSearches` 在任务 8 定义并使用；`__APP_VERSION__` 在任务 1 定义，任务 12 使用。
- 审查重点：6 条均已在对应任务中加入验证步骤（主题残留→任务 13，全局选择器→任务 4/5，定时器与 WS→任务 2/10，localStorage→任务 8，窄屏→任务 13，任务实时状态→任务 10）。
