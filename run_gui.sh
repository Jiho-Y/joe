#!/bin/bash

echo "========================================"
echo "  Semantic Scholar 논문 검색 도구 시작"
echo "========================================"
echo ""

if command -v python3 &> /dev/null; then
    python3 semantic_scholar_search_gui.py
elif command -v python &> /dev/null; then
    python semantic_scholar_search_gui.py
else
    echo "[오류] Python이 설치되어 있지 않습니다."
    echo ""
    echo "해결 방법:"
    echo "1. Python 설치: https://www.python.org/downloads/"
    echo "2. 패키지 설치: pip3 install -r requirements.txt"
    echo ""
    read -p "계속하려면 Enter를 누르세요..."
fi
