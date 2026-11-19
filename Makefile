# EpisodeScrap 开发入口
BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 5173

.PHONY: dev backend frontend install

# 同时启动前后端；Ctrl+C 一并停止
dev:
	@set -e; \
	trap 'echo; echo "正在停止开发服务…"; kill $$backend_pid $$frontend_pid 2>/dev/null; wait $$backend_pid $$frontend_pid 2>/dev/null' INT TERM; \
	( cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT) ) & backend_pid=$$!; \
	( cd $(FRONTEND_DIR) && npm run dev -- --port $(FRONTEND_PORT) --strictPort ) & frontend_pid=$$!; \
	wait

backend:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT)

frontend:
	cd $(FRONTEND_DIR) && npm run dev -- --port $(FRONTEND_PORT) --strictPort

install:
	cd $(BACKEND_DIR) && uv sync
	cd $(FRONTEND_DIR) && npm install
