@echo off
chcp 65001 >nul
title 패키지 설치
echo ========================================
echo   필요한 패키지 설치 중...
echo ========================================
echo.
pip install -r requirements.txt
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   설치 완료!
    echo ========================================
    echo.
    echo 이제 run_gui.bat 또는 run_cli.bat 파일을
    echo 더블클릭하여 프로그램을 실행하세요.
    echo.
) else (
    echo.
    echo [오류] 패키지 설치에 실패했습니다.
    echo Python이 올바르게 설치되어 있는지 확인하세요.
    echo.
)
pause
