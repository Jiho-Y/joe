#!/bin/bash

# 스크립트가 위치한 디렉토리로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  Semantic Scholar 논문 검색 도구 시작"
echo "========================================"
echo ""
echo "작업 디렉토리: $SCRIPT_DIR"
echo ""

if command -v python3 &> /dev/null; then
    python3 semantic_scholar_search.py
elif command -v python &> /dev/null; then
    python semantic_scholar_search.py
else
    echo "[오류] Python이 설치되어 있지 않습니다."
    echo ""
    echo "해결 방법:"
    echo "1. Python 설치: https://www.python.org/downloads/"
    echo "2. 패키지 설치: pip3 install -r requirements.txt"
    echo ""
    read -p "계속하려면 Enter를 누르세요..."
fi
