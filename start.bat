@echo off
chcp 65001 >nul
title AI 面试教练

echo.
echo   ╔══════════════════════════════════╗
echo   ║       AI 面试教练 启动中...      ║
echo   ╚══════════════════════════════════╝
echo.

cd /d "%~dp0backend"

echo [1/2] 启动后端服务...
start "AI面试教练服务" /MIN python main.py

echo [2/2] 等待服务就绪...
:wait
timeout /t 1 /nobreak >nul
curl -s http://localhost:8008 >nul 2>&1
if errorlevel 1 goto wait

echo 正在打开浏览器...
start "" http://localhost:8008

echo.
echo   服务已启动！浏览器已打开 http://localhost:8008
echo   服务窗口已最小化到任务栏，请勿关闭。
echo.
echo   按任意键关闭此窗口（不影响服务运行）...
pause >nul