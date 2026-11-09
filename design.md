# OpenList 影视剧剧集重命名与刮削系统 — 设计文档

> 版本：v1.1　|　技术栈：前端 Vue 3 + 后端 Python 3.11　|　文档类型：系统设计文档
>
> v1.1 更新：新增 **OpenList 网盘数据源** 支持，系统同时处理本地文件与 OpenList 挂载的云盘文件。

---

## 1. 项目概述

### 1.1 项目背景

影视剧爱好者在下载剧集后，本地文件名往往杂乱无章，例如：

- `Breaking.Bad.S01E01.1080p.BluRay.x264.mkv`
- `绝命毒师 第1季 第02集.mp4`
- `s01e03.pilot.hdtv.mkv`

这类文件难以被 Plex / Emby / Jellyfin 等媒体服务器正确识别，也不利于本地整理。**剧集重命名**与**剧集刮削**是媒体库管理的基础能力：

- **重命名（Rename）**：从文件名中解析出剧名、季、集等关键信息，按统一规则重命名。
- **刮削（Scrape）**：从 TMDB / TVDB / 豆瓣等在线元数据库拉取剧集详情（标题、简介、播出日期、海报、缩略图等），写入本地 `.nfo` 文件或媒体库。

### 1.2 项目目标

构建一个 **Web 化** 的剧集重命名与刮削工具，同时支持 **本地文件系统** 与 **OpenList 网盘数据源**：

1. 用户在浏览器中选择数据源（本地目录或 OpenList 云盘路径），系统扫描并解析文件名。
2. 用户可手动修正解析结果，或选择自动匹配的剧集元数据。
3. 一键执行重命名并生成 `.nfo` 元数据文件，兼容主流媒体服务器。
4. 全程可预览、可回滚，避免误操作。
5. 通过 OpenList API 直接操作云盘文件（列目录、重命名、上传 NFO），无需下载到本地。

### 1.2.1 OpenList 数据源说明

[OpenList](https://doc.oplist.org/) 是一个开源的网盘聚合服务（基于 AList），可挂载阿里云盘、115、百度网盘等多种云存储，并对外提供统一的 REST API。其文件系统接口（`/api/fs/*`）与 AList 兼容，核心能力包括：

| 能力 | 接口 | 说明 |
|---|---|---|
| 登录鉴权 | `POST /api/auth/login` | 用户名密码获取 JWT Token |
| 列出目录 | `POST /api/fs/list` | 按路径分页列出文件 |
| 获取文件详情 | `POST /api/fs/get` | 获取单个文件的元信息 |
| 重命名文件 | `POST /api/fs/rename` | 原地重命名（`{path, name}`） |
| 批量重命名 | `POST /api/fs/batch_rename` | 批量重命名多个文件 |
| 正则重命名 | `POST /api/fs/regex_rename` | 按正则规则批量重命名 |
| 移动文件 | `POST /api/fs/move` | 移动/跨目录重命名 |
| 创建目录 | `POST /api/fs/mkdir` | 新建文件夹 |
| 上传文件 | `PUT /api/fs/put` | 流式上传（用于写入 NFO） |
| 删除文件 | `POST /api/fs/remove` | 删除文件或文件夹 |

> 本系统通过 OpenList 的 `/api/fs/*` 接口实现云盘文件的扫描、重命名与 NFO 写入，复用与本地文件系统相同的解析/刮削/重命名核心逻辑。

### 1.3 术语定义

| 术语 | 说明 |
|---|---|
| 刮削（Scrape） | 从在线元数据库获取剧集元数据的过程 |
| 重命名（Rename） | 按规则将文件名改为标准化格式 |
| NFO | Kodi/Emby/Jellyfin 采用的 XML 元数据文件 |
| 季（Season）/ 集（Episode） | 剧集结构层级 |
| 媒体源（Provider） | 元数据提供方，如 TMDB、TVDB、豆瓣 |
| 数据源（DataSource） | 文件存储来源，分为 `local`（本地文件系统）和 `openlist`（OpenList 云盘） |
| 解析（Parse） | 从文件名提取剧名、季、集、年份等字段 |
| OpenList | 开源网盘聚合服务，提供统一 `/api/fs/*` 文件系统 API |

---

## 2. 需求分析

### 2.1 功能需求

#### F1. 目录扫描与文件识别
- 支持选择 **数据源**：本地目录 或 OpenList 云盘路径。
- 本地数据源：递归扫描指定目录下的视频文件。
- OpenList 数据源：通过 `POST /api/fs/list` 递归列出云盘目录下的视频文件。
- 支持的视频扩展名：`.mkv .mp4 .avi .mov .wmv .flv .ts .webm`。
- 自动过滤非视频文件（字幕、种子等可单独显示）。
- 扫描结果统一抽象为 `MediaFile`，携带 `source_type`（local/openlist）与 `source_ref`（本地路径或 OpenList 路径）。

#### F1.1 数据源管理（OpenList）
- 配置 OpenList 服务地址（如 `https://fox.oplist.org`）、用户名、密码。
- 后端调用 `POST /api/auth/login` 获取并缓存 JWT Token，Token 过期自动刷新。
- 支持多个 OpenList 实例配置（多网盘账号）。
- 测试连接：验证账号可用性与 Token 获取。

#### F2. 文件名解析
- 从文件名自动提取：剧名、年份、季号、集号、集标题、分辨率、编码、发布组。
- 支持中英文剧名、多季多集（`S01E01-E02`）、特殊集（`S00`）。
- 解析结果可人工编辑修正。

#### F3. 在线刮削
- 调用 TMDB / TVDB / 豆瓣 API 搜索匹配剧集。
- 返回候选剧集列表，用户选择或自动选择置信度最高的一项。
- 拉取剧集详情：标题、简介、首播日期、评分、海报、季集信息。

#### F4. 重命名
- 可配置命名模板，例如 `{剧名} - S{季:02d}E{集:02d} - {集标题}`。
- 支持预览重命名前后的文件名对比。
- 支持 dry-run（仅预览不执行）。
- 执行后支持撤销（恢复原文件名）。
- **本地数据源**：通过 `os.rename` 原地重命名。
- **OpenList 数据源**：通过 `POST /api/fs/rename` 原地重命名；批量操作优先使用 `POST /api/fs/batch_rename` 以减少请求次数。

#### F5. 元数据写入
- 生成剧集 `.nfo` 文件（Kodi 兼容格式）。
- 下载海报、缩略图到本地（可选）。
- 与视频文件同名，供媒体服务器识别。
- **本地数据源**：直接写入同目录 `.nfo` 文件。
- **OpenList 数据源**：通过 `PUT /api/fs/put` 将 NFO 内容流式上传到视频文件同目录，文件名与视频同名（扩展名 `.nfo`）。

#### F6. 任务管理
- 重命名与刮削作为后台任务执行。
- 显示进度、成功/失败计数。
- 失败项可重试。

#### F7. 配置管理
- 媒体源（Provider）API Key 配置（TMDB / TVDB / 豆瓣）。
- 命名模板配置。
- 目录黑白名单（本地数据源）。
- OpenList 数据源配置：服务地址、用户名、密码（加密存储）。

#### F8. 数据源抽象
- 定义统一的 `DataSource` 接口：`list_dir`、`get_file`、`rename`、`upload`、`mkdir`。
- 实现两个数据源：`LocalDataSource`（本地文件系统）、`OpenListDataSource`（OpenList API）。
- 上层业务（解析/刮削/重命名）仅依赖 `DataSource` 接口，不感知具体存储位置。

### 2.2 非功能需求

| 类别 | 要求 |
|---|---|
| 性能 | 本地扫描 1000 文件 < 5s；OpenList 扫描受网络与 API 限流约束，分页并发可控；刮削并发可控 |
| 可用性 | 所有写操作（重命名、写 NFO）必须可预览、可回滚；OpenList Token 过期自动重登 |
| 兼容性 | NFO 兼容 Kodi / Emby / Jellyfin；命名规则可自定义；OpenList API 兼容 AList `/api/fs/*` 规范 |
| 可扩展性 | 媒体源与数据源均以插件形式接入，新增源不修改核心代码 |
| 安全性 | API Key / OpenList 密码加密存储；本地仅允许访问授权目录；OpenList 凭证不暴露给前端 |

### 2.3 用户角色

| 角色 | 说明 |
|---|---|
| 普通用户 | 使用重命名与刮削功能的最终用户 |
| 管理员 | 配置 API Key、目录权限、模板等系统级参数 |

---

## 3. 总体架构设计

### 3.1 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      浏览器 (Vue 3)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ 扫描页   │ │ 解析页   │ │ 刮削页   │ │ 任务/配置  │  │
│  │(数据源选) │ │          │ │          │ │(OpenList配)│  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘  │
│       └────────────┴────────────┴──────────────┘        │
│                         │ HTTP / WebSocket               │
└─────────────────────────┼───────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────┐
│                   Python 后端 (FastAPI)                  │
│  ┌──────────────────────┴────────────────────────────┐   │
│  │                    API Layer                       │   │
│  │   REST API + WebSocket (任务进度推送)               │   │
│  └──────────────────────┬────────────────────────────┘   │
│  ┌──────────────────────┴────────────────────────────┐   │
│  │                  Service Layer                     │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐  │   │
│  │  │ 解析器 │ │ 刮削器 │ │ 重命名 │ │ 任务调度   │  │   │
│  │  └────────┘ └────────┘ └────────┘ └────────────┘  │   │
│  └──────────────────────┬────────────────────────────┘   │
│  ┌──────────────────────┼────────────────────────────┐   │
│  │        Provider 层  │      DataSource 层           │   │
│  │  TMDB TVDB 豆瓣     │  ┌────────┐ ┌────────────┐  │   │
│  │  (元数据刮削)        │  │ Local  │ │ OpenList   │  │   │
│  │                     │  │ 文件系统│ │ 网盘数据源 │  │   │
│  │                     │  └────────┘ └─────┬──────┘  │   │
│  └─────────────────────┴────────────────────┼──────────┘   │
│  ┌──────────────────────────────────────────┼──────────┐   │
│  │              Data / Storage Layer         │          │   │
│  │   SQLite/PostgreSQL   本地缓存            │          │   │
│  └──────────────────────────────────────────┼──────────┘   │
└──────────────────────────────────────────────┼────────────┘
                                               │ HTTPS
                                               ▼
                                    ┌─────────────────────┐
                                    │   OpenList 服务端    │
                                    │  /api/fs/* 接口      │
                                    │  (阿里云盘/115/...)  │
                                    └─────────────────────┘
```

**数据源层（DataSource）** 与 **媒体源层（Provider）** 是两个独立的插件体系：
- **DataSource**：解决"文件在哪里"——本地文件系统 或 OpenList 云盘。
- **Provider**：解决"元数据从哪来"——TMDB / TVDB / 豆瓣。

### 3.2 技术栈选型

**前端：**

| 类别 | 选型 | 理由 |
|---|---|---|
| 框架 | Vue 3 + `<script setup>` | 组合式 API，轻量灵活 |
| 构建工具 | Vite | 启动快、HMR 体验好 |
| 路由 | Vue Router 4 | 官方方案 |
| 状态管理 | Pinia | Vue 3 官方推荐，轻量 |
| UI 组件库 | Element Plus | 成熟、组件丰富、适合后台工具 |
| HTTP | Axios | 拦截器、请求取消 |
| 实时通信 | 原生 WebSocket | 任务进度推送 |

**后端：**

| 类别 | 选型 | 理由 |
|---|---|---|
| Web 框架 | FastAPI | 异步、自动文档、类型提示 |
| ASGI 服务器 | Uvicorn | 与 FastAPI 配套 |
| 异步任务 | asyncio + 自建队列（轻量）/ Celery（可选） | MVP 用 asyncio，避免过重依赖 |
| 数据库 | SQLite（MVP）/ PostgreSQL（生产） | ORM 用 SQLModel |
| HTTP 客户端 | httpx（异步） | 调用媒体源 API |
| 文件名解析 | 自研 + 正则 + guessit（可选） | guessit 成熟但需校验 |
| 配置 | Pydantic Settings | 类型安全 |
| 日志 | loguru | 结构化日志 |

### 3.3 模块划分

```
episode-scrap/
├── frontend/                 # Vue 前端
│   ├── src/
│   │   ├── views/            # 页面（含数据源选择）
│   │   ├── components/       # 组件
│   │   ├── stores/           # Pinia store
│   │   ├── api/              # API 封装
│   │   ├── router/           # 路由
│   │   └── utils/            # 工具函数
│   └── ...
└── backend/                  # Python 后端
    ├── app/
    │   ├── api/              # 路由层
    │   ├── core/             # 核心：解析、刮削、重命名、NFO
    │   ├── providers/        # 媒体源插件（TMDB/TVDB/豆瓣）
    │   ├── datasources/      # 数据源插件 ★新增
    │   │   ├── base.py       # DataSource 抽象基类
    │   │   ├── local.py      # 本地文件系统
    │   │   └── openlist.py   # OpenList 网盘
    │   ├── clients/          # 外部客户端 ★新增
    │   │   └── openlist.py   # OpenList API 客户端
    │   ├── models/           # 数据模型
    │   ├── schemas/          # Pydantic schema
    │   ├── services/         # 业务服务
    │   ├── tasks/            # 后台任务
    │   └── config.py         # 配置
    └── ...
```

---

## 4. 前端设计（Vue）

### 4.1 页面结构与路由

| 路由 | 页面 | 说明 |
|---|---|---|
| `/` | 扫描页 | 选择目录、扫描文件 |
| `/parse` | 解析页 | 展示解析结果、手动修正 |
| `/scrape` | 刮削页 | 搜索匹配剧集、选择元数据 |
| `/rename` | 重命名页 | 预览命名、执行/回滚 |
| `/tasks` | 任务页 | 查看任务进度与历史 |
| `/settings` | 设置页 | API Key、模板、目录配置 |

### 4.2 核心页面设计

#### 扫描页
- **数据源选择器**：顶部切换「本地」/「OpenList」。
  - 本地：目录选择器（输入路径或后端目录树）。
  - OpenList：下拉选择已配置的 OpenList 实例 + 云盘路径输入（支持浏览选择）。
- 扫描按钮：调用 `POST /api/scan`（携带 `source_type` 与 `source_ref`），返回文件列表。
- 文件列表：表格展示原文件名、大小、修改时间、数据源标记。

#### 解析页
- 左侧：文件列表（未解析 / 已解析状态）。
- 右侧：当前选中文件的解析结果表单。
  - 剧名、年份、季、集、集标题（可编辑）。
  - "自动解析"按钮重新解析。
  - "批量应用"将规则应用到同季其他集。

#### 刮削页
- 顶部：搜索框（输入剧名，调用 `GET /api/search`）。
- 候选列表：卡片展示候选剧集（海报、标题、年份、简介）。
- 选中后展示季集详情，与本地文件做匹配预览。

#### 重命名页
- 模板编辑器：可视化编辑命名模板，实时预览。
- 对比表格：原文件名 → 新文件名（标注数据源）。
- 操作按钮：Dry-run / 执行 / 撤销。
- OpenList 批量重命名提示：当数据源为 OpenList 且文件数较多时，提示将使用 `batch_rename` 接口。

#### 设置页
- 媒体源 API Key 配置（TMDB / TVDB / 豆瓣）。
- 命名模板配置。
- 本地目录黑白名单。
- **OpenList 数据源配置**（新增）：
  - 实例列表（名称、服务地址、用户名）。
  - 新增/编辑：服务地址、用户名、密码、测试连接按钮。
  - 删除实例。

### 4.3 状态管理（Pinia）

```typescript
// stores/files.ts
type SourceType = 'local' | 'openlist';

interface MediaFile {
  id: string;
  sourceType: SourceType;       // 数据源类型
  sourceRef: string;            // 本地路径 或 OpenList 云盘路径
  openlistId?: string;          // OpenList 数据源时：实例 ID
  originalName: string;
  size: number;
  parsed: ParsedInfo | null;    // 解析结果
  scrapeTarget: ScrapeInfo | null; // 刮削匹配
  newName: string | null;       // 重命名结果
  status: 'pending' | 'parsed' | 'matched' | 'renamed' | 'error';
}

export const useFileStore = defineStore('files', () => {
  const files = ref<MediaFile[]>([]);
  const selectedId = ref<string | null>(null);
  const currentSource = ref<{ type: SourceType; ref: string; openlistId?: string }>(
    { type: 'local', ref: '' }
  );
  // ... actions: scan, parse, scrape, rename, rollback
});
```

### 4.4 关键交互流程

```
选择数据源(本地/OpenList) → 扫描 → 自动解析 → 人工修正 → 搜索刮削 → 选择元数据 → 预览重命名 → 执行
```

每一步失败都不阻塞后续操作，用户可回退修正。数据源在扫描时确定，同一批文件必须来自同一数据源（避免混淆回滚映射）。

---

## 5. 后端设计（Python）

### 5.1 API 设计

#### 数据源管理（OpenList）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/datasources` | 列出所有数据源（本地 + 已配置的 OpenList 实例） |
| POST | `/api/datasources/openlist` | 新增 OpenList 实例（服务地址、用户名、密码） |
| PUT | `/api/datasources/openlist/{id}` | 更新 OpenList 实例配置 |
| DELETE | `/api/datasources/openlist/{id}` | 删除 OpenList 实例 |
| POST | `/api/datasources/openlist/{id}/test` | 测试连接（登录验证） |
| GET | `/api/datasources/openlist/{id}/tree?path=/` | 浏览 OpenList 云盘目录树 |

#### 目录与扫描

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/directories/tree` | 获取本地可选目录树（受白名单限制） |
| POST | `/api/scan` | 扫描目录，返回视频文件列表。Body: `{source_type, source_ref, openlist_id?}` |

#### 解析

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/parse` | 解析单个/批量文件名 |
| PUT | `/api/parse/{file_id}` | 手动更新解析结果 |

#### 刮削

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/providers` | 列出可用媒体源 |
| GET | `/api/search?query=&provider=` | 搜索剧集 |
| GET | `/api/shows/{provider}/{show_id}` | 获取剧集详情（含季集） |
| POST | `/api/match` | 将本地文件与剧集季集匹配 |

#### 重命名

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/rename/preview` | 预览重命名结果（dry-run），支持所有数据源 |
| POST | `/api/rename/execute` | 执行重命名。OpenList 批量时自动调用 `batch_rename` |
| POST | `/api/rename/rollback` | 回滚重命名。OpenList 再次调用 `rename` 恢复原名 |

#### 任务

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/tasks` | 任务列表 |
| GET | `/api/tasks/{task_id}` | 任务详情 |
| WebSocket | `/ws/tasks/{task_id}` | 任务进度推送 |

#### 配置

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/settings` | 获取配置 |
| PUT | `/api/settings` | 更新配置 |

### 5.2 核心模块设计

#### 5.2.0 数据源抽象层（DataSource）★新增

**职责**：统一本地文件系统与 OpenList 网盘的文件操作接口，上层业务不感知存储位置。

```python
# app/datasources/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class FileEntry:
    name: str
    path: str          # 完整路径（本地绝对路径 或 OpenList 云盘路径）
    size: int
    is_dir: bool
    modified_at: str | None

class BaseDataSource(ABC):
    name: str  # "local" or "openlist"

    @abstractmethod
    async def list_dir(self, path: str, recursive: bool = False) -> list[FileEntry]: ...

    @abstractmethod
    async def get_file(self, path: str) -> FileEntry | None: ...

    @abstractmethod
    async def rename(self, path: str, new_name: str) -> None: ...

    @abstractmethod
    async def batch_rename(self, items: list[tuple[str, str]]) -> None:
        """批量重命名：[(原路径, 新文件名), ...]"""
        ...

    @abstractmethod
    async def upload(self, path: str, content: bytes, filename: str) -> None:
        """上传/写入文件（用于 NFO）"""
        ...

    @abstractmethod
    async def mkdir(self, path: str) -> None: ...
```

**本地数据源实现**：

```python
# app/datasources/local.py
import os

class LocalDataSource(BaseDataSource):
    name = "local"

    async def list_dir(self, path, recursive=False):
        entries = []
        for root, dirs, files in os.walk(path) if recursive else [(path, [], os.listdir(path))]:
            for f in files:
                full = os.path.join(root, f)
                entries.append(FileEntry(
                    name=f, path=full, size=os.path.getsize(full),
                    is_dir=False, modified_at=os.path.getmtime(full),
                ))
        return entries

    async def rename(self, path, new_name):
        new_path = os.path.join(os.path.dirname(path), new_name)
        os.rename(path, new_path)

    async def upload(self, path, content, filename):
        with open(os.path.join(path, filename), "wb") as f:
            f.write(content)
    ...
```

**OpenList 数据源实现**：

```python
# app/datasources/openlist.py
from app.clients.openlist import OpenListClient

class OpenListDataSource(BaseDataSource):
    name = "openlist"

    def __init__(self, client: OpenListClient):
        self.client = client

    async def list_dir(self, path, recursive=False):
        # recursive=True 时递归调用 fs/list
        return await self.client.list(path, recursive=recursive)

    async def rename(self, path, new_name):
        await self.client.rename(path, new_name)

    async def batch_rename(self, items):
        # 调用 OpenList batch_rename 接口
        await self.client.batch_rename(items)

    async def upload(self, path, content, filename):
        # PUT /api/fs/put 流式上传 NFO
        await self.client.upload(path, filename, content)
    ...
```

**数据源工厂**：

```python
# app/datasources/factory.py
_DATASOURCES: dict[str, BaseDataSource] = {}

def get_datasource(source_type: str, **kwargs) -> BaseDataSource:
    if source_type == "local":
        return LocalDataSource()
    elif source_type == "openlist":
        instance = get_openlist_instance(kwargs["openlist_id"])
        return OpenListDataSource(client=instance.client)
    raise ValueError(f"Unknown datasource: {source_type}")
```

#### 5.2.0.1 OpenList API 客户端 ★新增

**职责**：封装 OpenList `/api/fs/*` 与 `/api/auth/login` 接口，管理 Token 生命周期。

```python
# app/clients/openlist.py
import httpx

class OpenListClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._token: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _ensure_token(self):
        if not self._token:
            await self.login()

    async def login(self) -> str:
        r = await self._client.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self.username, "password": self.password},
        )
        r.raise_for_status()
        self._token = r.json()["data"]["token"]
        return self._token

    async def _auth_headers(self) -> dict:
        await self._ensure_token()
        return {"Authorization": self._token}

    async def list(self, path: str, page: int = 1, per_page: int = 0,
                   recursive: bool = False) -> list[FileEntry]:
        """POST /api/fs/list"""
        r = await self._client.post(
            f"{self.base_url}/api/fs/list",
            headers=await self._auth_headers(),
            json={"path": path, "page": page, "per_page": per_page, "refresh": False},
        )
        r.raise_for_status()
        items = r.json()["data"]["content"]
        entries = [FileEntry(
            name=i["name"], path=f"{path.rstrip('/')}/{i['name']}",
            size=i.get("size", 0), is_dir=i["is_dir"],
            modified_at=i.get("modified"),
        ) for i in items]
        if recursive:
            # 递归遍历子目录
            for entry in list(entries):
                if entry.is_dir:
                    entries.extend(await self.list(entry.path, recursive=True))
        return entries

    async def rename(self, path: str, new_name: str):
        """POST /api/fs/rename  — 原地重命名"""
        r = await self._client.post(
            f"{self.base_url}/api/fs/rename",
            headers=await self._auth_headers(),
            json={"path": path, "name": new_name},
        )
        r.raise_for_status()

    async def batch_rename(self, items: list[tuple[str, str]]):
        """POST /api/fs/batch_rename"""
        r = await self._client.post(
            f"{self.base_url}/api/fs/batch_rename",
            headers=await self._auth_headers(),
            json={"rename_objects": [
                {"path": p, "new_name": n} for p, n in items
            ]},
        )
        r.raise_for_status()

    async def upload(self, dir_path: str, filename: str, content: bytes):
        """PUT /api/fs/put — 流式上传文件"""
        r = await self._client.put(
            f"{self.base_url}/api/fs/put",
            headers={**await self._auth_headers(),
                     "File-Path": f"{dir_path.rstrip('/')}/{filename}",
                     "Content-Type": "application/octet-stream"},
            content=content,
        )
        r.raise_for_status()

    async def mkdir(self, path: str):
        """POST /api/fs/mkdir"""
        r = await self._client.post(
            f"{self.base_url}/api/fs/mkdir",
            headers=await self._auth_headers(),
            json={"path": path},
        )
        r.raise_for_status()
```

**Token 过期处理**：OpenList 返回 401 时，自动调用 `login()` 刷新 Token 并重试一次（仅重试一次，避免死循环）。

#### 5.2.1 解析器（Parser）

**职责**：从文件名提取结构化信息。

```python
# app/core/parser.py
from dataclasses import dataclass
import re

@dataclass
class ParsedInfo:
    title: str | None
    year: int | None
    season: int | None
    episode: int | None
    episode_end: int | None      # 多集，如 E01-E02
    episode_title: str | None
    resolution: str | None       # 1080p
    codec: str | None            # x264
    release_group: str | None
    raw: str                     # 原始文件名

class FilenameParser:
    PATTERNS = [
        # S01E02 / s1e2
        r'(?P<title>.+?)[.\s_-]+S(?P<season>\d{1,2})E(?P<episode>\d{1,2})(?:-E(?P<episode_end>\d{1,2}))?',
        # 1x02
        r'(?P<title>.+?)[.\s_-]+(?P<season>\d{1,2})x(?P<episode>\d{1,2})',
        # 第X季第Y集
        r'(?P<title>.+?)第(?P<season>\d+)季.*?第(?P<episode>\d+)集',
    ]

    def parse(self, filename: str) -> ParsedInfo:
        # 1. 去扩展名
        # 2. 依次尝试 PATTERNS
        # 3. 清理 title（去除分辨率、编码、发布组等噪声）
        # 4. 返回 ParsedInfo
        ...
```

**解析策略**：
1. 正则匹配优先，按置信度排序。
2. 标题清洗：去除 `1080p`、`BluRay`、`x264`、`WEB-DL` 等已知标签。
3. 中文剧名识别：保留中文字符，去除季集描述。
4. 失败时返回 `title=None`，标记需人工处理。

#### 5.2.2 刮削器（Scraper）

**职责**：统一封装不同媒体源的 API。

```python
# app/providers/base.py
from abc import ABC, abstractmethod

class BaseProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, year: int | None = None) -> list[Show]: ...

    @abstractmethod
    async def get_show(self, show_id: str) -> ShowDetail: ...

    @abstractmethod
    async def get_episode(self, show_id: str, season: int, episode: int) -> EpisodeInfo: ...
```

**媒体源实现**（以 TMDB 为例）：

```python
# app/providers/tmdb.py
import httpx

class TMDBProvider(BaseProvider):
    name = "tmdb"
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(base_url=self.BASE_URL)

    async def search(self, query, year=None):
        params = {"api_key": self.api_key, "query": query}
        if year:
            params["first_air_date_year"] = year
        r = await self.client.get("/search/tv", params=params)
        return [self._to_show(item) for item in r.json()["results"]]

    async def get_show(self, show_id):
        r = await self.client.get(f"/tv/{show_id}", params={"api_key": self.api_key})
        return self._to_show_detail(r.json())
    ...
```

**Provider 注册**：通过配置启用/禁用，动态加载。

```python
# app/providers/__init__.py
_PROVIDERS: dict[str, BaseProvider] = {}

def register(provider: BaseProvider):
    _PROVIDERS[provider.name] = provider

def get_provider(name: str) -> BaseProvider:
    return _PROVIDERS[name]
```

#### 5.2.3 重命名引擎（Renamer）

**职责**：根据模板生成新文件名，通过 `DataSource` 抽象层执行重命名（本地 `os.rename` / OpenList `fs/rename`）。

```python
# app/core/renamer.py
import os
from app.datasources.base import BaseDataSource

class RenameEngine:
    def __init__(self, template: str, datasource: BaseDataSource):
        self.template = template  # 例如 "{title} - S{season:02d}E{episode:02d} - {episode_title}"
        self.ds = datasource

    def preview(self, parsed: ParsedInfo, scrape: EpisodeInfo) -> str:
        ctx = {
            "title": scrape.show_title or parsed.title,
            "season": parsed.season,
            "episode": parsed.episode,
            "episode_title": scrape.title,
            "year": scrape.year,
        }
        ctx = {k: v for k, v in ctx.items() if v is not None}
        return self.template.format(**ctx)

    async def execute(self, file_path: str, new_name: str) -> RenameResult:
        """执行单个文件重命名"""
        # 保留原扩展名
        ext = os.path.splitext(file_path)[1]
        final_name = new_name + ext
        await self.ds.rename(file_path, final_name)
        new_path = os.path.join(os.path.dirname(file_path), final_name)
        return RenameResult(original=file_path, new=new_path)

    async def execute_batch(self, items: list[tuple[str, str]]) -> list[RenameResult]:
        """批量重命名：[(原路径, 新文件名), ...]
        OpenList 数据源优先使用 batch_rename 接口减少请求。
        """
        if self.ds.name == "openlist" and len(items) > 1:
            await self.ds.batch_rename(items)
            return [RenameResult(original=p, new=os.path.join(os.path.dirname(p), n))
                    for p, n in items]
        # 逐个执行
        results = []
        for path, name in items:
            results.append(await self.execute(path, name))
        return results
```

**命名模板变量**：

| 变量 | 说明 |
|---|---|
| `{title}` | 剧名 |
| `{season}` | 季号（可用 `{season:02d}` 补零） |
| `{episode}` | 集号 |
| `{episode_title}` | 集标题 |
| `{year}` | 首播年份 |
| `{release_group}` | 发布组 |
| `{resolution}` | 分辨率 |

**回滚机制**：每次执行重命名前，将 `{原路径: 新路径}` 映射写入数据库 `rename_history` 表。回滚时：
- **本地**：`os.rename(新路径, 原路径)`。
- **OpenList**：再次调用 `POST /api/fs/rename`，将新文件名改回原名。

#### 5.2.4 NFO 生成器

```python
# app/core/nfo.py
from xml.etree.ElementTree import Element, SubElement, tostring

def generate_episode_nfo(show: ShowDetail, ep: EpisodeInfo) -> str:
    root = Element("episodedetails")
    SubElement(root, "title").text = ep.title
    SubElement(root, "showtitle").text = show.title
    SubElement(root, "season").text = str(ep.season)
    SubElement(root, "episode").text = str(ep.episode)
    SubElement(root, "plot").text = ep.plot
    SubElement(root, "aired").text = ep.air_date
    SubElement(root, "rating").text = str(ep.rating)
    return tostring(root, encoding="unicode")
```

**NFO 写入**：NFO 内容生成后，通过 `DataSource.upload()` 写入视频文件同目录：
- **本地**：直接写文件。
- **OpenList**：`PUT /api/fs/put` 流式上传，文件名与视频同名（`.nfo` 扩展名）。

#### 5.2.5 任务调度

```python
# app/tasks/manager.py
import asyncio
from uuid import uuid4

class TaskManager:
    def __init__(self):
        self.tasks: dict[str, Task] = {}

    async def run_rename(self, file_ids: list[str]) -> str:
        task_id = str(uuid4())
        task = Task(id=task_id, type="rename", total=len(file_ids))
        self.tasks[task_id] = task
        asyncio.create_task(self._do_rename(task, file_ids))
        return task_id

    async def _do_rename(self, task: Task, file_ids: list[str]):
        for i, fid in enumerate(file_ids):
            try:
                await self._rename_one(fid)
                task.done += 1
            except Exception as e:
                task.failed += 1
                task.errors.append((fid, str(e)))
            await self._broadcast(task)
        task.status = "completed"
```

### 5.3 数据模型（SQLModel）

```python
# app/models/models.py
from sqlmodel import SQLModel, Field
from datetime import datetime

class OpenListInstance(SQLModel, table=True):
    """OpenList 数据源实例配置"""
    id: int | None = Field(default=None, primary_key=True)
    name: str                      # 实例名称（用户自定义）
    base_url: str                  # 服务地址，如 https://fox.oplist.org
    username: str
    password_encrypted: str        # 密码（Fernet 加密存储）
    created_at: datetime

class MediaFile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source_type: str = Field(index=True)   # "local" or "openlist"
    source_ref: str = Field(index=True)    # 本地路径 或 OpenList 云盘路径
    openlist_id: int | None = Field(default=None, foreign_key="openlistinstance.id")
    original_name: str
    size: int
    parsed_title: str | None
    parsed_year: int | None
    parsed_season: int | None
    parsed_episode: int | None

class ScrapeMatch(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="mediafile.id")
    provider: str
    show_id: str
    show_title: str
    season: int
    episode: int
    episode_title: str | None

class RenameHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="mediafile.id")
    source_type: str              # 记录数据源，回滚时选择对应策略
    original_path: str
    new_path: str
    executed_at: datetime
    rolled_back: bool = False

class TaskRecord(SQLModel, table=True):
    id: str = Field(primary_key=True)
    type: str
    status: str          # pending / running / completed / failed
    total: int
    done: int
    failed: int
    created_at: datetime
```

---

## 6. 核心算法设计

### 6.1 文件名解析算法

```
输入: "Breaking.Bad.S01E03.1080p.BluRay.x264-DEMAND.mkv"

步骤:
1. 去扩展名 → "Breaking.Bad.S01E03.1080p.BluRay.x264-DEMAND"
2. 匹配季集正则 → season=1, episode=3, 切分点在 "S01E03"
3. 切分点左侧 → "Breaking.Bad."  → 清洗 → title="Breaking Bad"
4. 切分点右侧 → ".1080p.BluRay.x264-DEMAND"
   - 匹配分辨率 → 1080p
   - 匹配编码 → x264
   - 匹配发布组 → DEMAND
5. 输出 ParsedInfo
```

**多集处理**：`S01E01-E02` → `episode=1, episode_end=2`，重命名时生成 `E01-E02`。

**中文处理**：`绝命毒师 第1季 第03集.mp4` → 匹配 `第(?P<season>\d+)季.*?第(?P<episode>\d+)集`。

### 6.2 刮削匹配算法

```python
async def match_file(file: MediaFile, parsed: ParsedInfo) -> ScrapeMatch | None:
    # 1. 搜索候选剧集
    candidates = await provider.search(parsed.title, year=parsed.year)
    if not candidates:
        return None

    # 2. 置信度评分
    best = None
    best_score = 0
    for show in candidates:
        score = 0
        if parsed.year and show.year == parsed.year:
            score += 30
        if show.title.lower() == parsed.title.lower():
            score += 50
        elif parsed.title.lower() in show.title.lower():
            score += 20
        if score > best_score:
            best_score = score
            best = show

    # 3. 获取详情，验证集是否存在
    if best:
        detail = await provider.get_show(best.id)
        ep = detail.seasons[parsed.season].episodes.get(parsed.episode)
        if ep:
            return ScrapeMatch(show=best, episode=ep)
    return None
```

**置信度阈值**：低于阈值（如 40 分）时返回 `None`，要求用户手动选择。

### 6.3 重命名冲突处理

- 若目标文件名已存在且非当前文件 → 追加 ` (1)`、` (2)` 或报错要求用户确认。
- 跨目录重命名：仅支持同目录内重命名（避免意外移动）。

### 6.4 OpenList 远程操作注意事项 ★新增

1. **网络延迟**：OpenList 重命名/上传为网络操作，单个请求可能耗时数百 ms 至数秒。批量场景使用 `batch_rename` 减少往返。
2. **API 限流**：OpenList 服务端可能对 `/api/fs/*` 限流，客户端需控制并发（默认并发数 3），遇 429 时指数退避重试。
3. **冲突检测**：执行前调用 `fs/list` 检查目标文件名是否已存在于同目录，避免覆盖。
4. **部分失败**：`batch_rename` 若部分成功部分失败，需解析响应中每个条目的状态，成功项不重复执行，失败项记入错误列表。
5. **NFO 上传**：`PUT /api/fs/put` 需在 Header 中携带 `File-Path`（含完整目标路径），Content-Type 为 `application/octet-stream`。

---

## 7. 关键流程设计

### 7.1 重命名主流程

```
用户选择数据源(本地/OpenList)与目录
     │
     ▼
调用 /api/scan 扫描 → 返回 MediaFile 列表(含 source_type)
     │
     ▼
调用 /api/parse 解析文件名
     │
     ├── 解析失败 → 标记需人工修正
     │
     ▼
调用 /api/search 搜索剧集
     │
     ├── 无结果 → 用户手动搜索
     │
     ▼
用户选择候选剧集
     │
     ▼
调用 /api/match 匹配季集
     │
     ├── 匹配失败 → 用户手动指定季集
     │
     ▼
调用 /api/rename/preview 预览
     │
     ▼
用户确认 → /api/rename/execute
     │
     ├── 根据 source_type 获取 DataSource
     ├── 本地: os.rename / OpenList: fs/rename (批量用 batch_rename)
     ├── 写入 NFO: 本地写文件 / OpenList: PUT fs/put
     ├── 下载海报（可选，仅本地）
     └── 记录 rename_history (含 source_type)
     │
     ▼
返回执行结果（可撤销）
```

### 7.2 刮削流程

```
用户输入剧名
     │
     ▼
GET /api/search?query=xxx
     │
     ▼
后端并发请求已启用的 Provider
     │
     ▼
合并结果，按置信度排序返回
     │
     ▼
用户选择某 Provider 的某剧集
     │
     ▼
GET /api/shows/{provider}/{show_id}
     │
     ▼
返回完整季集树
     │
     ▼
前端展示匹配关系，用户确认
```

---

## 8. 配置与部署

### 8.1 配置项（`.env`）

```env
# 后端
DATABASE_URL=sqlite:///./episodescrap.db
SECRET_KEY=your-secret
ENCRYPTION_KEY=your-fernet-key        # 用于加密 OpenList 密码

# 媒体源 API Key
TMDB_API_KEY=
TVDB_API_KEY=
DOUBAN_COOKIE=

# 本地目录白名单（分号分隔）
ALLOWED_PATHS=/data/media;/home/user/downloads

# 刮削并发
SCRAPE_CONCURRENCY=3

# OpenList 相关
OPENLIST_CONCURRENCY=3                # OpenList API 并发数
OPENLIST_TIMEOUT=30                   # 请求超时（秒）
OPENLIST_RETRY=3                      # 失败重试次数

# 命名模板
RENAME_TEMPLATE={title} - S{season:02d}E{episode:02d} - {episode_title}
```

> OpenList 实例（服务地址、用户名、密码）不写在 `.env`，而是通过设置页动态增删，密码以 Fernet 加密存入数据库 `OpenListInstance` 表。

### 8.2 部署方式

**开发环境**：
```bash
# 后端
cd backend && uvicorn app.main:app --reload --port 8000
# 前端
cd frontend && npm run dev
```

**生产环境（Docker Compose）**：
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - /data/media:/media:rw
  frontend:
    build: ./frontend
    ports: ["80:80"]
```

**注意**：
- 本地数据源：后端容器需挂载用户的媒体目录，且 `ALLOWED_PATHS` 必须包含挂载路径。
- OpenList 数据源：**无需挂载本地目录**，所有文件操作通过 OpenList HTTP API 完成，后端只需能访问 OpenList 服务地址即可。

---

## 9. 异常处理与容错

| 场景 | 处理方式 |
|---|---|
| 文件名解析失败 | 标记 `status=error`，用户手动填写剧名/季/集 |
| 媒体源 API 超时/限流 | 指数退避重试（最多 3 次），失败记入任务错误 |
| 刮削无匹配结果 | 返回空候选，提示用户修改搜索关键词 |
| 重命名目标冲突 | 提示用户，支持追加序号或跳过 |
| 重命名中途失败 | 已成功的保持，失败的记录错误，支持重试 |
| 文件被外部修改 | 执行前校验文件是否存在且哈希一致 |
| **OpenList 登录失败** | 返回 401，提示用户检查账号密码；不自动重试 |
| **OpenList Token 过期** | 捕获 401，自动 `login()` 刷新 Token 后重试一次 |
| **OpenList API 限流 (429)** | 指数退避重试，最大等待 30s，记入任务警告 |
| **OpenList 网络超时** | 重试 3 次，仍失败则记入错误，不阻塞其他文件 |
| **OpenList batch_rename 部分失败** | 解析逐项响应，成功项标记完成，失败项允许单独重试 |
| **OpenList NFO 上传失败** | 记录错误，重命名操作不回滚（NFO 可重新生成上传） |

---

## 10. 安全考量

1. **目录访问控制**：本地数据源仅允许访问 `ALLOWED_PATHS` 下的路径，防止路径穿越。
2. **API Key 加密**：数据库中 API Key 以 Fernet 加密存储，内存中解密使用。
3. **命令注入**：所有文件操作使用 `os.path` 标准库，禁止 `shell=True`。
4. **输入校验**：Pydantic 校验所有请求参数，模板变量白名单校验。
5. **OpenList 凭证保护**：
   - OpenList 密码以 Fernet 加密存入数据库，前端永不返回明文密码。
   - JWT Token 仅存在后端内存中，不下发前端。
   - OpenList 服务地址需校验为合法 URL（http/https），防止 SSRF 指向内网。
6. **OpenList 操作隔离**：每个 OpenList 实例的操作独立，Token 不跨实例共享；删除实例时清除缓存 Token。
7. **重命名前确认**：所有写操作（重命名、上传 NFO）执行前必须经 preview 确认，OpenList 的 `remove` 接口在本系统中不封装（避免误删）。

---

## 11. 扩展点

- **新增媒体源**：继承 `BaseProvider` 并注册，无需修改核心代码。
- **新增数据源**：继承 `BaseDataSource` 并注册到工厂，可扩展 AList 原生、WebDAV、S3 等。
- **命名模板**：支持自定义变量与条件表达式（MVP 仅支持简单变量）。
- **媒体类型**：当前仅支持剧集，可扩展电影、综艺。
- **通知**：任务完成后可接入 Webhook / 邮件通知。
- **OpenList 正则重命名**：对简单规则可直接调用 `POST /api/fs/regex_rename`，减少逐个请求。

---

## 12. 里程碑（建议）

| 阶段 | 内容 |
|---|---|
| M1 | 后端：数据源抽象层 + 本地扫描 + 解析 + 重命名（无刮削） |
| M2 | 前端：数据源选择 + 扫描/解析/重命名页面联调 |
| M3 | 后端：OpenList 数据源（登录/list/rename）+ NFO 上传 |
| M4 | 前端：OpenList 实例配置页 + 云盘浏览 |
| M5 | 后端：TMDB 刮削 + NFO 生成 |
| M6 | 前端：刮削页面 + 任务进度 + 回滚 |
| M7 | 多 Provider、批量重命名优化、配置页完善 |
