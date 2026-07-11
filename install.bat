@echo off
chcp 65001 >nul
title 安装依赖

echo.
echo   ╔══════════════════════════════════════╗
echo   ║      AI 面试教练 - 一键安装依赖      ║
echo   ╚══════════════════════════════════════╝
echo.

echo 正在安装 Python 依赖...
pip install -r requirements.txt

echo.
echo 正在安装 Tesseract OCR（用于截图识别）...
echo.
echo 请手动下载安装 Tesseract OCR：
echo https://github.com/UB-Mannheim/tesseract/wiki
echo.
echo 安装时记得勾选中文语言包（Chinese Simplified）
echo.

echo 安装完成后，请把 API Key 填入 backend\.env 文件
echo 然后双击 start.bat 启动
echo.

pause