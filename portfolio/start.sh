#!/usr/bin/env bash
# 王耀威 · 个人主页 启动脚本（macOS / Linux）
# 优先使用 FastAPI；未安装依赖时自动回退到零依赖标准库服务器
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

export PORTFOLIO_HOST="${PORTFOLIO_HOST:-127.0.0.1}"
export PORTFOLIO_PORT="${PORTFOLIO_PORT:-8000}"

echo
echo "  王耀威 · 个人主页"
echo "  首页   http://${PORTFOLIO_HOST}:${PORTFOLIO_PORT}/"
echo "  后台   http://${PORTFOLIO_HOST}:${PORTFOLIO_PORT}/admin"
echo
echo "  按 Ctrl+C 停止服务"
echo

exec "$PYTHON" "$DIR/backend/app.py"
