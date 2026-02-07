#!/bin/bash

# Bili-Sentinel 一键启动脚本

PROJECT_ROOT="/home/jikns/Projects/bilibili"
VENV_BIN="$PROJECT_ROOT/venv/bin/python3"

echo "🚀 正在启动 Bili-Sentinel..."

# 1. 启动后端 (后台运行)
echo "📡 正在启动后端引擎 (FastAPI)..."
cd $PROJECT_ROOT
$VENV_BIN -m backend.main > /home/jikns/.gemini/tmp/backend.log 2>&1 &
BACKEND_PID=$!

# 2. 启动前端
echo "🎨 正在启动前端界面 (Next.js)..."
cd $PROJECT_ROOT/frontend
bun run dev > /home/jikns/.gemini/tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

echo "✅ 系统已就绪！"
echo "🔗 后端接口: http://localhost:8000"
echo "🔗 前端面板: http://localhost:3000"
echo "提示: 使用 'kill $BACKEND_PID $FRONTEND_PID' 可停止服务。"

# 保持脚本运行以监听 Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; echo '🛑 服务已停止'; exit" INT
wait
