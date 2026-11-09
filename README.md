# EpisodeScrap

面向影视剧集的**重命名与刮削** Web 工具，同时支持本地文件系统与 [OpenList](https://doc.oplist.org/) 云盘数据源。扫描目录 → 解析文件名 → 从 TMDB 刮削元数据 → 批量重命名并生成 NFO / STRM，全程可预览、可回滚。

## 功能

- **数据源**：本地目录（受白名单约束）与 OpenList 实例（在设置页动态增删，密码 Fernet 加密入库）
- **扫描**：递归识别 `.mkv .mp4 .avi .mov .wmv .flv .ts .webm`，统一抽象为 `MediaFile`
- **解析**：自动从文件名提取剧名、季、集、年份，支持中文/英文/常见发布组命名，解析结果可手动修正
- **刮削**：TMDB 搜索与剧集详情、按季/集自动匹配，展示匹配置信度
- **重命名**：模板化命名（默认 `{title} - S{season:02d}E{episode:02d} - {episode_title}`），冲突自动避让，支持一键回滚
- **NFO / STRM**：为匹配结果生成 `<episodedetails>` NFO；按模板生成 STRM，支持 `alongside` / `library` / `mirror` 三种输出模式
- **任务中心**：后台任务进度、失败重试，通过 `/ws/tasks/{task_id}` 实时推送
- **设置**：重命名模板、允许路径、TMDB Key、OpenList 并发/超时/重试、STRM 规则

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + TypeScript、Vite、Vue Router、Pinia、Axios、Tailwind CSS v4 |
| 后端 | Python 3.12、FastAPI、Uvicorn、SQLModel（SQLite）、httpx、loguru、pydantic-settings |
| 测试 | pytest、pytest-asyncio |
| 部署 | 多阶段 Docker（nginx 托管前端 + 反代 API/WS） |

## 目录结构

```
episode-scrap/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 路由：scan / parse / scrape / rename / tasks / settings / datasources
│   │   ├── core/            # parser、matcher、renamer、nfo、strm
│   │   ├── datasources/     # local / openlist 数据源实现
│   │   ├── providers/       # 元数据提供方（tmdb）
│   │   ├── clients/         # OpenList API 客户端
│   │   ├── services/        # 业务服务、加密、任务管理
│   │   └── config.py        # 环境变量配置
│   ├── tests/
│   └── pyproject.toml
├── frontend/                # Vue 前端
│   └── src/{views,components,stores,api,router}
├── docker/                  # nginx.conf、entrypoint.sh
├── .github/workflows/       # 构建并推送 GHCR 镜像
├── Dockerfile
└── design.md                # 系统设计文档
```

## 本地开发

需要 Python 3.12、[uv](https://docs.astral.sh/uv/)、Node.js 22（Vite 7 要求 20.19+）。

```bash
# 后端（默认 http://localhost:8000）
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 前端（默认 http://localhost:5173，已代理 /api 与 /ws 到 8000）
cd frontend
npm install
npm run dev
```

前端构建：

```bash
cd frontend && npm run build   # 包含 vue-tsc 类型检查，产物在 dist/
```

## 配置

后端通过 `.env`（见 [backend/.env.example](backend/.env.example)）读取配置：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./episodescrap.db` |
| `SECRET_KEY` | 通用密钥，参与 Fernet 密钥派生 | `dev-secret-change-me` |
| `ENCRYPTION_KEY` | Fernet key；留空则由 `SECRET_KEY` 派生 | 空 |
| `TMDB_API_KEY` | TMDB API Key（也可在设置页填写） | 空 |
| `ALLOWED_PATHS` | 本地目录白名单，分号分隔 | 空 |
| `SCRAPE_CONCURRENCY` | 刮削并发数 | `3` |
| `OPENLIST_CONCURRENCY` / `OPENLIST_TIMEOUT` / `OPENLIST_RETRY` | OpenList 请求并发、超时（秒）、重试 | `3` / `30` / `3` |
| `RENAME_TEMPLATE` | 重命名模板 | `{title} - S{season:02d}E{episode:02d} - {episode_title}` |
| `STRM_URL_TEMPLATE` | STRM 链接模板 | `{base_url}/d/{path}` |
| `STRM_OUTPUT_MODE` | STRM 输出模式：`alongside` / `library` / `mirror` | `alongside` |
| `STRM_TARGET_DIR` | `library` / `mirror` 模式的目标目录 | 空 |

> OpenList 实例（地址、用户名、密码）不写在 `.env`，在设置页添加，密码加密后存入数据库。

## 测试

```bash
cd backend
uv run pytest
```

## Docker 部署

镜像内由 nginx 托管前端静态文件，并将 `/api`、`/ws` 反代到同一容器内的 Uvicorn。

```bash
docker build -t episode-scrap .

docker run -d --name episode-scrap \
  -p 8080:80 \
  -v es-data:/data \
  -v /path/to/media:/media:rw \
  -e ALLOWED_PATHS=/media \
  -e TMDB_API_KEY=your-tmdb-key \
  episode-scrap
```

- 访问 `http://localhost:8080`，健康检查：`curl http://localhost:8080/api/health`
- 数据库存放在 `/data/episodescrap.db`，挂载卷可持久化
- 使用本地数据源时必须挂载媒体目录，且 `ALLOWED_PATHS` 要指向**容器内**路径
- 仅使用 OpenList 数据源时无需挂载媒体目录，只需容器能访问 OpenList 服务

## 镜像发布

[.github/workflows/docker.yml](.github/workflows/docker.yml) 在以下情况构建并推送 `linux/amd64` 镜像到 GitHub Container Registry：

- 推送到 `main`：标签 `latest`、`sha-<短哈希>`
- 推送 `v*` 标签（符合 semver）：额外生成 `1.2.3`、`1.2` 版本标签

使用内置 `GITHUB_TOKEN`，无需额外 Secrets。镜像地址为 `ghcr.io/<owner>/episode-scrap`，拉取前按需登录：

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin
docker pull ghcr.io/<owner>/episode-scrap:latest
```

## 说明

- 当前元数据提供方仅实现 TMDB
- 项目尚未声明开源许可证
- 更完整的需求与架构说明见 [design.md](design.md)
