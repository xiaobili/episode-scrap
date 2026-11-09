# EpisodeScrap 全栈 MVP 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 subagent-driven-development（推荐）或 executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 交付可运行的「扫描 → 解析 → 刮削 → 重命名」全栈 MVP，同时支持本地文件与 OpenList 云盘数据源。

**架构：** FastAPI 后端按 `api / services / core / datasources / providers / clients` 分层：DataSource 负责“文件在哪”，Provider 负责“元数据从哪来”，核心解析/重命名/NFO 只依赖抽象接口。Vue 3 前端用 Pinia 保存单批文件工作流状态，六个页面围绕顶部四步流程串联。

**技术栈：** Python 3.11+ / FastAPI / SQLModel + SQLite / httpx / loguru / cryptography；Vue 3 + TypeScript / Vite / Tailwind CSS 4 / Pinia / Vue Router 4 / axios。**不使用 Element Plus**，弹窗、消息、抽屉、提示等全部用 Tailwind 自研组件。

**规格：** `design.md`（系统设计 v1.1）、`frontend-layout-design.md`（前端布局 v1.0）；视觉参考 `prototype/index.html`。

## 全局约束

- 支持的视频扩展名：`.mkv .mp4 .avi .mov .wmv .flv .ts .webm`。
- 本地路径必须落在 `ALLOWED_PATHS`（分号分隔）内；解析真实路径后校验，拒绝 `..` 越界。
- OpenList 密码 Fernet 加密入库；API Key 同样加密；任何响应不得返回明文密码或完整 Key，只返回 `has_password` / `has_tmdb_key`。
- OpenList Token 仅存后端内存；401 自动重登并只重试一次；429 指数退避，最多 30s。
- 所有重命名/写 NFO 必须先经过 preview；目标文件已存在时状态为 `conflict`，绝不覆盖。
- 仅同目录重命名，不移动文件；扩展名由后端保留。
- 单个文件失败不中断批次，失败项逐条写入任务结果。
- 回滚只回滚 `rolled_back=false` 的历史；文件已不存在时记失败，不中断。
- 默认命名模板：`{title} - S{season:02d}E{episode:02d} - {episode_title}`。
- 深色为默认主题，支持浅色切换；主场景桌面端 ≥1024px。
- 不创建 git commit（用户未授权提交）。

## 审查重点（Review Focus）

| # | 输入 / 条件 | 期望行为 | 负责任务 |
|---|---|---|---|
| 1 | 无季集信息或动漫绝对集号（`[Group] Show - 05.mkv`） | 不臆造季号，`season/episode` 为空或低置信度，进入人工确认 | 任务 2 |
| 2 | 扫描路径含 `..`、软链接越界或不在白名单 | 返回 400，不列出任何目录外文件 | 任务 3 |
| 3 | 目标新文件名已存在 | preview 标 `conflict`，execute 跳过，不覆盖 | 任务 5 |
| 4 | OpenList Token 过期 / 429 / 单条重命名失败 | 401 重登一次；429 退避；仅失败项入错误列表 | 任务 4、7 |
| 5 | 回滚时原文件已被外部移动/删除 | 该项失败并记录原因，其余项继续，历史不标记已回滚 | 任务 7 |

---

## 文件结构

```
backend/
├── pyproject.toml
├── .env.example
├── app/
│   ├── main.py                 # FastAPI 实例、CORS、路由与 WS 注册
│   ├── config.py               # pydantic-settings 配置
│   ├── db.py                   # engine / session / init_db
│   ├── models.py               # 全部 SQLModel 表
│   ├── schemas.py              # 请求/响应 Pydantic 模型
│   ├── api/
│   │   ├── __init__.py         # APIRouter 聚合
│   │   ├── datasources.py      # OpenList 实例 CRUD / 测试 / 目录树
│   │   ├── scan.py             # /api/scan、/api/directories/tree、/api/files
│   │   ├── parse.py            # /api/parse、PUT /api/parse/{id}
│   │   ├── scrape.py           # providers/search/shows/match
│   │   ├── rename.py           # preview / execute / rollback
│   │   ├── tasks.py            # 任务列表、详情、重试、WS
│   │   └── settings.py         # GET/PUT /api/settings
│   ├── core/
│   │   ├── parser.py           # FilenameParser → ParsedInfo
│   │   ├── matcher.py          # 文件 ↔ 季集匹配
│   │   ├── renamer.py          # 模板渲染、冲突检测、执行
│   │   └── nfo.py              # Kodi 兼容 NFO
│   ├── datasources/
│   │   ├── base.py             # FileEntry + BaseDataSource
│   │   ├── local.py
│   │   ├── openlist.py
│   │   └── factory.py
│   ├── clients/openlist.py     # OpenList HTTP 客户端（token 生命周期）
│   ├── providers/
│   │   ├── base.py             # Show / ShowDetail / EpisodeInfo
│   │   ├── tmdb.py
│   │   └── __init__.py         # 注册表 + get_provider
│   ├── services/
│   │   ├── crypto.py           # Fernet 加解密
│   │   ├── paths.py            # 白名单与路径安全
│   │   ├── settings.py         # key-value 配置读写
│   │   └── task_manager.py     # 后台任务 + WS 广播
│   └── ws.py                   # 任务进度连接管理
└── tests/
    ├── conftest.py
    ├── test_parser.py
    ├── test_local_datasource.py
    ├── test_openlist_client.py
    ├── test_renamer.py
    ├── test_tmdb_provider.py
    ├── test_tasks.py
    └── test_settings.py

frontend/
├── package.json
├── vite.config.ts
├── index.html
├── tsconfig.json
└── src/
    ├── main.ts
    ├── App.vue
    ├── style.css               # Tailwind 主题 tokens + 全局样式
    ├── router/index.ts
    ├── api/client.ts           # axios + 全部 API 封装
    ├── types.ts
    ├── stores/workflow.ts      # 文件工作流 + 设置 + 任务
    ├── components/
    │   ├── AppShell.vue        # TopBar + SideNav + 内容区
    │   ├── StepNav.vue
    │   ├── BatchBar.vue
    │   ├── DataSourceSwitch.vue
    │   ├── PathPicker.vue
    │   ├── DirectoryBrowser.vue
    │   ├── FileTable.vue
    │   ├── StatusTag.vue
    │   ├── ConfidenceBadge.vue
    │   ├── EmptyState.vue
    │   ├── TemplateEditor.vue
    │   ├── DiffText.vue
    │   ├── ShowCard.vue
    │   ├── EpisodeMapper.vue
    │   └── TaskProgress.vue
    └── views/
        ├── ScanView.vue
        ├── ParseView.vue
        ├── ScrapeView.vue
        ├── RenameView.vue
        ├── TasksView.vue
        └── SettingsView.vue
```

---

## 任务 1：后端骨架、配置与数据模型

**文件：**
- 创建：`backend/pyproject.toml`、`backend/.env.example`、`backend/app/{main,config,db,models,schemas}.py`
- 测试：`backend/tests/conftest.py`

- [ ] **步骤 1：编写失败的测试**

`tests/conftest.py` 提供 `client` fixture：用临时 SQLite + `httpx.AsyncClient(transport=ASGITransport(app=app))`。
`test_health()`：`GET /api/health` 返回 `{"status":"ok"}`。

- [ ] **步骤 2：运行测试确认失败**

运行：`cd backend && uv run pytest tests/conftest.py -q`（尚无 app 导入，预期 Collection error）。

- [ ] **步骤 3：实现骨架**

- `pyproject.toml` 依赖：`fastapi`、`uvicorn[standard]`、`sqlmodel`、`httpx`、`pydantic-settings`、`loguru`、`cryptography`、`pytest`、`pytest-asyncio`、`anyio`。
- `config.py`：`Settings` 含 `database_url`、`secret_key`、`encryption_key`、`tmdb_api_key`、`allowed_paths: list[str]`、`openlist_concurrency=3`、`openlist_timeout=30`、`openlist_retry=3`、`rename_template`。
- `db.py`：`engine`、`get_session()` 依赖、`init_db()`。
- `models.py`：`OpenListInstance`、`MediaFile`、`ScrapeMatch`、`RenameHistory`、`TaskRecord`、`TaskItem`、`Setting`。字段与 design.md §5.3 一致，并补充：`MediaFile.confidence/status/scan_batch`、`TaskItem{task_id,file_id,name,status,error}`、`RenameHistory.task_id`。
- `schemas.py`：`MediaFileOut`、`ParsedOut`、`ScanRequest`、`TaskOut`、`TaskDetailOut`、`SettingsOut` 等。
- `main.py`：创建 `FastAPI(title="EpisodeScrap")`，启动时 `init_db()`，注册 `GET /api/health` 与 CORS（`http://localhost:5173`）。

- [ ] **步骤 4：运行测试确认通过**

运行：`cd backend && uv run pytest tests -q`；预期 health 测试 PASS。

## 任务 2：文件名解析器

**文件：**
- 创建：`backend/app/core/parser.py`
- 测试：`backend/tests/test_parser.py`

- [ ] **步骤 1：编写失败的测试**

覆盖：
- `Breaking.Bad.S01E03.1080p.BluRay.x264-DEMAND.mkv` → title=`Breaking Bad`, season=1, episode=3, resolution=1080p, codec=x264, release_group=DEMAND, confidence≥85。
- `绝命毒师 第1季 第03集.mp4` → title=`绝命毒师`, season=1, episode=3。
- `Show.1x02.720p.mkv` → season=1, episode=2。
- `Show.S01E01-E02.mkv` → episode=1, episode_end=2。
- `[Group] Some Anime - 05 [1080p].mkv` → season 为 `None`，不臆造季号，confidence<60。
- `README.txt` → 非视频（由 `is_video_filename` 判定 false）。

- [ ] **步骤 2：运行确认失败**

运行：`cd backend && uv run pytest tests/test_parser.py -q`；预期 ImportError。

- [ ] **步骤 3：实现**

`ParsedInfo` dataclass 字段照 design.md §5.2.1，另加 `confidence: int`。
`FilenameParser.parse(filename)`：
1. `is_video_filename` 检查扩展名白名单。
2. 依次匹配 `S(\d{1,2})E(\d{1,2})(?:-E(\d{1,2}))?`、`(\d{1,2})x(\d{1,2})`、`第(\d+)季.*?第(\d+)集`。
3. 切分点左侧清洗标题：去掉方括号内容、分辨率/编码/HDR/来源标签，`.`/`_` 替换空格，压缩空白。
4. 分辨率 `2160p|1080p|720p|480p`；编码 `[xh]\.?26[45]|AV1|HEVC`；发布组取 `-GROUP` 结尾大写段。
5. 置信度：title 40 + season 25 + episode 25 + （year 或 release_group）10，上限 100；无季集时保留已识别 title 并封顶 55。

- [ ] **步骤 4：运行测试确认通过**

运行：`cd backend && uv run pytest tests/test_parser.py -q`；预期全 PASS。

## 任务 3：本地数据源、白名单与扫描 API

**文件：**
- 创建：`backend/app/datasources/{base,local,factory}.py`、`backend/app/services/paths.py`、`backend/app/api/scan.py`
- 测试：`backend/tests/test_local_datasource.py`

- [ ] **步骤 1：编写失败的测试**

用 `tmp_path` 建 `Show/Season 01/a.mkv`、`b.txt`：
- `POST /api/scan {source_type:"local", source_ref:str(tmp), recursive:true}` 只返回视频，`source_type=local`，`is_video=true`，写入数据库。
- `source_ref` 指向白名单外 → 400。
- `source_ref` 含 `..` 越界 → 400。
- `LocalDataSource.rename` 改名成功；目标已存在时抛 `FileExistsError`。
- 再次扫描同目录不产生重复 `MediaFile` 行（按 name 去重）。

- [ ] **步骤 2：运行确认失败**

运行：`cd backend && uv run pytest tests/test_local_datasource.py -q`；预期 ImportError。

- [ ] **步骤 3：实现**

- `FileEntry{name,path,size,is_dir,modified_at}`；`BaseDataSource` 抽象方法 `list_dir/get_file/rename/batch_rename/upload/mkdir/exists`。
- `paths.ensure_allowed(path)`：`realpath` 后必须是白名单根目录或其子路径，否则 `PermissionError`。
- `LocalDataSource`：`list_dir` 用 `os.walk`（recursive）或 `os.scandir`；`rename` 前 `os.path.exists` 检查冲突；`batch_rename` 逐个调用；`upload` 写文件；`exists` 用 `os.path.exists`。
- `factory.get_datasource("local")`；openlist 分支留到任务 4。
- `POST /api/scan`：校验路径 → 列目录 → 过滤视频 → 按 `(source_type, source_ref, openlist_id, original_name)` upsert → 返回 `{files:[MediaFileOut], total, video_count, other_count, elapsed_ms}`。
- `GET /api/directories/tree?path=`：只返回白名单内的目录项 + `parent`。
- `GET /api/files`：返回最近 500 条 `MediaFileOut`。

- [ ] **步骤 4：运行测试确认通过**

运行：`cd backend && uv run pytest tests/test_local_datasource.py -q`；预期全 PASS。

## 任务 4：OpenList 客户端、数据源与管理 API

**文件：**
- 创建：`backend/app/clients/openlist.py`、`backend/app/datasources/openlist.py`、`backend/app/api/datasources.py`、`backend/app/services/crypto.py`
- 修改：`backend/app/datasources/factory.py`、`backend/app/config.py`
- 测试：`backend/tests/test_openlist_client.py`

- [ ] **步骤 1：编写失败的测试**

用 `httpx.MockTransport` 模拟：
- 首次 `list` 自动 `POST /api/auth/login` 并带 `Authorization`。
- 401 后重登一次并重试成功；连续 401 只重试一次。
- `list(recursive=True)` 递归子目录。
- `rename` 请求体为 `{path,name}`；`batch_rename` 体为 `{rename_objects:[{path,new_name}]}`；`upload` 带 `File-Path` 头。
- `POST /api/datasources/openlist` 保存后 GET 不返回明文密码，`has_password=true`。
- `POST .../{id}/test` 登录失败返回 401 且不崩溃。

- [ ] **步骤 2：运行确认失败**

运行：`cd backend && uv run pytest tests/test_openlist_client.py -q`；预期 ImportError。

- [ ] **步骤 3：实现**

- `crypto.py`：Fernet key 取 `ENCRYPTION_KEY`，否则由 `sha256(secret_key)` base64 派生；`encrypt/decrypt`。
- `OpenListClient`：`login`、`_auth_headers`、`_request(method,path,**kw)` 统一处理 401 重登一次、429/5xx 指数退避（0.5s 起，封顶 30s，最多 `openlist_retry` 次）、超时。
- `list` 分页 `per_page=0`，递归；`get`、`rename`、`batch_rename`、`upload`、`mkdir`、`tree`（仅目录）。
- `OpenListDataSource` 实现 base 接口，`exists` 通过父目录 list 判断。
- 工厂 openlist 分支：按 `openlist_id` 读取实例、解密密码、构造 client（进程内缓存）。
- `api/datasources.py`：`GET /api/datasources`（local + 实例）、`POST/PUT/DELETE /api/datasources/openlist/{id}`、`POST .../{id}/test`、`GET .../{id}/tree?path=/`。删除实例时清缓存与 Token。
- 服务地址只接受 `http/https` URL。

- [ ] **步骤 4：运行测试确认通过**

运行：`cd backend && uv run pytest tests/test_openlist_client.py -q`；预期全 PASS。

## 任务 5：重命名引擎、NFO 与预览

**文件：**
- 创建：`backend/app/core/renamer.py`、`backend/app/core/nfo.py`、`backend/app/api/rename.py`（preview 部分）
- 测试：`backend/tests/test_renamer.py`

- [ ] **步骤 1：编写失败的测试**

- 模板 `{title} - S{season:02d}E{episode:02d} - {episode_title}` → `Breaking Bad - S01E03 - ...And the Bag's in the River`。
- 缺失 `episode_title` 时清理悬空分隔符，不残留 ` - .mkv`。
- 未知变量 `{foo}` → 400，提示白名单变量。
- `preview` 对已存在目标文件返回 `status="conflict"`；无匹配返回 `skipped`。
- `generate_episode_nfo` 输出包含 `episodedetails/title/showtitle/season/episode/plot/aired/rating`。
- 模板变量白名单：`title,season,episode,episode_end,episode_title,year,release_group,resolution`。

- [ ] **步骤 2：运行确认失败**

运行：`cd backend && uv run pytest tests/test_renamer.py -q`；预期 ImportError。

- [ ] **步骤 3：实现**

- `RenameEngine.render(ctx, template)`：白名单校验 → `str.format` → 清理重复分隔符与首尾空格 → 追加原扩展名。
- `RenameEngine.preview(files, template)`：读取 `MediaFile.parsed_*` 与 `ScrapeMatch`，组装 context；`episode_title` 优先取刮削结果；输出 `{file_id, original_name, new_name, status, reason}`。
- 冲突检测通过 datasource `exists(parent, new_name)`；同一批次内重名也算冲突。
- `nfo.generate_episode_nfo(match, show_title)` 返回 UTF-8 XML 字符串，含 `<plot>`、`<aired>`、`<rating>`，空值省略。
- `POST /api/rename/preview` 返回预览列表与统计。

- [ ] **步骤 4：运行测试确认通过**

运行：`cd backend && uv run pytest tests/test_renamer.py -q`；预期全 PASS。

## 任务 6：TMDB Provider、搜索/详情/匹配 API

**文件：**
- 创建：`backend/app/providers/{base,tmdb,__init__}.py`、`backend/app/core/matcher.py`、`backend/app/api/scrape.py`
- 测试：`backend/tests/test_tmdb_provider.py`

- [ ] **步骤 1：编写失败的测试**

用 MockTransport 模拟 TMDB：
- `search("绝命毒师")` 映射为 `Show{provider:"tmdb",id,title,year,overview,poster_url,rating,seasons_count}`。
- `get_show(id, season=1)` 返回季元信息与分集列表。
- 未配置 Key 时 `GET /api/search` 返回 400，`detail` 含「未配置 TMDB API Key」。
- `match_file`：标题完全一致 + 年份一致 → 选中；分集存在 → `matched`；分集不存在 → `unmatched`。
- 置信度 <40 不自动选择。

- [ ] **步骤 2：运行确认失败**

运行：`cd backend && uv run pytest tests/test_tmdb_provider.py -q`；预期 ImportError。

- [ ] **步骤 3：实现**

- `providers/base.py`：`Show`、`SeasonInfo`、`EpisodeInfo`、`ShowDetail` dataclass 与 `BaseProvider`。
- `TMDBProvider`：`/search/tv`、`/tv/{id}`、`/tv/{id}/season/{n}`，`language=zh-CN`，图片拼接 `https://image.tmdb.org/t/p/w500`。
- `providers/__init__.py`：注册表，`get_provider(name, api_key)`。
- Key 读取顺序：数据库设置 → 环境变量；缺失抛 `ProviderNotConfigured`（API 层转 400）。
- `matcher.match_files(files, detail, season)`：按 `season_number/episode_number` 对齐，返回 matched/unmatched。
- API：`GET /api/providers`、`GET /api/search?query&provider&year`、`GET /api/shows/{provider}/{show_id}?season=`、`POST /api/match {file_ids, provider, show_id, season}`，匹配结果写 `ScrapeMatch`（upsert by file_id）。

- [ ] **步骤 4：运行测试确认通过**

运行：`cd backend && uv run pytest tests/test_tmdb_provider.py -q`；预期全 PASS。

## 任务 7：任务管理、执行/回滚/重试与 WebSocket

**文件：**
- 创建：`backend/app/services/task_manager.py`、`backend/app/ws.py`、`backend/app/api/tasks.py`
- 修改：`backend/app/api/rename.py`
- 测试：`backend/tests/test_tasks.py`

- [ ] **步骤 1：编写失败的测试**

- execute 本地 3 个文件 → 文件被改名、生成 `.nfo`（写入开启时）、`RenameHistory` 3 条、任务 `completed`。
- 目标冲突项跳过，任务记 2 成功 1 失败/跳过。
- 回滚该任务 → 文件名恢复、历史 `rolled_back=true`。
- 删除其中一个新文件后再回滚 → 该项失败，其余成功，该历史保持 `rolled_back=false`。
- 重试失败任务 → 生成新任务且只包含失败项。
- WS `/ws/tasks/{id}` 至少收到一条 `progress` 消息（completed 后关闭）。

- [ ] **步骤 2：运行确认失败**

运行：`cd backend && uv run pytest tests/test_tasks.py -q`；预期 ImportError。

- [ ] **步骤 3：实现**

- `TaskManager`：进程内 `dict[str, asyncio.Task]`；`run_rename(file_ids, template, write_nfo, download_posters)` 创建 `TaskRecord` + `TaskItem`，后台协程逐项处理并更新计数、广播。
- 执行顺序：解析 context → 冲突检查 → `datasource.rename` → 可选 NFO `upload` → 可选海报（仅 local，保存 `{stem}-thumb.jpg`）→ 写 `RenameHistory`。
- OpenList 且可执行项 >1 时先 `batch_rename`；若抛错则降级为逐项执行，保证逐项状态。
- 每项异常捕获并写 `TaskItem.error`，继续下一项；任务最终 `completed`（含失败）或 `failed`（整体异常）。
- `POST /api/rename/execute` 返回 `{task_id, total}`；`POST /api/rename/rollback {task_id?}` 默认最近未回滚任务，逐项恢复。
- `POST /api/tasks/{id}/retry` 复制失败项为新任务。
- `GET /api/tasks`、`GET /api/tasks/{id}`（含 items）；`ws.py` 维护 `task_id -> set[WebSocket]`，断连自动移除。

- [ ] **步骤 4：运行测试确认通过**

运行：`cd backend && uv run pytest tests/test_tasks.py -q`；预期全 PASS。

## 任务 8：设置 API

**文件：**
- 创建：`backend/app/services/settings.py`、`backend/app/api/settings.py`
- 测试：`backend/tests/test_settings.py`

- [ ] **步骤 1：编写失败的测试**

- GET 返回 `rename_template`、`allowed_paths`、`openlist_*`、`has_tmdb_key`，绝不返回 Key 明文。
- PUT `{tmdb_api_key:"abc"}` 后 `has_tmdb_key=true`，DB 中为密文。
- PUT `{tmdb_api_key:""}` 不覆盖已有 Key。
- PUT 非法模板变量 → 400。

- [ ] **步骤 2：运行确认失败**

运行：`cd backend && uv run pytest tests/test_settings.py -q`；预期 ImportError。

- [ ] **步骤 3：实现**

`settings` 服务：`get_setting/set_setting`（key-value 表），`get_effective(key)` 回退到环境配置。
`PUT /api/settings` 允许字段：`tmdb_api_key`、`rename_template`、`allowed_paths`、`openlist_concurrency`、`openlist_timeout`、`openlist_retry`；模板校验复用 `renamer` 白名单。

- [ ] **步骤 4：运行测试确认通过**

运行：`cd backend && uv run pytest tests -q`；预期全 PASS。

## 任务 9：前端脚手架、主题与 AppShell

**文件：**
- 创建：`frontend/package.json`、`vite.config.ts`、`tsconfig.json`、`index.html`、`src/{main,App}.ts/vue`、`style.css`、`router/index.ts`、`api/client.ts`、`types.ts`、`stores/workflow.ts`、`components/{AppShell,StepNav,StatusTag,EmptyState}.vue`
- 验证：`npm run build`

- [ ] **步骤 1：初始化工程**

`npm create vite@latest`（vue-ts）后安装：`vue-router pinia axios`、`tailwindcss @tailwindcss/vite`。不安装 Element Plus。

- [ ] **步骤 2：实现主题与外壳**

- `style.css`：`@import "tailwindcss";` + `@theme` 映射 CSS 变量；`:root[data-theme="dark"]` 与 `light` 两套 token，数值照 `frontend-layout-design.md §4.1`；全局网格背景、滚动条、focus-visible。
- `AppShell.vue`：56px TopBar（Logo、StepNav、任务/设置/主题按钮）+ 224px SideNav（徽标计数、激活左强调条、可折叠 64px）+ 内容区（max-width 1440、padding 24）；<1024px 折叠侧栏。
- `StepNav.vue`：四步状态（done/active/disabled）+ 计数，禁用时 tooltip 说明。
- `workflow.ts`：状态 `files/selectedIds/source/currentShow/preview/tasks/settings`；getters `videoFiles/parsedFiles/matchedFiles/readyFiles/stepCounts`；actions 调 API 并同步本地文件状态。

- [ ] **步骤 3：验证**

运行：`cd frontend && npm run build`；预期构建成功，无 TS 错误。

## 任务 10：扫描页与数据源组件

**文件：**
- 创建：`frontend/src/views/ScanView.vue`、`components/{DataSourceSwitch,PathPicker,DirectoryBrowser,FileTable,BatchBar}.vue`
- 修改：`router/index.ts`、`stores/workflow.ts`

- [ ] **步骤 1：实现扫描页**

- 顶部数据源切换（本地/OpenList）；OpenList 未配置时展示空态与「去配置」。
- PathPicker：Mono 输入 + 浏览 + 递归开关；DirectoryBrowser 弹窗支持本地/云盘树、面包屑、目录优先排序、双击进入、选择当前目录。
- FileTable：多选、列排序、文件名 Mono 省略 + tooltip、来源标签、状态列、仅看视频与状态筛选。
- 统计条：总数/视频/其他/解析失败；扫描中骨架屏 + 进度条。
- BatchBar：已选数量、清空、下一步解析；`Esc` 清空。

- [ ] **步骤 2：联调**

`npm run dev`（后端同时运行），扫描测试目录能看到文件；切换数据源清空选择并提示。

## 任务 11：解析页

**文件：**
- 创建：`frontend/src/views/ParseView.vue`、`components/{ConfidenceBadge,ParseForm}.vue`
- 修改：`stores/workflow.ts`

- [ ] **步骤 1：实现**

- 左右分栏（320px 列表 + 详情），左列表状态点 + 置信度、筛选「全部/待确认/失败」、`j/k` 切换、`space` 选中。
- 右侧原始文件名 Mono 块、可编辑字段（剧名/年份/季/集/集标题/分辨率/编码/发布组）。
- 置信度徽标：≥85 绿/高，60–84 黄/待确认，<60 红/低；低置信度字段黄框提示。
- 「重新自动解析」「保存并下一项」「批量自动解析」「全部接受」「应用到本季其他集」（确认弹窗列出影响数量）。

- [ ] **步骤 2：联调**

解析接口写回后列表状态更新；刷新页面通过 `GET /api/files` 恢复。

## 任务 12：刮削页

**文件：**
- 创建：`frontend/src/views/ScrapeView.vue`、`components/{ShowCard,EpisodeMapper}.vue`

- [ ] **步骤 1：实现**

- 搜索栏：关键词 + 媒体源 + 年份；回车搜索；最近搜索标签（localStorage）。
- 左栏待匹配文件；中栏候选卡片（2:3 海报、标题、年份、评分、季数，hover 抬升）；右栏映射表。
- 选中剧集后选择季，调用详情接口，自动按集号对齐；失败行标黄并可手动指定。
- 「确认匹配」调用 `/api/match`，更新文件状态；未配置 Key 显示 `el-alert` + 去设置。

- [ ] **步骤 2：联调**

无 Key 时错误提示清晰；后端有 Key 时搜索/匹配可用（无真实 Key 时验证错误分支）。

## 任务 13：重命名页

**文件：**
- 创建：`frontend/src/views/RenameView.vue`、`components/{TemplateEditor,DiffText}.vue`

- [ ] **步骤 1：实现**

- TemplateEditor：Mono 输入、变量 chips 插入、非法变量红字、实时示例取当前选中行。
- DiffTable：原/新文件名、字符级差异高亮（新名变更段 success 色）、冲突行黄底 + 展开「保留两者/覆盖/跳过」（MVP：覆盖禁用，保留两者追加序号，跳过）。
- 统计条：可执行/冲突/跳过/数据源。
- 「仅预览」调 preview；「执行重命名」二次确认（数量、数据源、是否写 NFO）后创建任务并轮询/WS 跟踪行内状态；「撤销上次」确认后调 rollback；完成后结果条 + 查看任务/撤销。
- OpenList 且 >1 项时提示将使用 batch_rename。

- [ ] **步骤 2：联调**

本地测试目录完整跑通 preview → execute → rollback；冲突文件不被覆盖。

## 任务 14：任务中心与设置页

**文件：**
- 创建：`frontend/src/views/{TasksView,SettingsView}.vue`、`components/TaskProgress.vue`

- [ ] **步骤 1：任务中心**

表格（类型/数据源/进度/成功失败/状态/时间/详情）、类型筛选、刷新；运行中任务建 WS 连接，失败回退 2s 轮询；详情抽屉列出逐项结果与错误，支持「重试失败项」。

- [ ] **步骤 2：设置页**

左侧 Tab（媒体源 / OpenList / 命名模板 / 通用）+ 右侧表单。
- 媒体源：TMDB Key（占位显示已配置/未配置，不回显）、保存、测试状态提示。
- OpenList：实例卡片（名称/地址/连接状态/测试/编辑/删除）；新增编辑弹窗（名称、地址、用户名、密码、超时、并发）；删除二次确认提示引用数量。
- 命名模板：模板列表/默认模板、变量说明表。
- 通用：目录白名单编辑、并发/超时/重试参数。

- [ ] **步骤 3：验证**

`npm run build` 通过；实例增删改测走通（无真实 OpenList 时验证失败态）。

## 任务 15：端到端验证

- [ ] **步骤 1：后端全量测试**

运行：`cd backend && uv run pytest tests -q`；预期全 PASS。

- [ ] **步骤 2：前端构建**

运行：`cd frontend && npm run build`；预期成功。

- [ ] **步骤 3：启动联调**

后端：`cd backend && uv run uvicorn app.main:app --port 8000`；前端：`cd frontend && npm run dev`。
创建临时演示目录（`/tmp/episode-demo/Show/Season 01/*.mkv`），把该目录加入 `ALLOWED_PATHS`。
浏览器验证：扫描 → 解析 → 重命名预览 → 执行 → 任务中心 → 撤销；检查深色/浅色主题、空态、冲突提示、移动端只读降级。

- [ ] **步骤 4：验收记录**

记录通过项、受限项（无真实 TMDB Key、无在线 OpenList 实例时的降级表现）与遗留问题。
