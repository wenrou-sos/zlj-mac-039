#!/bin/bash
# 一键启动前后端 (本地开发)
cd "$(dirname "$0")"

cd backend
python3 -m uvicorn app.main:app --port 8000 &
BACK_PID=$!
cd ../frontend
npm run dev &
FRONT_PID=$!

echo "后端: http://localhost:8000  (API文档: http://localhost:8000/docs)"
echo "前端: http://localhost:5173"
trap "kill $BACK_PID $FRONT_PID 2>/dev/null" EXIT
wait
