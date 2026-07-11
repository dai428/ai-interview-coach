@echo off
chcp 65001 >nul
title 局域网分享

echo.
echo   ╔══════════════════════════════════════╗
echo   ║        AI 面试教练 - 局域网分享      ║
echo   ╚══════════════════════════════════════╝
echo.

REM 获取本机局域网IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr "IPv4"') do (
    set "IP=%%a"
    set "IP=!IP: =!"
    if not "!IP!"=="127.0.0.1" goto found
)
:found

echo 本机局域网地址: http://!IP!:8008
echo.

REM 启动服务
cd /d "%~dp0backend"
echo 启动服务中...
start "AI面试教练服务" /MIN python main.py

echo.
echo 等待服务就绪...
:wait
timeout /t 1 /nobreak >nul
curl -s http://localhost:8008 >nul 2>&1
if errorlevel 1 goto wait

echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║                                              ║
echo   ║   分享以下地址给同一WiFi下的朋友：            ║
echo   ║   http://!IP!:8008                           ║
echo   ║                                              ║
echo   ╚══════════════════════════════════════════════╝
echo.
echo 按任意键关闭此窗口（服务仍在运行）...
pause >nul