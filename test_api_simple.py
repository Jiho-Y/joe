#!/usr/bin/env python3
"""
Semantic Scholar API 연결 테스트 스크립트 (GUI 없이)
"""

import requests
import time
from typing import Optional, Dict

class SimpleAPITest:
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {}
        if api_key:
            self.headers['x-api-key'] = api_key

    def test_connection(self) -> bool:
        """API 연결 테스트"""
        print("🔍 API 연결 테스트 중...")
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/paper/search",
                params={
                    'query': 'test',
                    'limit': 1,
                    'fields': 'paperId,title'
                },
                headers=self.headers,
                timeout=10
            )
            elapsed = time.time() - start_time

            print(f"응답 코드: {response.status_code}")
            print(f"응답 시간: {elapsed:.2f}초")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ API 연결 성공!")
                print(f"데이터 샘플: {data}")
                return True
            else:
                print(f"❌ API 응답 에러: {response.status_code}")
                print(f"응답 내용: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print("❌ 연결 실패: 타임아웃 (10초 초과)")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"❌ 연결 실패: 네트워크 오류 - {str(e)}")
            return False
        except Exception as e:
            print(f"❌ 연결 실패: {type(e).__name__} - {str(e)}")
            return False

    def test_search(self, query: str = "machine learning", limit: int = 3) -> bool:
        """간단한 검색 테스트"""
        print(f"\n🔍 검색 테스트: '{query}' (최대 {limit}개)")
        print("-" * 70)

        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/paper/search",
                params={
                    'query': query,
                    'limit': limit,
                    'fields': 'paperId,title,authors,year,citationCount'
                },
                headers=self.headers,
                timeout=30
            )
            elapsed = time.time() - start_time

            print(f"응답 코드: {response.status_code}")
            print(f"응답 시간: {elapsed:.2f}초")

            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                total = data.get('total', 0)

                print(f"✅ 검색 성공!")
                print(f"전체 결과 수: {total}")
                print(f"반환된 논문 수: {len(papers)}")

                for i, paper in enumerate(papers, 1):
                    print(f"\n[{i}] {paper.get('title', 'N/A')}")
                    authors = paper.get('authors', [])
                    author_names = [a.get('name', '') for a in authors[:3]]
                    print(f"    저자: {', '.join(author_names)}")
                    print(f"    연도: {paper.get('year', 'N/A')}")
                    print(f"    인용수: {paper.get('citationCount', 0)}")

                return True
            else:
                print(f"❌ 검색 실패: HTTP {response.status_code}")
                print(f"응답 내용: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print("❌ 검색 실패: 타임아웃 (30초 초과)")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"❌ 검색 실패: 네트워크 오류 - {str(e)}")
            return False
        except Exception as e:
            print(f"❌ 검색 실패: {type(e).__name__} - {str(e)}")
            return False

def main():
    print("=" * 70)
    print("Semantic Scholar API 테스트 (간소화 버전)")
    print("=" * 70)

    # API 키 없이 테스트
    api = SimpleAPITest()

    # 1. 연결 테스트
    print("\n[테스트 1] API 연결 테스트")
    print("-" * 70)
    connection_ok = api.test_connection()

    if not connection_ok:
        print("\n⚠️ API 연결에 실패했습니다. 네트워크 상태를 확인하세요.")
        return

    # 2. 검색 테스트
    print("\n" + "=" * 70)
    print("[테스트 2] 논문 검색 테스트")
    search_ok = api.test_search(query="machine learning", limit=3)

    # 결과 요약
    print("\n" + "=" * 70)
    print("테스트 결과 요약")
    print("=" * 70)
    print(f"연결 테스트: {'✅ 통과' if connection_ok else '❌ 실패'}")
    print(f"검색 테스트: {'✅ 통과' if search_ok else '❌ 실패'}")

    if connection_ok and search_ok:
        print("\n🎉 모든 테스트가 통과했습니다!")
        print("프로그램이 정상적으로 작동할 준비가 되었습니다.")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")
        print("네트워크 연결 또는 API 상태를 확인하세요.")

if __name__ == "__main__":
    main()
