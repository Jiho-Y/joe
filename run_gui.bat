@echo off
chcp 65001 >nul
title Semantic Scholar 논문 검색 도구
echo ========================================
echo   Semantic Scholar 논문 검색 도구 시작
echo ========================================
echo.
python semantic_scholar_search_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [오류] Python이 설치되어 있지 않거나 패키지가 설치되지 않았습니다.
    echo.
    echo 해결 방법:
    echo 1. Python 설치: https://www.python.org/downloads/
    echo 2. 패키지 설치: pip install -r requirements.txt
    echo.
    pause
)
