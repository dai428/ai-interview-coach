@echo off
echo 正在停止 AI 面试教练服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8008" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo 服务已停止。
pause