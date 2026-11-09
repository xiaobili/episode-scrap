#!/bin/bash
set -e

uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

nginx -g 'daemon off;' &
NGINX_PID=$!

stop() {
    kill -TERM "$API_PID" "$NGINX_PID" 2>/dev/null || true
}
trap stop TERM INT

# 任一进程退出即结束容器
wait -n
STATUS=$?

stop
wait
exit "$STATUS"
