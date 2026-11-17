# 前端按原型重构 — 设计规格

> 日期：2026-11-17
> 依据：`prototype/index.html`（Media Workbench / Projection Room 原型）
> 范围：`frontend/` 视觉与布局层重构，不改后端与 API

## 1. 背景与目标

现有前端是 Vue 3 + Vite + Tailwind 4 的深/浅主题工作台，视觉体系为冷色青绿（`#18c2a8`）。`prototype/index.html` 提供了完整的新设计方向：暖色暗房黑 + 琥珀色、场记板/胶片元素、Topbar + 左侧编号 Rail 的外壳结构，覆盖扫描、解析、刮削、重命名、任务中心、刷新媒体库、设置七个页面。

本次重构的目标是让前端在**不改变任何业务行为与 API 契约**的前提下，视觉与布局对齐原型。

成功标准：

- 七个路由页面在外壳、配色、字体、面板/表格/表单风格上与原型一致。
- 现有全部功能与交互保留，主链路（扫描 → 解析 → 刮削 → 重命名 → 刷新）可正常操作。
- `npm run typecheck` 与 `npm run build` 通过，无控制台报错。
- 不出现原型中的示例假数据。

## 2. 已确认决策

| 决策点 | 结论 |
|---|---|
| 主题 | 只保留深色；移除主题切换、`data-theme` 与浅色 token |
| 装饰元素 | 尽量用真实数据驱动；无法映射的数据显示 `—` 或省略 |
| 功能边界 | 保留全部现有功能、交互与 API；原型只决定视觉与布局 |
| 实现策略 | Token + 组件类迁移：重写 `style.css` 设计 token 与基础组件类，Tailwind 继续负责布局；逐页替换模板 |

## 3. 设计基准

### 3.1 色彩 Token

在 `frontend/src/style.css` 中替换 `:root`：

| Token | 值 | 用途 |
|---|---|---|
| `--bg` | `#0a0807` | 页面底色 |
| `--surface` | `#12100e` | 面板 |
| `--surface-2` | `#191512` | 面板内次级块 |
| `--elev` | `#211b17` | 浮层 |
| `--line` | `#292420` | 常规边框 |
| `--line-2` | `#3d342d` | 强调边框 |
| `--ink` | `#f3ebdf` | 主文本 |
| `--muted` | `#a2968a` | 次要文本 |
| `--faint` | `#6c6258` | 弱文本 |
| `--amber` | `#f0a02c` | 主强调 |
| `--amber-2` | `#ffc873` | 高亮强调 |
| `--amber-soft` | `rgba(240,160,44,.09)` | 选中底色 |
| `--green` | `#86c98d` | 成功 |
| `--red` | `#e2654f` | 失败/危险 |
| `--blue` | `#7fa8cf` | 信息/云盘 |

保留 Tailwind `@theme inline` 映射，让现有工具类继续可用：

- `--color-base → --bg`、`--color-surface → --surface`、`--color-elevated → --elev`
- `--color-line → --line`、`--color-line-strong → --line-2`
- `--color-ink/muted/faint` 对应文本三级
- `--color-accent → --amber`、`--color-accent-soft → --amber-soft`
- 新增 `--color-surface-2`、`--color-amber-2`
- `--font-sans → --sans`、`--font-mono → --mono`

### 3.2 字体

在 `frontend/index.html` 引入：

- Display：Bricolage Grotesque
- 正文：IBM Plex Sans
- 数据/等宽：IBM Plex Mono

字体栈保留中文兜底：`PingFang SC`、`Hiragino Sans GB`、`Microsoft YaHei`。CDN 不可用时回退系统字体，不阻塞页面。

### 3.3 全局氛围

- `.ambient`：双径向暖色/冷色光晕。
- `.scanlines`：细横线叠加。
- `.grain`：低透明度噪点（`aria-hidden`）。
- 移除现有网格背景 `body::before`。
- `prefers-reduced-motion` 下关闭动画。

### 3.4 基础组件类

从原型移植并在 `style.css` 内以组件层实现：

- 按钮：`.btn`、`.btn-amber`、`.btn-ghost`、`.btn-danger`、`.btn-sm`、`.btn-xs`
- 图标按钮：`.icon-btn`（含 `.bubble` 徽标）
- 面板：`.panel`、`.panel-head`、`.panel-title`、`.panel-side`
- 表单：`.input`、`.input.mono`、`.input-group`、`.textarea`、`.field`、`.field.low`、`.hint-low`
- 标签：`.tag`、`.tag-ok`、`.tag-warn`、`.tag-bad`、`.tag-info`、`.tag-mute`、`.tag-amber`
- 其它：`.kbd`、`.hr`、`.dot`（ok/warn/bad）、`.seg/.seg-btn`、`.toggle`、`.bar`、`.stats/.stat`、`.page-head`、`.kicker`、`.slate`
- 动画：`rise`、`fadeIn`、`toastIn`、`pulse`、`spin`、`sweep`

注：原型对 `table`、`thead th`、`tbody td`、`h1` 使用全局选择器；落地时收进 `.panel` 等作用域，避免污染。

## 4. 应用外壳（AppShell）

### 4.1 结构

`frontend/src/components/AppShell.vue` 由「顶栏 + 可折叠侧栏」重写为：

- 网格：`grid-template-columns: 236px minmax(0,1fr)`，行 `58px minmax(0,1fr)`。
- Topbar 跨两列；Rail 位于第二行左侧；主内容区 `main > page-wrap > router-view`。
- `page-wrap` 最大宽度 1500px，内边距 `22px 28px 140px`。

### 4.2 Topbar

- 品牌：圆形胶片盘 + `EPISODE SCRAP` + `MEDIA WORKBENCH`。
- 中段：`LIVE` 红点、真实 timecode（`HH:MM:SS:FF`，24fps）、`24 FPS · REC.709`、虚线分隔、SOURCE pill（真实数据源 + 扫描路径）。
- 右侧：任务中心图标（运行中/等待中数量气泡）、设置图标。
- 移除主题切换按钮。

### 4.3 Rail

- `WORKFLOW` 标签 + 竖线连接的四步：`01 扫描 / INGEST`、`02 解析 / PARSE`、`03 刮削 / SCRAPE`、`04 重命名 / RENAME`。
- 每步右侧显示 `store.stepCounts` 对应计数。
- 保留「前置步骤未完成则禁用」逻辑。
- `UTILITIES` 分组：刷新媒体库。
- 底部 rail-meta：`LIBRARY`（`store.files.length`）、`IN QUEUE`（已解析未匹配数）、film-strip（12 段，高亮段数由完成度决定，`aria-hidden`）、`SYSTEM NOMINAL` + 版本号。
- 底部链接：任务中心（真实运行数量）、设置。
- 响应式：≤1180px 收为 76px 图标模式；≤900px 隐藏 Topbar 中段。
- 移除手动折叠状态与移动端抽屉。

### 4.4 BatchBar

改为原型固定底部居中胶囊：左侧选中数量 / 总数，中部选中项 chips（最多 4 个），右侧清空与下一步。保留现有 `count`、`next-label`、`clear`、`next` 交互。

## 5. 新增与改造的共享组件

### 5.1 新增

| 组件 | 职责 |
|---|---|
| `PageHeader.vue` | 统一页头：ghost 编号、kicker、标题、英文副标题、描述、右侧 slate 行；`#actions` 插槽渲染在标题描述下方的操作区，slate 始终固定右侧 |
| `StatStrip.vue` | 四格统计条（扫描页），支持 label / value / 单位 / spark |
| `ToggleSwitch.vue` | 原型开关外观，`v-model:boolean`，可调尺寸 |
| `SegmentedControl.vue` | 原型分段控件，`v-model` + options，用于数据源、筛选、冲突策略、STRM 模式 |
| `ConfidenceGauge.vue` | 环形置信度仪表，按 85/60 阈值着色，展示百分比与高/中/低标签 |

### 5.2 改造（保持对外 props/emit 不变）

`FileTable`、`Pager`、`PathPicker`、`DirectoryBrowser`、`SelectMenu`、`ShowCard`、`EpisodeMapper`、`TemplateEditor`、`DiffText`、`TaskProgress`、`StatusTag`、`ConfidenceBadge`、`BaseModal`、`BaseDrawer`、`ConfirmDialog`、`ToastHost`、`EmptyState`、`ErrorBanner`、`DataSourceSwitch`、`AppIcon`。

改造仅限模板结构与 class，不改变组件 API；`AppIcon` 补齐原型所需图标（clap、film、cloud、server、sparkles、play、plus、trash、eye、clock、loader、radio、chevron、arrow-left/right）。

## 6. 页面设计

### 6.1 扫描 `/`

- `PageHeader`：ghost `01`、`STEP 01 · INGEST`、标题「扫描 / SCAN」、描述；slate：`SOURCE`（本地/OpenList）、`ROOT`（扫描路径或 `—`）、`TAKE`（文件数 ITEMS）、`STATUS`（扫描中/就绪/待扫描）。
- 控制面板：数据源 `SegmentedControl`；路径用 `input-group`（文件夹图标 + 输入 + 浏览）；`ToggleSwitch` 递归；琥珀色「开始扫描」；扫描中显示 `scan-line` 扫光。
- 统计条：`TOTAL ITEMS`、`VIDEO FILES`、`OTHER`、`ELAPSED`（`lastScan.elapsed_ms`，无则 `—`）。
- 文件面板：工具栏 `FILE INDEX` + 当前区间 + `SCAN OK` 标签；仅看视频开关 + 文件名筛选；`FileTable`；`Pager` 在面板底部。
- 保留 `Ctrl/Cmd+Enter` 扫描、行点击进入解析、BatchBar。

### 6.2 解析 `/parse`

- `PageHeader`：`02`、`STEP 02 · PARSE`；slate：`FILES`、`PENDING`、`AVG CONF.`、`MODE`（MANUAL REVIEW）。
- 页头操作区（`#actions`）保留「批量自动解析」「全部接受」。
- 左栏 FILE ROLL：全部/待确认/未解析 Tab（含计数）；行内状态点、`SxxExx`、集标题、置信度；底部 J/K 快捷键提示与 `Pager`。
- 右栏 SHOT DETAIL：`SxxExx` 徽标 + 原始文件名块（可复制）；表单网格含剧名、年份、季、集、集标题、分辨率、编码、发布组、结束集；`ConfidenceGauge` 显示真实置信度；低置信度或剧名为空时字段高亮并提示。
- 底部操作条：重新自动解析、跳过、保存并下一项。
- 保留批量解析、键盘 J/K、分页与选中联动。

### 6.3 刮削 `/scrape`

- `PageHeader`：`03`、`STEP 03 · SCRAPE`；slate：`PROVIDER`、`MATCHED`（`mappingCount/targetFiles`）、`SEASON`、`STATUS`（需人工数）。
- 搜索条：`input-group` 搜索框、媒体源 `SelectMenu`、搜索、琥珀色「自动匹配全部」。
- 三栏：
  - 左 PENDING：文件勾选行（`SxxExx` + 标题 + 状态标签），保留全选逻辑与分页。
  - 中 CANDIDATES：`ShowCard` 真实海报，无图时用字体海报占位；下方 RECENT（localStorage 最近 4 次成功搜索，空则整块隐藏）；底部图例。
  - 右 MAPPING：真实剧名/原名/年份/评分/季数 + 季选择；`EpisodeMapper` 展示本地 → 目标映射与未匹配警示；底部确认匹配。
- 保留 TMDB 未配置提示与跳转设置。

### 6.4 重命名 `/rename`

- `PageHeader`：`04`、`STEP 04 · RENAME`；slate：`READY`、`CONFLICT`、`SKIPPED`、`OUTPUT`（来自 `preview`，否则 `—`）。
- 模板面板：`TemplateEditor` 改为 `tpl-panel`（TEMPLATE 输入、变量 chips、PREVIEW 示例行），保留恢复默认。
- DIFF PREVIEW 面板：工具栏显示可执行/冲突/跳过计数；冲突策略 `SegmentedControl`；表格列为勾选、原→新 diff、状态、说明；保留分页与仅勾选可执行项。
- 底部执行条（sticky）：`已选 X / 总数`、写入 NFO / 下载海报 / 生成 STRM 三个 `ToggleSwitch`、仅预览、撤销上次、执行重命名；执行中显示实时任务进度。
- 保留两个二次确认弹窗（执行、撤销）。

### 6.5 任务中心 `/tasks`

- `PageHeader`：`05`、`OPERATIONS · TASKS`；slate：`RUNNING`、`QUEUED`、`DONE TODAY`、`SOCKET`（有 WebSocket 连接时 CONNECTED，否则 IDLE）。
- 左右两栏：左侧任务表（状态分段筛选、刷新按钮、类型图标、数据源标签、`TaskProgress`、状态、开始时间）；右侧详情面板（任务 ID、标题、数据源/启动时间、大号百分比 + 计数、模板/并发/NFO/海报元信息、逐项结果、复制 ID、重试失败项、关闭）。
- 宽屏内联右栏，窄屏详情堆叠在任务表下方；保留轮询、WebSocket 实时更新、重试。
- `BaseDrawer` 不再用于任务详情，但组件保留给其它场景。

### 6.6 刷新媒体库 `/refresh`

- `PageHeader`：`06`、`MAINTENANCE · REFRESH`；slate：`JELLYFIN`（URL）、`LIBRARIES`（数量）、`LAST RUN`（本次会话最近刷新时间或 `—`）、`STATE`（已连接/未配置）。
- 未配置时显示 EmptyState + 去设置。
- 已配置时：工具栏含重新加载、全选、刷新选中；`lib-grid` 每库一张卡片，显示库名、类型（剧集/电影/音乐/混合）、本次刷新状态、单库刷新按钮。
- 后端未提供条目数与上次扫描时间，卡片不显示这些数字。
- 刷新日志面板：由本次会话真实刷新结果生成（时间、成功/失败、错误信息）；无记录时显示空态。
- 保留 `results` 每条库的成功/失败反馈。

### 6.7 设置 `/settings`

- `PageHeader`：`07`、`CONFIG · SETTINGS`；slate：`TMDB`（已配置/未配置）、`OPENLIST`（实例数）、`JELLYFIN`（已配置/未配置）、`VERSION`（构建注入版本）。
- `settings-grid`：左侧 Tabs `01 媒体源`、`02 OpenList`、`03 命名模板`、`04 STRM`、`05 Jellyfin`、`06 通用`；右侧面板按 Tab 切换。
- 各 Tab 内容与现有逻辑一一保留：TMDB Key/语言/测试；OpenList 实例列表、新增/编辑弹窗、测试、删除确认；命名模板编辑与预览；STRM 三模式卡片 + 链接模板 + 目标目录 + 规则；Jellyfin 地址/Key/测试；通用白名单、并发、超时、重试、清空缓存。
- 表单布局改为原型 `form-row` / `form-row.three` / `instance` / `mode-grid` / `warn-note`。

## 7. 真实数据映射

| 元素 | 来源 |
|---|---|
| timecode | 本地时钟，24fps 帧位，每秒刷新 |
| LIVE / REC | 应用在线状态，不伪造录制 |
| SOURCE pill | `store.sourceType` + `store.scanPath` |
| 页头 slate | 各页真实 store/API 数据，缺失显示 `—` |
| ghost number | 路由固定 01–07 |
| Rail 步骤计数 | `store.stepCounts` |
| Rail LIBRARY / IN QUEUE | `store.files.length` / 已解析未匹配数 |
| film-strip | 12 段，高亮段数由工作流完成度决定 |
| RECENT 搜索 | localStorage 最近 4 次成功搜索 |
| 刷新日志 | 本次会话真实刷新结果 |
| 版本号 | `package.json` 版本经 Vite 注入 |

原则：无真实来源的数字不渲染。

## 8. 响应式与可访问性

- ≥1440px：完整三栏布局，内容居中。
- 1180–1440px：Rail 收为 76px；刮削三栏按原型收窄。
- 900–1180px：设置/任务单列；刮削堆叠为单列；解析单列。
- <900px：隐藏 Topbar 中段；表格隐藏日期列；BatchBar 收窄。
- 保留 `:focus-visible` 2px 琥珀描边、弹窗焦点管理、`aria-label`、`aria-selected`、`aria-hidden` 装饰层、`prefers-reduced-motion`。

## 9. 实施顺序

1. 基础层：`index.html` 字体、`style.css` token/组件类/动画、`main.ts` 去主题初始化、`vite.config.ts` 注入版本号。
2. 外壳：`AppShell.vue` 重写；新增 `PageHeader`、`StatStrip`、`ToggleSwitch`、`SegmentedControl`、`ConfidenceGauge`；改造 `BatchBar`、`ToastHost`、`AppIcon`。
3. 共享组件样式改造。
4. 页面按顺序：扫描 → 解析 → 刮削 → 重命名 → 任务中心 → 刷新 → 设置。
5. 清理：浅色主题残留、失效样式、未使用 class、响应式断点、可访问性。

## 10. 验证

- `npm run typecheck` 通过。
- `npm run build` 通过。
- `npm run dev` 后逐页检查 1440 / 1180 / 900 三档宽度。
- 无浏览器控制台报错。
- 主链路可操作：扫描 → 解析 → 搜索/匹配 → 预览 → 执行 → 任务详情 → 刷新库。
- 关键状态覆盖：空态、加载态、错误条、未配置 Jellyfin/TMDB、低置信度、冲突行。

## 11. 不在本次范围

- 不修改后端、数据库、API 契约与 WebSocket 协议。
- 不新增 npm 依赖（字体走 CDN）。
- 不新增原型未体现的业务功能。
- 不保留浅色主题。
