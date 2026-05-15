#!/bin/bash

# 스크립트가 위치한 디렉토리로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  필요한 패키지 설치 중..."
echo "========================================"
echo ""
echo "작업 디렉토리: $SCRIPT_DIR"
echo ""

if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    echo "[오류] pip이 설치되어 있지 않습니다."
    echo "Python과 pip을 먼저 설치해주세요."
    exit 1
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "  설치 완료!"
    echo "========================================"
    echo ""
    echo "이제 run_gui.sh 또는 run_cli.sh 파일을"
    echo "더블클릭하여 프로그램을 실행하세요."
    echo ""
else
    echo ""
    echo "[오류] 패키지 설치에 실패했습니다."
    echo "Python이 올바르게 설치되어 있는지 확인하세요."
    echo ""
fi

read -p "계속하려면 Enter를 누르세요..."
