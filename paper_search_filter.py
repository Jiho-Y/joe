#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Scholar 논문 검색 및 필터링 통합 GUI 프로그램
Mac에서 사용 가능한 논문 검색 및 필터링 도구
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import pandas as pd
import requests
import time
from typing import List, Dict, Optional
import re
from pathlib import Path
from datetime import datetime
import threading
import json
import os


class ConfigManager:
    """설정 파일 관리 클래스"""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path.home() / ".paper_search_filter" / config_file
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """설정 파일 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"설정 파일 로드 오류: {e}")
                return {}
        return {}

    def save_config(self):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 파일 저장 오류: {e}")

    def get(self, key: str, default=None):
        """설정 값 가져오기"""
        return self.config.get(key, default)

    def set(self, key: str, value):
        """설정 값 저장"""
        self.config[key] = value
        self.save_config()


class SemanticScholarAPI:
    """Semantic Scholar API 검색 클래스 (견고한 에러 처리 포함)"""

    def __init__(self, api_key: Optional[str] = None, log_callback=None):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Academic Research Tool)'
        }
        self.api_key = api_key
        self.log_callback = log_callback

        # API 키가 있으면 헤더에 추가
        if api_key:
            self.headers['x-api-key'] = api_key

    def log(self, message):
        """로그 메시지 출력"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def exponential_backoff_wait(self, attempt, base_wait=1, max_wait=300):
        """
        지수 백오프 대기

        Args:
            attempt: 현재 시도 횟수 (0부터 시작)
            base_wait: 기본 대기 시간 (초)
            max_wait: 최대 대기 시간 (초) - 기본 5분
        """
        wait_time = min(base_wait * (2 ** attempt), max_wait)
        self.log(f"⏳ 재시도 대기 중... ({wait_time}초)")
        time.sleep(wait_time)
        return wait_time

    def search_single_batch(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        max_retries: int = 5,
        stop_flag: Optional[threading.Event] = None
    ) -> Optional[Dict]:
        """
        단일 배치 검색 (재시도 로직 포함)

        Args:
            query: 검색 키워드
            limit: 한 번에 가져올 결과 수 (최대 100)
            offset: 시작 위치
            year_from: 시작 연도
            year_to: 종료 연도
            max_retries: 재시도 최대 횟수
            stop_flag: 중단 플래그

        Returns:
            dict: {'data': 논문 리스트, 'total': 전체 결과 수} 또는 None
        """
        # 중단 확인
        if stop_flag and stop_flag.is_set():
            self.log("🛑 검색이 중단되었습니다.")
            return None

        params = {
            'query': query,
            'limit': min(limit, 100),
            'offset': offset,
            'fields': 'paperId,title,authors,year,venue,citationCount,abstract,externalIds,publicationDate,url'
        }

        # 연도 범위 설정
        if year_from and year_to:
            params['year'] = f"{year_from}-{year_to}"
        elif year_from:
            params['year'] = f"{year_from}-"
        elif year_to:
            params['year'] = f"-{year_to}"

        url = f"{self.base_url}/paper/search"

        for attempt in range(max_retries):
            # 중단 확인
            if stop_flag and stop_flag.is_set():
                self.log("🛑 검색이 중단되었습니다.")
                return None

            try:
                if attempt > 0:
                    self.log(f"📌 재시도 {attempt + 1}/{max_retries} (offset={offset})")

                # 첫 시도에만 URL 로깅
                if attempt == 0 and offset == 0:
                    self.log(f"🔗 API URL: {url}")
                    self.log(f"📦 Query: {query[:50]}{'...' if len(query) > 50 else ''}")

                response = requests.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=30  # 30초 타임아웃으로 변경
                )

                # Rate limit 처리 (429 에러)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.log(f"⚠️ Rate Limit 초과 - {retry_after}초 후 재시도 ({attempt + 1}/{max_retries})")

                    if attempt < max_retries - 1:
                        # 서버 권장 시간과 지수 백오프 중 큰 값 사용
                        exponential_wait = 2 ** attempt
                        wait_time = max(retry_after, exponential_wait)
                        time.sleep(wait_time)
                        continue
                    else:
                        self.log("❌ 최대 재시도 횟수 초과")
                        return None

                # 서버 오류 (500+)
                if response.status_code >= 500:
                    self.log(f"⚠️ 서버 오류 ({response.status_code}) - 재시도 {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        self.exponential_backoff_wait(attempt, base_wait=10, max_wait=300)
                        continue
                    else:
                        return None

                # HTTP 오류 체크
                response.raise_for_status()

                results = response.json()

                if 'data' not in results:
                    self.log("⚠️ API 응답 형식 오류")
                    if attempt < max_retries - 1:
                        self.exponential_backoff_wait(attempt, base_wait=2, max_wait=300)
                        continue
                    return None

                return results

            except requests.exceptions.Timeout:
                self.log(f"⚠️ 타임아웃 오류 ({attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    self.exponential_backoff_wait(attempt, base_wait=5, max_wait=300)
                else:
                    return None

            except requests.exceptions.HTTPError as http_err:
                self.log(f"⚠️ HTTP 오류: {http_err} ({attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    self.exponential_backoff_wait(attempt, base_wait=5, max_wait=300)
                else:
                    return None

            except requests.exceptions.RequestException as req_err:
                self.log(f"⚠️ 네트워크 오류: {req_err} ({attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    self.exponential_backoff_wait(attempt, base_wait=3, max_wait=300)
                else:
                    return None

            except Exception as e:
                self.log(f"⚠️ 알 수 없는 오류: {str(e)} ({attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    self.exponential_backoff_wait(attempt, base_wait=5, max_wait=300)
                else:
                    return None

        return None

    def test_connection(self) -> bool:
        """
        API 연결 테스트

        Returns:
            bool: 연결 성공 여부
        """
        try:
            self.log("🔍 API 연결 테스트 중...")
            response = requests.get(
                f"{self.base_url}/paper/search",
                params={'query': 'test', 'limit': 1, 'fields': 'paperId'},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                self.log(f"✅ API 연결 성공! (응답 시간: {response.elapsed.total_seconds():.2f}초)")
                return True
            else:
                self.log(f"⚠️ API 응답 코드: {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            self.log("❌ 연결 시간 초과 (10초)")
            return False
        except Exception as e:
            self.log(f"❌ 연결 실패: {str(e)}")
            return False

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        progress_callback=None,
        stop_flag: Optional[threading.Event] = None
    ) -> List[Dict]:
        """
        논문 검색 (Pagination 지원)

        Args:
            query: 검색 키워드
            limit: 검색 결과 최대 개수
            year_from: 시작 연도
            year_to: 종료 연도
            progress_callback: 진행상황 콜백 함수
            stop_flag: 중단 플래그

        Returns:
            논문 정보 리스트
        """
        all_papers = []
        offset = 0
        batch_size = 100

        # 중단 확인
        if stop_flag and stop_flag.is_set():
            self.log("🛑 검색이 중단되었습니다.")
            return []

        self.log(f"🔍 '{query}' 검색 시작...")

        # 첫 번째 요청으로 전체 결과 수 확인
        first_result = self.search_single_batch(
            query=query,
            limit=batch_size,
            offset=0,
            year_from=year_from,
            year_to=year_to,
            stop_flag=stop_flag
        )

        if first_result is None:
            if stop_flag and stop_flag.is_set():
                self.log(f"🛑 '{query}' 검색이 중단되었습니다.")
            else:
                self.log(f"❌ '{query}' 검색 실패")
            return []

        total_available = first_result.get('total', 0)
        papers = first_result.get('data', [])

        if not papers:
            self.log(f"⚠️ '{query}' 검색 결과 없음")
            return []

        all_papers.extend(papers)
        self.log(f"✓ 배치 1: {len(papers)}개 수집 (전체 약 {total_available}개 존재)")

        if progress_callback:
            progress_callback(len(all_papers), limit)

        # 100개 미만이거나 원하는 개수를 달성하면 종료
        if len(papers) < batch_size or len(all_papers) >= limit:
            self.log(f"✓ 검색 완료: 총 {len(all_papers)}개")
            return all_papers[:limit]

        # Pagination 계속
        target = min(limit, total_available)
        batch_num = 2

        while len(all_papers) < target:
            # 중단 확인
            if stop_flag and stop_flag.is_set():
                self.log("🛑 검색이 중단되었습니다.")
                break

            offset += batch_size
            remaining = target - len(all_papers)
            current_limit = min(batch_size, remaining)

            # API 키 없으면 Rate Limit 준수 (1.2초 대기)
            if not self.api_key:
                self.log(f"⏳ Rate Limit 준수를 위해 1.2초 대기...")
                time.sleep(1.2)

            self.log(f"📥 배치 {batch_num}: offset={offset}, limit={current_limit}")

            result = self.search_single_batch(
                query=query,
                limit=current_limit,
                offset=offset,
                year_from=year_from,
                year_to=year_to,
                stop_flag=stop_flag
            )

            if result is None:
                if stop_flag and stop_flag.is_set():
                    self.log(f"🛑 배치 {batch_num} 검색 중단")
                else:
                    self.log(f"⚠️ 배치 {batch_num} 검색 실패 (계속 진행)")
                break

            papers = result.get('data', [])

            if not papers:
                self.log(f"✓ 더 이상 결과 없음")
                break

            all_papers.extend(papers)
            self.log(f"✓ 배치 {batch_num}: {len(papers)}개 수집 (누적: {len(all_papers)}개)")

            if progress_callback:
                progress_callback(len(all_papers), limit)

            batch_num += 1

            # 전체 결과를 모두 가져왔으면 종료
            if len(all_papers) >= total_available:
                self.log(f"✓ 전체 결과 수집 완료")
                break

        self.log(f"✅ '{query}' 검색 완료: 총 {len(all_papers)}개 수집")
        return all_papers[:limit]

    def format_papers_for_export(self, papers: List[Dict]) -> pd.DataFrame:
        """
        논문 데이터를 DataFrame으로 변환 (지정된 컬럼 순서)
        컬럼 순서: 출판일, 제목, 저자, 저널, 인용수, DOI, 초록
        """
        formatted_data = []

        for paper in papers:
            # 저자 정보 포맷팅
            authors = paper.get('authors', [])
            if authors:
                author_names = ', '.join([a.get('name', '') for a in authors])
            else:
                author_names = 'No authors listed'

            # DOI 추출
            external_ids = paper.get('externalIds', {})
            doi = external_ids.get('DOI', 'N/A') if external_ids else 'N/A'

            # 출판일 (publicationDate가 있으면 사용, 없으면 year 사용)
            pub_date = paper.get('publicationDate', '')
            if not pub_date and paper.get('year'):
                pub_date = str(paper.get('year'))
            if not pub_date:
                pub_date = 'N/A'

            # Abstract 길이 체크 (Excel 셀 최대 길이 32767)
            abstract = paper.get('abstract', 'No abstract available')
            if abstract and len(abstract) > 32767:
                abstract = abstract[:32760] + "..."

            formatted_data.append({
                'Publication Date': pub_date,
                'Title': paper.get('title', 'No title'),
                'Authors': author_names,
                'Journal': paper.get('venue', 'N/A'),
                'Citation Count': paper.get('citationCount', 0),
                'DOI': doi,
                'Abstract': abstract,
                'Paper ID': paper.get('paperId', 'N/A'),  # 중복 제거용
                'URL': paper.get('url', 'N/A')
            })

        df = pd.DataFrame(formatted_data)

        # 컬럼 순서 확정: 출판일, 제목, 저자, 저널, 인용수, DOI, 초록 (+ Paper ID, URL)
        column_order = ['Publication Date', 'Title', 'Authors', 'Journal',
                       'Citation Count', 'DOI', 'Abstract', 'Paper ID', 'URL']
        df = df[column_order]

        return df

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """
        DOI 또는 Paper ID 기준으로 중복 제거

        Args:
            df: 논문 DataFrame

        Returns:
            tuple: (중복 제거된 DataFrame, 제거된 중복 수)
        """
        original_count = len(df)

        # DOI가 'N/A'가 아닌 경우 DOI로 중복 제거
        # DOI가 'N/A'인 경우 Paper ID로 중복 제거
        df['_dedup_key'] = df.apply(
            lambda row: row['DOI'] if row['DOI'] != 'N/A' else f"PID_{row['Paper ID']}",
            axis=1
        )

        # 중복 제거 (첫 번째 항목 유지)
        df_unique = df.drop_duplicates(subset=['_dedup_key'], keep='first')

        # 임시 컬럼 제거
        df_unique = df_unique.drop(columns=['_dedup_key'])

        removed_count = original_count - len(df_unique)

        return df_unique, removed_count


class PaperFilter:
    """
    논문 데이터를 다양한 키워드 조건으로 필터링하는 클래스
    """

    def __init__(self, file_path: str):
        """
        Args:
            file_path: 논문 데이터가 담긴 파일 경로 (csv, xlsx, xls 지원)
        """
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.csv':
            self.df = pd.read_csv(file_path, encoding='utf-8-sig')
        elif file_ext in ['.xlsx', '.xls', '.xlsm']:
            self.df = pd.read_excel(file_path, engine='openpyxl')
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {file_ext}\n지원 형식: .csv, .xlsx, .xls, .xlsm")

        self.original_count = len(self.df)

    def filter_by_keywords(
        self,
        keywords: List[str],
        mode: str = 'all',
        target_column: str = 'Title',
        case_sensitive: bool = False
    ) -> pd.DataFrame:
        """키워드 기반 필터링"""
        if target_column not in self.df.columns:
            raise ValueError(f"'{target_column}' 컬럼이 존재하지 않습니다.")

        search_data = self.df[target_column].fillna('')

        if not case_sensitive:
            search_data = search_data.str.lower()
            keywords = [k.lower() for k in keywords]

        contains_mask = pd.DataFrame({
            kw: search_data.str.contains(re.escape(kw), regex=True, na=False)
            for kw in keywords
        })

        if mode == 'all':
            mask = contains_mask.all(axis=1)
        elif mode == 'any':
            mask = contains_mask.any(axis=1)
        elif mode == 'none':
            mask = ~contains_mask.any(axis=1)
        else:
            raise ValueError("mode는 'all', 'any', 'none' 중 하나여야 합니다.")

        return self.df[mask].copy()

    def advanced_filter(
        self,
        include_all: List[str] = None,
        include_any: List[str] = None,
        exclude_any: List[str] = None,
        target_column: str = 'Title',
        case_sensitive: bool = False
    ) -> pd.DataFrame:
        """
        복합 조건 필터링 (AND, OR, NOT 조합)
        """
        mask = pd.Series([True] * len(self.df))
        search_data = self.df[target_column].fillna('')

        if not case_sensitive:
            search_data = search_data.str.lower()
            include_all = [k.lower() for k in include_all] if include_all else []
            include_any = [k.lower() for k in include_any] if include_any else []
            exclude_any = [k.lower() for k in exclude_any] if exclude_any else []

        if include_all:
            for kw in include_all:
                mask &= search_data.str.contains(re.escape(kw), regex=True, na=False)

        if include_any:
            any_mask = pd.Series([False] * len(self.df))
            for kw in include_any:
                any_mask |= search_data.str.contains(re.escape(kw), regex=True, na=False)
            mask &= any_mask

        if exclude_any:
            for kw in exclude_any:
                mask &= ~search_data.str.contains(re.escape(kw), regex=True, na=False)

        return self.df[mask].copy()

    def filter_by_year_range(self, start_year: int = None, end_year: int = None) -> pd.DataFrame:
        """연도 범위로 필터링"""
        mask = pd.Series([True] * len(self.df))

        # Publication Date 컬럼에서 연도 추출
        if 'Publication Date' in self.df.columns:
            # 연도만 추출 (YYYY 형식)
            years = self.df['Publication Date'].astype(str).str.extract(r'(\d{4})')[0]
            years = pd.to_numeric(years, errors='coerce')

            if start_year:
                mask &= years >= start_year
            if end_year:
                mask &= years <= end_year

        return self.df[mask].copy()

    def filter_by_citation_count(self, min_citations: int = None, max_citations: int = None) -> pd.DataFrame:
        """인용 수 범위로 필터링"""
        mask = pd.Series([True] * len(self.df))

        if 'Citation Count' in self.df.columns:
            if min_citations is not None:
                mask &= self.df['Citation Count'] >= min_citations
            if max_citations is not None:
                mask &= self.df['Citation Count'] <= max_citations

        return self.df[mask].copy()

    def get_statistics(self, filtered_df: pd.DataFrame = None) -> Dict:
        """필터링 결과 통계"""
        if filtered_df is None:
            filtered_df = self.df

        stats = {
            '총 논문 수': len(filtered_df),
        }

        # Publication Date에서 연도 추출
        if 'Publication Date' in filtered_df.columns:
            years = filtered_df['Publication Date'].astype(str).str.extract(r'(\d{4})')[0]
            years = pd.to_numeric(years, errors='coerce')
            if not years.isna().all():
                stats['연도 범위'] = f"{int(years.min())} - {int(years.max())}"

        if 'Citation Count' in filtered_df.columns:
            stats['평균 인용 수'] = f"{filtered_df['Citation Count'].mean():.1f}"
            stats['중앙 인용 수'] = f"{filtered_df['Citation Count'].median():.0f}"

        return stats


class PaperSearchFilterGUI:
    """통합 GUI 애플리케이션"""

    def __init__(self, root):
        self.root = root
        self.root.title("Semantic Scholar 논문 검색 및 필터링 도구")
        self.root.geometry("1200x800")

        # 설정 관리자
        self.config = ConfigManager()

        # API 객체
        self.api = SemanticScholarAPI()
        self.filter_obj = None

        # Excel 뷰어 데이터
        self.current_df = None
        self.current_excel_path = None

        # 검색 중단 플래그
        self.stop_search_flag = None
        self.search_thread_running = False

        # 탭 생성
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # 탭 1: 논문 검색
        self.search_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.search_tab, text="논문 검색")
        self.create_search_tab()

        # 탭 2: 논문 필터링
        self.filter_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.filter_tab, text="논문 필터링")
        self.create_filter_tab()

        # 탭 3: Excel 뷰어/에디터
        self.excel_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.excel_tab, text="Excel 뷰어/에디터")
        self.create_excel_tab()

    def create_search_tab(self):
        """논문 검색 탭 생성"""
        # 검색 설정 프레임
        settings_frame = ttk.LabelFrame(self.search_tab, text="검색 설정", padding=10)
        settings_frame.pack(fill='x', padx=10, pady=10)

        # API 키 입력
        ttk.Label(settings_frame, text="API Key:").grid(row=0, column=0, sticky='w', pady=5)
        self.api_key_var = tk.StringVar()

        # 저장된 API 키 자동 로드
        saved_api_key = self.config.get('api_key', '')
        if saved_api_key:
            self.api_key_var.set(saved_api_key)

        api_key_entry = ttk.Entry(settings_frame, textvariable=self.api_key_var, width=50, show='*')
        api_key_entry.grid(row=0, column=1, columnspan=2, sticky='ew', pady=5, padx=5)

        # API 키 저장 버튼
        ttk.Button(settings_frame, text="저장", command=self.save_api_key, width=8).grid(row=0, column=3, pady=5, padx=5)
        ttk.Label(settings_frame, text="(자동 로드됨)", font=('', 8)).grid(row=0, column=4, sticky='w')

        # 키워드 입력
        ttk.Label(settings_frame, text="검색 키워드:").grid(row=1, column=0, sticky='w', pady=5)
        self.search_query_entry = ttk.Entry(settings_frame, width=50)
        self.search_query_entry.grid(row=1, column=1, columnspan=2, sticky='ew', pady=5, padx=5)

        # 결과 개수
        ttk.Label(settings_frame, text="결과 개수:").grid(row=2, column=0, sticky='w', pady=5)
        self.limit_var = tk.IntVar(value=100)
        ttk.Entry(settings_frame, textvariable=self.limit_var, width=15).grid(row=2, column=1, sticky='w', pady=5, padx=5)

        # 연도 범위
        ttk.Label(settings_frame, text="연도 범위:").grid(row=3, column=0, sticky='w', pady=5)
        year_frame = ttk.Frame(settings_frame)
        year_frame.grid(row=3, column=1, sticky='w', pady=5, padx=5)

        self.year_from_var = tk.StringVar()
        self.year_to_var = tk.StringVar()
        ttk.Entry(year_frame, textvariable=self.year_from_var, width=8).pack(side='left')
        ttk.Label(year_frame, text=" ~ ").pack(side='left')
        ttk.Entry(year_frame, textvariable=self.year_to_var, width=8).pack(side='left')
        ttk.Label(year_frame, text=" (선택사항)").pack(side='left', padx=5)

        # 저장 경로
        ttk.Label(settings_frame, text="저장 경로:").grid(row=4, column=0, sticky='w', pady=5)
        self.save_path_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.save_path_var, width=40).grid(row=4, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(settings_frame, text="찾아보기", command=self.browse_save_path).grid(row=4, column=2, pady=5, padx=5)

        settings_frame.columnconfigure(1, weight=1)

        # 검색 버튼
        btn_frame = ttk.Frame(self.search_tab)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="🔗 연결 테스트", command=self.test_api_connection, width=15).pack(side='left', padx=5)
        self.start_search_btn = ttk.Button(btn_frame, text="🔍 검색 시작", command=self.start_search, width=15)
        self.start_search_btn.pack(side='left', padx=5)
        self.stop_search_btn = ttk.Button(btn_frame, text="🛑 검색 중단", command=self.stop_search, width=15, state='disabled')
        self.stop_search_btn.pack(side='left', padx=5)

        # 진행 상황
        progress_frame = ttk.LabelFrame(self.search_tab, text="진행 상황", padding=10)
        progress_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.search_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.search_progress.pack(fill='x', pady=5)

        self.search_status_text = scrolledtext.ScrolledText(progress_frame, height=15, wrap=tk.WORD)
        self.search_status_text.pack(fill='both', expand=True, pady=5)

    def create_filter_tab(self):
        """논문 필터링 탭 생성"""
        # 파일 선택
        file_frame = ttk.LabelFrame(self.filter_tab, text="파일 선택", padding=10)
        file_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(file_frame, text="필터링할 파일:").grid(row=0, column=0, sticky='w', pady=5)
        self.filter_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.filter_file_var, width=50).grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(file_frame, text="찾아보기", command=self.browse_filter_file).grid(row=0, column=2, pady=5, padx=5)
        ttk.Button(file_frame, text="파일 로드", command=self.load_filter_file).grid(row=0, column=3, pady=5, padx=5)

        file_frame.columnconfigure(1, weight=1)

        # 필터 설정
        filter_settings_frame = ttk.LabelFrame(self.filter_tab, text="필터 조건", padding=10)
        filter_settings_frame.pack(fill='x', padx=10, pady=10)

        # 검색 대상 컬럼
        ttk.Label(filter_settings_frame, text="검색 대상:").grid(row=0, column=0, sticky='w', pady=5)
        self.target_column_var = tk.StringVar(value='Title')
        column_combo = ttk.Combobox(filter_settings_frame, textvariable=self.target_column_var,
                                     values=['Title', 'Abstract', 'Authors', 'Journal'], width=15)
        column_combo.grid(row=0, column=1, sticky='w', pady=5, padx=5)

        # 대소문자 구분
        self.case_sensitive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_settings_frame, text="대소문자 구분",
                       variable=self.case_sensitive_var).grid(row=0, column=2, sticky='w', pady=5, padx=20)

        # Include All (모두 포함)
        ttk.Label(filter_settings_frame, text="모두 포함 (AND):").grid(row=1, column=0, sticky='w', pady=5)
        self.include_all_entry = ttk.Entry(filter_settings_frame, width=50)
        self.include_all_entry.grid(row=1, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        ttk.Label(filter_settings_frame, text="(쉼표로 구분)", font=('', 8)).grid(row=1, column=3, sticky='w')

        # Include Any (하나 이상 포함)
        ttk.Label(filter_settings_frame, text="하나 이상 포함 (OR):").grid(row=2, column=0, sticky='w', pady=5)
        self.include_any_entry = ttk.Entry(filter_settings_frame, width=50)
        self.include_any_entry.grid(row=2, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        ttk.Label(filter_settings_frame, text="(쉼표로 구분)", font=('', 8)).grid(row=2, column=3, sticky='w')

        # Exclude Any (제외)
        ttk.Label(filter_settings_frame, text="제외 (NOT):").grid(row=3, column=0, sticky='w', pady=5)
        self.exclude_any_entry = ttk.Entry(filter_settings_frame, width=50)
        self.exclude_any_entry.grid(row=3, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        ttk.Label(filter_settings_frame, text="(쉼표로 구분)", font=('', 8)).grid(row=3, column=3, sticky='w')

        # 연도 범위
        ttk.Label(filter_settings_frame, text="출판 연도:").grid(row=4, column=0, sticky='w', pady=5)
        year_filter_frame = ttk.Frame(filter_settings_frame)
        year_filter_frame.grid(row=4, column=1, sticky='w', pady=5, padx=5)

        self.filter_year_from_var = tk.StringVar()
        self.filter_year_to_var = tk.StringVar()
        ttk.Entry(year_filter_frame, textvariable=self.filter_year_from_var, width=8).pack(side='left')
        ttk.Label(year_filter_frame, text=" ~ ").pack(side='left')
        ttk.Entry(year_filter_frame, textvariable=self.filter_year_to_var, width=8).pack(side='left')

        # 인용 수 범위
        ttk.Label(filter_settings_frame, text="인용 수:").grid(row=5, column=0, sticky='w', pady=5)
        citation_frame = ttk.Frame(filter_settings_frame)
        citation_frame.grid(row=5, column=1, sticky='w', pady=5, padx=5)

        self.min_citations_var = tk.StringVar()
        self.max_citations_var = tk.StringVar()
        ttk.Entry(citation_frame, textvariable=self.min_citations_var, width=8).pack(side='left')
        ttk.Label(citation_frame, text=" ~ ").pack(side='left')
        ttk.Entry(citation_frame, textvariable=self.max_citations_var, width=8).pack(side='left')

        filter_settings_frame.columnconfigure(1, weight=1)

        # 실행 버튼
        btn_frame = ttk.Frame(self.filter_tab)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="필터링 실행", command=self.apply_filter, width=15).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="결과 저장", command=self.save_filtered_results, width=15).pack(side='left', padx=5)

        # 결과 표시
        result_frame = ttk.LabelFrame(self.filter_tab, text="필터링 결과", padding=10)
        result_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.filter_result_text = scrolledtext.ScrolledText(result_frame, height=10, wrap=tk.WORD)
        self.filter_result_text.pack(fill='both', expand=True)

        # 필터링된 데이터 저장용
        self.filtered_df = None

    def browse_save_path(self):
        """저장 경로 선택"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.save_path_var.set(filename)

    def browse_filter_file(self):
        """필터링할 파일 선택"""
        filename = filedialog.askopenfilename(
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.filter_file_var.set(filename)

    def load_filter_file(self):
        """필터링 파일 로드"""
        file_path = self.filter_file_var.get()
        if not file_path:
            messagebox.showwarning("경고", "파일을 선택해주세요.")
            return

        try:
            self.filter_obj = PaperFilter(file_path)
            self.filter_result_text.delete(1.0, tk.END)
            self.filter_result_text.insert(tk.END, f"파일 로드 완료!\n")
            self.filter_result_text.insert(tk.END, f"총 {self.filter_obj.original_count}편의 논문이 로드되었습니다.\n")
            messagebox.showinfo("성공", f"{self.filter_obj.original_count}편의 논문이 로드되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"파일 로드 실패:\n{str(e)}")

    def log_search_status(self, message):
        """검색 상태 로깅"""
        self.search_status_text.insert(tk.END, f"{message}\n")
        self.search_status_text.see(tk.END)
        self.root.update()

    def update_progress(self, current, total):
        """진행률 업데이트"""
        progress = (current / total) * 100
        self.search_progress['value'] = progress
        self.log_search_status(f"진행 중: {current}/{total} 논문")

    def search_thread(self):
        """검색 스레드 (백그라운드 실행)"""
        query = self.search_query_entry.get().strip()

        if not query:
            messagebox.showwarning("경고", "검색 키워드를 입력해주세요.")
            return

        save_path = self.save_path_var.get().strip()
        if not save_path:
            messagebox.showwarning("경고", "저장 경로를 지정해주세요.")
            return

        try:
            # API 키 가져오기
            api_key = self.api_key_var.get().strip() if self.api_key_var.get().strip() else None

            # log_callback 포함한 API 객체 생성
            api = SemanticScholarAPI(api_key=api_key, log_callback=self.log_search_status)

            if api_key:
                self.log_search_status("✅ API 키를 사용하여 검색합니다.")
            else:
                self.log_search_status("⚠️ API 키 없이 검색합니다 (기본 rate limit).")

            limit = self.limit_var.get()
            year_from = int(self.year_from_var.get()) if self.year_from_var.get().strip() else None
            year_to = int(self.year_to_var.get()) if self.year_to_var.get().strip() else None

            self.log_search_status(f"\n{'='*60}")
            self.log_search_status(f"검색 키워드: '{query}'")
            self.log_search_status(f"최대 결과 수: {limit}편")
            if year_from or year_to:
                year_range = f"{year_from or '?'} ~ {year_to or '?'}"
                self.log_search_status(f"연도 범위: {year_range}")
            self.log_search_status(f"{'='*60}\n")

            # 검색 실행
            papers = api.search_papers(
                query=query,
                limit=limit,
                year_from=year_from,
                year_to=year_to,
                progress_callback=self.update_progress,
                stop_flag=self.stop_search_flag
            )

            # 중단 확인
            if self.stop_search_flag and self.stop_search_flag.is_set():
                self.log_search_status("\n🛑 검색이 중단되었습니다.")
                messagebox.showinfo("중단", "검색이 중단되었습니다.")
                return

            if not papers:
                self.log_search_status("\n❌ 검색 결과가 없습니다.")
                messagebox.showinfo("알림", "검색 결과가 없습니다.")
                return

            self.log_search_status(f"\n{'='*60}")
            self.log_search_status(f"📊 데이터 처리 중...")
            self.log_search_status(f"{'='*60}")

            # DataFrame 변환
            df = api.format_papers_for_export(papers)
            self.log_search_status(f"✓ {len(papers)}편의 논문 데이터 변환 완료")

            # 중복 제거
            df_unique, removed_count = SemanticScholarAPI.remove_duplicates(df)
            if removed_count > 0:
                self.log_search_status(f"✓ {removed_count}개의 중복 논문 제거")
                self.log_search_status(f"✓ 최종 논문 수: {len(df_unique)}편")
            else:
                self.log_search_status(f"✓ 중복 논문 없음")

            # 엑셀 저장
            self.log_search_status(f"\n💾 엑셀 파일 저장 중...")
            df_unique.to_excel(save_path, index=False, engine='openpyxl')

            self.log_search_status(f"\n{'='*60}")
            self.log_search_status(f"✅ 저장 완료!")
            self.log_search_status(f"{'='*60}")
            self.log_search_status(f"📁 파일 경로: {save_path}")
            self.log_search_status(f"📊 논문 수: {len(df_unique)}편")
            self.log_search_status(f"📅 저장 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_search_status(f"{'='*60}")

            messagebox.showinfo("완료",
                f"검색 완료!\n\n"
                f"검색된 논문: {len(papers)}편\n"
                f"중복 제거: {removed_count}편\n"
                f"최종 저장: {len(df_unique)}편\n\n"
                f"{save_path}")

        except Exception as e:
            self.log_search_status(f"\n오류 발생: {str(e)}")
            messagebox.showerror("오류", f"검색 중 오류가 발생했습니다:\n{str(e)}")

        finally:
            # 버튼 상태 복원
            self.search_thread_running = False
            self.start_search_btn.config(state='normal')
            self.stop_search_btn.config(state='disabled')

    def start_search(self):
        """검색 시작 (별도 스레드)"""
        if self.search_thread_running:
            messagebox.showwarning("경고", "이미 검색이 진행 중입니다.")
            return

        self.search_status_text.delete(1.0, tk.END)
        self.search_progress['value'] = 0

        # 중단 플래그 초기화
        self.stop_search_flag = threading.Event()
        self.search_thread_running = True

        # 버튼 상태 변경
        self.start_search_btn.config(state='disabled')
        self.stop_search_btn.config(state='normal')

        # 백그라운드 스레드로 실행
        thread = threading.Thread(target=self.search_thread, daemon=True)
        thread.start()

    def stop_search(self):
        """검색 중단"""
        if self.stop_search_flag:
            self.stop_search_flag.set()
            self.log_search_status("\n🛑 검색 중단 요청...")
            self.stop_search_btn.config(state='disabled')

    def test_api_connection(self):
        """API 연결 테스트"""
        self.search_status_text.delete(1.0, tk.END)

        api_key = self.api_key_var.get().strip() if self.api_key_var.get().strip() else None
        api = SemanticScholarAPI(api_key=api_key, log_callback=self.log_search_status)

        # 백그라운드에서 테스트 실행
        def test_thread():
            result = api.test_connection()
            if result:
                messagebox.showinfo("성공", "API 연결에 성공했습니다!")
            else:
                messagebox.showerror("실패", "API 연결에 실패했습니다.\n로그를 확인하세요.")

        thread = threading.Thread(target=test_thread, daemon=True)
        thread.start()

    def apply_filter(self):
        """필터링 적용"""
        if self.filter_obj is None:
            messagebox.showwarning("경고", "먼저 파일을 로드해주세요.")
            return

        try:
            # 키워드 파싱
            def parse_keywords(text):
                if not text.strip():
                    return None
                return [k.strip() for k in text.split(',') if k.strip()]

            include_all = parse_keywords(self.include_all_entry.get())
            include_any = parse_keywords(self.include_any_entry.get())
            exclude_any = parse_keywords(self.exclude_any_entry.get())

            target_column = self.target_column_var.get()
            case_sensitive = self.case_sensitive_var.get()

            # 키워드 필터링
            result_df = self.filter_obj.advanced_filter(
                include_all=include_all,
                include_any=include_any,
                exclude_any=exclude_any,
                target_column=target_column,
                case_sensitive=case_sensitive
            )

            # 연도 필터링
            year_from = int(self.filter_year_from_var.get()) if self.filter_year_from_var.get().strip() else None
            year_to = int(self.filter_year_to_var.get()) if self.filter_year_to_var.get().strip() else None

            if year_from or year_to:
                temp_filter = PaperFilter.__new__(PaperFilter)
                temp_filter.df = result_df
                result_df = temp_filter.filter_by_year_range(year_from, year_to)

            # 인용 수 필터링
            min_cit = int(self.min_citations_var.get()) if self.min_citations_var.get().strip() else None
            max_cit = int(self.max_citations_var.get()) if self.max_citations_var.get().strip() else None

            if min_cit is not None or max_cit is not None:
                temp_filter = PaperFilter.__new__(PaperFilter)
                temp_filter.df = result_df
                result_df = temp_filter.filter_by_citation_count(min_cit, max_cit)

            # 결과 저장
            self.filtered_df = result_df

            # 통계 표시
            temp_filter = PaperFilter.__new__(PaperFilter)
            temp_filter.df = result_df
            stats = temp_filter.get_statistics(result_df)

            self.filter_result_text.delete(1.0, tk.END)
            self.filter_result_text.insert(tk.END, "=== 필터링 결과 ===\n\n")
            self.filter_result_text.insert(tk.END, f"원본 논문 수: {self.filter_obj.original_count}편\n")
            self.filter_result_text.insert(tk.END, f"필터링 후: {len(result_df)}편\n\n")

            self.filter_result_text.insert(tk.END, "=== 통계 ===\n")
            for key, value in stats.items():
                self.filter_result_text.insert(tk.END, f"{key}: {value}\n")

            self.filter_result_text.insert(tk.END, "\n✓ 필터링 완료! '결과 저장' 버튼을 눌러 저장하세요.")

            messagebox.showinfo("완료", f"필터링 완료!\n{len(result_df)}편의 논문이 선택되었습니다.")

        except Exception as e:
            messagebox.showerror("오류", f"필터링 중 오류가 발생했습니다:\n{str(e)}")

    def save_filtered_results(self):
        """필터링 결과 저장"""
        if self.filtered_df is None or len(self.filtered_df) == 0:
            messagebox.showwarning("경고", "저장할 필터링 결과가 없습니다.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                if filename.endswith('.csv'):
                    self.filtered_df.to_csv(filename, index=False, encoding='utf-8-sig')
                else:
                    self.filtered_df.to_excel(filename, index=False, engine='openpyxl')

                self.filter_result_text.insert(tk.END, f"\n\n✓ 저장 완료: {filename}")
                messagebox.showinfo("완료", f"필터링 결과가 저장되었습니다:\n{filename}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{str(e)}")

    def save_api_key(self):
        """API 키 저장"""
        api_key = self.api_key_var.get().strip()
        if api_key:
            self.config.set('api_key', api_key)
            messagebox.showinfo("저장 완료", "API 키가 저장되었습니다.\n다음 실행 시 자동으로 로드됩니다.")
        else:
            messagebox.showwarning("경고", "API 키를 입력해주세요.")

    def create_excel_tab(self):
        """Excel 뷰어/에디터 탭 생성"""
        # 파일 열기 프레임
        file_frame = ttk.LabelFrame(self.excel_tab, text="파일 열기", padding=10)
        file_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(file_frame, text="Excel 파일:").grid(row=0, column=0, sticky='w', pady=5)
        self.excel_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.excel_file_var, width=60).grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(file_frame, text="찾아보기", command=self.browse_excel_file).grid(row=0, column=2, pady=5, padx=5)
        ttk.Button(file_frame, text="열기", command=self.load_excel_file).grid(row=0, column=3, pady=5, padx=5)

        file_frame.columnconfigure(1, weight=1)

        # 도구 프레임
        tools_frame = ttk.Frame(self.excel_tab)
        tools_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(tools_frame, text="선택 행 삭제", command=self.delete_selected_rows, width=15).pack(side='left', padx=5)
        ttk.Button(tools_frame, text="변경사항 저장", command=self.save_excel_changes, width=15).pack(side='left', padx=5)
        ttk.Button(tools_frame, text="다른 이름으로 저장", command=self.save_excel_as, width=18).pack(side='left', padx=5)
        ttk.Button(tools_frame, text="새로고침", command=self.refresh_excel_view, width=12).pack(side='left', padx=5)

        # 통계 레이블
        self.excel_stats_label = ttk.Label(tools_frame, text="", font=('', 9))
        self.excel_stats_label.pack(side='right', padx=10)

        # Treeview 프레임
        tree_frame = ttk.Frame(self.excel_tab)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # 스크롤바
        y_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        y_scrollbar.pack(side='right', fill='y')

        x_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal')
        x_scrollbar.pack(side='bottom', fill='x')

        # Treeview
        self.excel_tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
            selectmode='extended'
        )
        self.excel_tree.pack(fill='both', expand=True)

        y_scrollbar.config(command=self.excel_tree.yview)
        x_scrollbar.config(command=self.excel_tree.xview)

        # 더블클릭으로 셀 편집
        self.excel_tree.bind('<Double-1>', self.on_cell_double_click)

    def browse_excel_file(self):
        """Excel 파일 찾아보기"""
        filename = filedialog.askopenfilename(
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.excel_file_var.set(filename)

    def load_excel_file(self):
        """Excel 파일 로드"""
        file_path = self.excel_file_var.get().strip()
        if not file_path:
            messagebox.showwarning("경고", "파일을 선택해주세요.")
            return

        try:
            # 파일 읽기
            file_ext = Path(file_path).suffix.lower()
            if file_ext == '.csv':
                self.current_df = pd.read_csv(file_path, encoding='utf-8-sig')
            else:
                self.current_df = pd.read_excel(file_path, engine='openpyxl')

            self.current_excel_path = file_path

            # Treeview 업데이트
            self.refresh_excel_view()

            messagebox.showinfo("성공", f"{len(self.current_df)}개 행이 로드되었습니다.")

        except Exception as e:
            messagebox.showerror("오류", f"파일 로드 실패:\n{str(e)}")

    def refresh_excel_view(self):
        """Excel 뷰 새로고침"""
        if self.current_df is None:
            return

        # 기존 트리 내용 삭제
        for item in self.excel_tree.get_children():
            self.excel_tree.delete(item)

        # 컬럼 설정
        columns = list(self.current_df.columns)
        self.excel_tree['columns'] = columns
        self.excel_tree['show'] = 'headings'

        # 컬럼 헤더 설정
        for col in columns:
            self.excel_tree.heading(col, text=col)
            self.excel_tree.column(col, width=150, anchor='w')

        # 데이터 삽입
        for idx, row in self.current_df.iterrows():
            values = [str(val) if pd.notna(val) else '' for val in row]
            self.excel_tree.insert('', 'end', iid=str(idx), values=values)

        # 통계 업데이트
        self.excel_stats_label.config(text=f"총 {len(self.current_df)}개 행")

    def on_cell_double_click(self, event):
        """셀 더블클릭 시 편집"""
        if self.current_df is None:
            return

        # 선택된 셀 정보 가져오기
        region = self.excel_tree.identify('region', event.x, event.y)
        if region != 'cell':
            return

        column = self.excel_tree.identify_column(event.x)
        row = self.excel_tree.identify_row(event.y)

        if not column or not row:
            return

        # 컬럼 인덱스 계산 (#1 -> 0)
        col_idx = int(column.replace('#', '')) - 1
        col_name = self.excel_tree['columns'][col_idx]

        # 현재 값 가져오기
        current_value = self.excel_tree.item(row, 'values')[col_idx]

        # 편집 다이얼로그
        new_value = tk.simpledialog.askstring(
            "셀 편집",
            f"컬럼: {col_name}\n\n현재 값:",
            initialvalue=current_value
        )

        if new_value is not None:
            # DataFrame 업데이트
            row_idx = int(row)
            self.current_df.at[row_idx, col_name] = new_value

            # Treeview 업데이트
            values = list(self.excel_tree.item(row, 'values'))
            values[col_idx] = new_value
            self.excel_tree.item(row, values=values)

    def delete_selected_rows(self):
        """선택된 행 삭제"""
        if self.current_df is None:
            messagebox.showwarning("경고", "파일을 먼저 로드해주세요.")
            return

        selected_items = self.excel_tree.selection()
        if not selected_items:
            messagebox.showwarning("경고", "삭제할 행을 선택해주세요.")
            return

        # 확인
        if not messagebox.askyesno("확인", f"{len(selected_items)}개 행을 삭제하시겠습니까?"):
            return

        # 행 인덱스 수집
        row_indices = [int(item) for item in selected_items]

        # DataFrame에서 삭제
        self.current_df = self.current_df.drop(index=row_indices).reset_index(drop=True)

        # 뷰 새로고침
        self.refresh_excel_view()

        messagebox.showinfo("완료", f"{len(row_indices)}개 행이 삭제되었습니다.")

    def save_excel_changes(self):
        """변경사항 저장 (원본 파일에)"""
        if self.current_df is None:
            messagebox.showwarning("경고", "파일을 먼저 로드해주세요.")
            return

        if not self.current_excel_path:
            messagebox.showwarning("경고", "파일 경로가 없습니다. '다른 이름으로 저장'을 사용하세요.")
            return

        try:
            if self.current_excel_path.endswith('.csv'):
                self.current_df.to_csv(self.current_excel_path, index=False, encoding='utf-8-sig')
            else:
                self.current_df.to_excel(self.current_excel_path, index=False, engine='openpyxl')

            messagebox.showinfo("완료", f"변경사항이 저장되었습니다:\n{self.current_excel_path}")
        except Exception as e:
            messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{str(e)}")

    def save_excel_as(self):
        """다른 이름으로 저장"""
        if self.current_df is None:
            messagebox.showwarning("경고", "파일을 먼저 로드해주세요.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                if filename.endswith('.csv'):
                    self.current_df.to_csv(filename, index=False, encoding='utf-8-sig')
                else:
                    self.current_df.to_excel(filename, index=False, engine='openpyxl')

                self.current_excel_path = filename
                messagebox.showinfo("완료", f"파일이 저장되었습니다:\n{filename}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{str(e)}")


def main():
    """메인 함수"""
    root = tk.Tk()
    app = PaperSearchFilterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
