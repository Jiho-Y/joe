#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Scholar 논문 검색 및 필터링 통합 GUI 프로그램
Mac에서 사용 가능한 논문 검색 및 필터링 도구
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import requests
import time
from typing import List, Dict, Optional
import re
from pathlib import Path
from datetime import datetime
import threading


class SemanticScholarAPI:
    """Semantic Scholar API 검색 클래스"""

    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0'
        }

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        progress_callback=None
    ) -> List[Dict]:
        """
        논문 검색

        Args:
            query: 검색 키워드
            limit: 검색 결과 최대 개수
            year_from: 시작 연도
            year_to: 종료 연도
            progress_callback: 진행상황 콜백 함수

        Returns:
            논문 정보 리스트
        """
        papers = []
        offset = 0
        batch_size = 100  # API 한 번에 최대 100개

        fields = "paperId,title,authors,year,venue,citationCount,abstract,externalIds,publicationDate"

        while len(papers) < limit:
            try:
                params = {
                    'query': query,
                    'offset': offset,
                    'limit': min(batch_size, limit - len(papers)),
                    'fields': fields
                }

                if year_from:
                    params['year'] = f"{year_from}-"
                if year_to:
                    if year_from:
                        params['year'] = f"{year_from}-{year_to}"
                    else:
                        params['year'] = f"-{year_to}"

                response = requests.get(
                    f"{self.base_url}/paper/search",
                    params=params,
                    headers=self.headers,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    batch_papers = data.get('data', [])

                    if not batch_papers:
                        break

                    papers.extend(batch_papers)
                    offset += len(batch_papers)

                    if progress_callback:
                        progress_callback(len(papers), limit)

                    # API rate limit 준수
                    time.sleep(1)

                    # 더 이상 결과가 없으면 종료
                    if len(batch_papers) < batch_size:
                        break

                elif response.status_code == 429:
                    # Rate limit 초과시 대기
                    time.sleep(5)
                    continue
                else:
                    print(f"API 오류: {response.status_code}")
                    break

            except Exception as e:
                print(f"검색 중 오류 발생: {str(e)}")
                break

        return papers[:limit]

    def format_papers_for_export(self, papers: List[Dict]) -> pd.DataFrame:
        """
        논문 데이터를 DataFrame으로 변환 (지정된 컬럼 순서)
        컬럼 순서: 출판일, 제목, 저자, 저널, 인용수, DOI, 초록
        """
        formatted_data = []

        for paper in papers:
            # 저자 정보 포맷팅
            authors = paper.get('authors', [])
            author_names = ', '.join([a.get('name', '') for a in authors])

            # DOI 추출
            external_ids = paper.get('externalIds', {})
            doi = external_ids.get('DOI', '') if external_ids else ''

            # 출판일 (publicationDate가 있으면 사용, 없으면 year 사용)
            pub_date = paper.get('publicationDate', '')
            if not pub_date and paper.get('year'):
                pub_date = str(paper.get('year'))

            formatted_data.append({
                'Publication Date': pub_date,
                'Title': paper.get('title', ''),
                'Authors': author_names,
                'Journal': paper.get('venue', ''),
                'Citation Count': paper.get('citationCount', 0),
                'DOI': doi,
                'Abstract': paper.get('abstract', '')
            })

        df = pd.DataFrame(formatted_data)

        # 컬럼 순서 확정: 출판일, 제목, 저자, 저널, 인용수, DOI, 초록
        column_order = ['Publication Date', 'Title', 'Authors', 'Journal',
                       'Citation Count', 'DOI', 'Abstract']
        df = df[column_order]

        return df


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
        self.root.geometry("900x700")

        # API 객체
        self.api = SemanticScholarAPI()
        self.filter_obj = None

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

    def create_search_tab(self):
        """논문 검색 탭 생성"""
        # 검색 설정 프레임
        settings_frame = ttk.LabelFrame(self.search_tab, text="검색 설정", padding=10)
        settings_frame.pack(fill='x', padx=10, pady=10)

        # 키워드 입력
        ttk.Label(settings_frame, text="검색 키워드:").grid(row=0, column=0, sticky='w', pady=5)
        self.search_query_entry = ttk.Entry(settings_frame, width=50)
        self.search_query_entry.grid(row=0, column=1, columnspan=2, sticky='ew', pady=5, padx=5)

        # 결과 개수
        ttk.Label(settings_frame, text="결과 개수:").grid(row=1, column=0, sticky='w', pady=5)
        self.limit_var = tk.IntVar(value=100)
        ttk.Entry(settings_frame, textvariable=self.limit_var, width=15).grid(row=1, column=1, sticky='w', pady=5, padx=5)

        # 연도 범위
        ttk.Label(settings_frame, text="연도 범위:").grid(row=2, column=0, sticky='w', pady=5)
        year_frame = ttk.Frame(settings_frame)
        year_frame.grid(row=2, column=1, sticky='w', pady=5, padx=5)

        self.year_from_var = tk.StringVar()
        self.year_to_var = tk.StringVar()
        ttk.Entry(year_frame, textvariable=self.year_from_var, width=8).pack(side='left')
        ttk.Label(year_frame, text=" ~ ").pack(side='left')
        ttk.Entry(year_frame, textvariable=self.year_to_var, width=8).pack(side='left')
        ttk.Label(year_frame, text=" (선택사항)").pack(side='left', padx=5)

        # 저장 경로
        ttk.Label(settings_frame, text="저장 경로:").grid(row=3, column=0, sticky='w', pady=5)
        self.save_path_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.save_path_var, width=40).grid(row=3, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(settings_frame, text="찾아보기", command=self.browse_save_path).grid(row=3, column=2, pady=5, padx=5)

        settings_frame.columnconfigure(1, weight=1)

        # 검색 버튼
        btn_frame = ttk.Frame(self.search_tab)
        btn_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(btn_frame, text="검색 시작", command=self.start_search, width=20).pack()

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
            limit = self.limit_var.get()
            year_from = int(self.year_from_var.get()) if self.year_from_var.get().strip() else None
            year_to = int(self.year_to_var.get()) if self.year_to_var.get().strip() else None

            self.log_search_status(f"검색 시작: '{query}'")
            self.log_search_status(f"최대 {limit}편의 논문을 검색합니다...")

            # 검색 실행
            papers = self.api.search_papers(
                query=query,
                limit=limit,
                year_from=year_from,
                year_to=year_to,
                progress_callback=self.update_progress
            )

            if not papers:
                self.log_search_status("검색 결과가 없습니다.")
                messagebox.showinfo("알림", "검색 결과가 없습니다.")
                return

            self.log_search_status(f"\n총 {len(papers)}편의 논문을 찾았습니다.")
            self.log_search_status("엑셀 파일로 저장 중...")

            # DataFrame 변환 (지정된 컬럼 순서: 출판일, 제목, 저자, 저널, 인용수, DOI, 초록)
            df = self.api.format_papers_for_export(papers)

            # 엑셀 저장
            df.to_excel(save_path, index=False, engine='openpyxl')

            self.log_search_status(f"✓ 저장 완료: {save_path}")
            self.log_search_status(f"✓ 컬럼 순서: 출판일, 제목, 저자, 저널, 인용수, DOI, 초록")

            messagebox.showinfo("완료", f"검색 완료!\n{len(papers)}편의 논문이 저장되었습니다.\n\n{save_path}")

        except Exception as e:
            self.log_search_status(f"\n오류 발생: {str(e)}")
            messagebox.showerror("오류", f"검색 중 오류가 발생했습니다:\n{str(e)}")

    def start_search(self):
        """검색 시작 (별도 스레드)"""
        self.search_status_text.delete(1.0, tk.END)
        self.search_progress['value'] = 0

        # 백그라운드 스레드로 실행
        thread = threading.Thread(target=self.search_thread, daemon=True)
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


def main():
    """메인 함수"""
    root = tk.Tk()
    app = PaperSearchFilterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
