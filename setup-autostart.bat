@echo off
chcp 65001 >nul
title 设置开机自启动

echo.
echo   ╔══════════════════════════════════════╗
echo   ║     设置 AI 面试教练 开机自启动      ║
echo   ╚══════════════════════════════════════╝
echo.

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SCRIPT_PATH=%~dp0start.bat"
set "VBS_PATH=%STARTUP_DIR%\AI面试教练.vbs"

echo 正在创建开机自启动项...

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_PATH%"
echo WshShell.Run """%SCRIPT_PATH%""", 0, False >> "%VBS_PATH%"

echo.
echo   ✓ 开机自启动已设置成功！
echo.
echo   以后每次开机都会自动启动 AI 面试教练服务。
echo   浏览器不会自动打开，需要手动访问 http://localhost:8008
echo.
echo   如需取消，请删除以下文件：
echo   %VBS_PATH%
echo.

pause