#!/usr/bin/env python3
"""
Semantic Scholar API 연결 테스트 스크립트
"""

import sys
import os

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from paper_search_filter import SemanticScholarAPI

def main():
    print("=" * 70)
    print("Semantic Scholar API 연결 테스트")
    print("=" * 70)

    # API 객체 생성 (키 없이)
    api = SemanticScholarAPI()

    print("\n1. API 키 없이 연결 테스트...")
    print("-" * 70)
    result = api.test_connection()

    if result:
        print("\n✅ 테스트 성공! API가 정상적으로 작동합니다.")
    else:
        print("\n❌ 테스트 실패! 네트워크 연결이나 API 상태를 확인하세요.")

    print("\n" + "=" * 70)
    print("2. 간단한 검색 테스트 (1개 논문만 검색)...")
    print("-" * 70)

    try:
        papers = api.search_papers(query="machine learning", limit=1)

        if papers:
            print(f"\n✅ 검색 성공! {len(papers)}개의 논문을 찾았습니다.")
            print("\n첫 번째 논문:")
            print(f"  제목: {papers[0].get('title', 'N/A')}")
            print(f"  저자: {', '.join([a.get('name', '') for a in papers[0].get('authors', [])])}")
            print(f"  연도: {papers[0].get('year', 'N/A')}")
        else:
            print("\n⚠️ 검색 결과가 없습니다.")

    except Exception as e:
        print(f"\n❌ 검색 오류: {str(e)}")

    print("\n" + "=" * 70)
    print("테스트 완료!")
    print("=" * 70)

if __name__ == "__main__":
    main()
