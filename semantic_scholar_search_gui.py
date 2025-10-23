import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
import pandas as pd
import openpyxl
import time
from pathlib import Path
from datetime import datetime
import threading
import os

# Semantic Scholar API v1 엔드포인트
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


class SemanticScholarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Semantic Scholar 논문 검색 도구 v3.0 GUI")
        self.root.geometry("900x800")

        # 변수 초기화
        self.api_key = tk.StringVar()
        self.mode = tk.StringVar(value="new")
        self.existing_file = tk.StringVar()
        self.keywords = []
        self.is_searching = False
        self.existing_papers = []

        self.create_widgets()

    def create_widgets(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 제목
        title_label = ttk.Label(main_frame, text="🔬 Semantic Scholar 논문 검색 도구",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        # API 키 섹션
        api_frame = ttk.LabelFrame(main_frame, text="API 설정", padding="10")
        api_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(api_frame, text="API 키 (선택):").grid(row=0, column=0, sticky=tk.W)
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=50)
        api_entry.grid(row=0, column=1, padx=5)
        ttk.Label(api_frame, text="※ 미입력 시 Rate Limit 적용",
                 foreground="gray").grid(row=0, column=2, sticky=tk.W)

        # 작업 모드 섹션
        mode_frame = ttk.LabelFrame(main_frame, text="작업 모드", padding="10")
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Radiobutton(mode_frame, text="새로운 검색 (새 파일 생성)",
                       variable=self.mode, value="new",
                       command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="기존 파일에 추가 (중복 제거)",
                       variable=self.mode, value="append",
                       command=self.on_mode_change).grid(row=1, column=0, sticky=tk.W)

        # 기존 파일 선택
        self.file_frame = ttk.Frame(mode_frame)
        self.file_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(self.file_frame, text="기존 파일:").grid(row=0, column=0, sticky=tk.W)
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.existing_file, width=40)
        self.file_entry.grid(row=0, column=1, padx=5)
        self.file_button = ttk.Button(self.file_frame, text="찾아보기...",
                                     command=self.browse_file)
        self.file_button.grid(row=0, column=2)

        # 초기 상태: 파일 선택 비활성화
        self.file_entry.config(state='disabled')
        self.file_button.config(state='disabled')

        # 키워드 섹션
        keyword_frame = ttk.LabelFrame(main_frame, text="검색 키워드", padding="10")
        keyword_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # 키워드 리스트박스와 스크롤바
        listbox_frame = ttk.Frame(keyword_frame)
        listbox_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.keyword_listbox = tk.Listbox(listbox_frame, height=6,
                                          yscrollcommand=scrollbar.set)
        self.keyword_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.keyword_listbox.yview)

        # 키워드 입력 및 버튼
        input_frame = ttk.Frame(keyword_frame)
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(input_frame, text="새 키워드:").grid(row=0, column=0, sticky=tk.W)
        self.keyword_entry = ttk.Entry(input_frame, width=40)
        self.keyword_entry.grid(row=0, column=1, padx=5)
        self.keyword_entry.bind('<Return>', lambda e: self.add_keyword())

        ttk.Button(input_frame, text="추가", command=self.add_keyword).grid(row=0, column=2, padx=2)
        ttk.Button(input_frame, text="제거", command=self.remove_keyword).grid(row=0, column=3, padx=2)
        ttk.Button(input_frame, text="모두 제거", command=self.clear_keywords).grid(row=0, column=4, padx=2)

        # 검색 옵션
        option_frame = ttk.LabelFrame(main_frame, text="검색 옵션", padding="10")
        option_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(option_frame, text="최대 결과 수 (키워드당):").grid(row=0, column=0, sticky=tk.W)
        self.max_results = tk.IntVar(value=1000)
        ttk.Spinbox(option_frame, from_=100, to=10000, increment=100,
                   textvariable=self.max_results, width=10).grid(row=0, column=1, padx=5, sticky=tk.W)

        # 진행 상황 섹션
        progress_frame = ttk.LabelFrame(main_frame, text="진행 상황", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.status_label = ttk.Label(progress_frame, text="대기 중...", foreground="blue")
        self.status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W)

        # 로그 출력
        log_frame = ttk.Frame(progress_frame)
        log_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80,
                                                  state='disabled', wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 버튼 섹션
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)

        self.start_button = ttk.Button(button_frame, text="🔍 검색 시작",
                                       command=self.start_search, style='Accent.TButton')
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(button_frame, text="⏸ 중지",
                                     command=self.stop_search, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=5)

        ttk.Button(button_frame, text="❌ 종료", command=self.root.quit).grid(row=0, column=2, padx=5)

        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(5, weight=2)
        keyword_frame.columnconfigure(0, weight=1)
        keyword_frame.rowconfigure(0, weight=1)
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(2, weight=1)

    def on_mode_change(self):
        """작업 모드 변경 시 파일 선택 활성화/비활성화"""
        if self.mode.get() == "append":
            self.file_entry.config(state='normal')
            self.file_button.config(state='normal')
        else:
            self.file_entry.config(state='disabled')
            self.file_button.config(state='disabled')
            self.existing_file.set("")

    def browse_file(self):
        """파일 찾아보기 대화상자"""
        filename = filedialog.askopenfilename(
            title="기존 엑셀 파일 선택",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.existing_file.set(filename)
            self.log(f"선택된 파일: {filename}")

    def add_keyword(self):
        """키워드 추가"""
        keyword = self.keyword_entry.get().strip()
        if keyword:
            if keyword not in self.keywords:
                self.keywords.append(keyword)
                self.keyword_listbox.insert(tk.END, keyword)
                self.keyword_entry.delete(0, tk.END)
                self.log(f"키워드 추가: {keyword}")
            else:
                messagebox.showwarning("중복", "이미 추가된 키워드입니다.")
        else:
            messagebox.showwarning("입력 오류", "키워드를 입력해주세요.")

    def remove_keyword(self):
        """선택된 키워드 제거"""
        selection = self.keyword_listbox.curselection()
        if selection:
            index = selection[0]
            keyword = self.keywords[index]
            self.keywords.pop(index)
            self.keyword_listbox.delete(index)
            self.log(f"키워드 제거: {keyword}")
        else:
            messagebox.showwarning("선택 오류", "제거할 키워드를 선택해주세요.")

    def clear_keywords(self):
        """모든 키워드 제거"""
        if self.keywords:
            if messagebox.askyesno("확인", "모든 키워드를 제거하시겠습니까?"):
                self.keywords.clear()
                self.keyword_listbox.delete(0, tk.END)
                self.log("모든 키워드 제거됨")

    def log(self, message):
        """로그 메시지 출력"""
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def update_status(self, message, color="blue"):
        """상태 레이블 업데이트"""
        self.status_label.config(text=message, foreground=color)
        self.root.update_idletasks()

    def update_progress(self, value):
        """프로그레스 바 업데이트"""
        self.progress_var.set(value)
        self.root.update_idletasks()

    def start_search(self):
        """검색 시작"""
        # 유효성 검사
        if not self.keywords:
            messagebox.showerror("오류", "최소 1개 이상의 키워드를 입력해주세요.")
            return

        if self.mode.get() == "append" and not self.existing_file.get():
            messagebox.showerror("오류", "기존 파일을 선택해주세요.")
            return

        # UI 상태 변경
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.is_searching = True

        # 로그 초기화
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

        # 별도 스레드에서 검색 실행
        search_thread = threading.Thread(target=self.perform_search, daemon=True)
        search_thread.start()

    def stop_search(self):
        """검색 중지"""
        self.is_searching = False
        self.update_status("검색 중지됨", "orange")
        self.log("사용자에 의해 검색이 중지되었습니다.")
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')

    def perform_search(self):
        """실제 검색 수행 (별도 스레드에서 실행)"""
        try:
            self.log("=" * 60)
            self.log("검색 시작")
            self.log("=" * 60)

            # 기존 파일 불러오기 (append 모드)
            if self.mode.get() == "append":
                self.update_status("기존 파일 불러오는 중...", "blue")
                self.existing_papers = self.load_existing_excel(self.existing_file.get())
                if not self.existing_papers:
                    self.log("⚠️  기존 파일을 불러올 수 없습니다. 새로운 파일로 생성합니다.")

            # 검색 수행
            all_papers_processed = []
            total_keywords = len(self.keywords)

            for i, keyword in enumerate(self.keywords):
                if not self.is_searching:
                    break

                self.log("-" * 60)
                self.log(f"🔍 키워드 {i+1}/{total_keywords}: '{keyword}'")
                self.update_status(f"검색 중... ({i+1}/{total_keywords})", "blue")
                self.update_progress((i / total_keywords) * 100)

                # 검색
                papers_raw = self.search_with_pagination(keyword, self.max_results.get())

                if papers_raw and self.is_searching:
                    papers_processed = self.process_papers(papers_raw, keyword)
                    all_papers_processed.extend(papers_processed)
                    self.log(f"✅ 키워드 {i+1} 완료: {len(papers_processed)}개 논문 수집")
                else:
                    self.log(f"⚠️  키워드 {i+1} 검색 결과 없음")

            if not self.is_searching:
                return

            # 결과 요약
            self.log("=" * 60)
            self.log("검색 결과 요약")
            self.log(f"새로 수집된 논문: {len(all_papers_processed)}개")

            # 기존 데이터와 병합
            if self.mode.get() == "append" and self.existing_papers:
                all_papers_combined = self.existing_papers + all_papers_processed
                self.log(f"기존 논문: {len(self.existing_papers)}개")
                self.log(f"병합 전 총합: {len(all_papers_combined)}개")
            else:
                all_papers_combined = all_papers_processed

            if not all_papers_combined:
                self.log("⚠️  검색된 논문이 없습니다.")
                self.update_status("검색 완료 (결과 없음)", "orange")
                return

            # 중복 제거
            self.update_status("중복 제거 중...", "blue")
            unique_papers = self.remove_duplicates_by_doi(all_papers_combined)

            # 파일 저장
            self.update_status("파일 저장 중...", "blue")
            self.update_progress(90)

            if self.mode.get() == "append" and self.existing_file.get():
                filename = self.existing_file.get()
                self.log(f"💾 기존 파일 업데이트: {filename}")
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"semantic_scholar_results_{timestamp}.xlsx"
                self.log(f"💾 새 파일 생성: {filename}")

            success = self.save_to_excel(unique_papers, filename)

            if success:
                self.update_progress(100)
                self.update_status("✅ 검색 완료!", "green")
                self.log("=" * 60)
                self.log("🎉 검색이 성공적으로 완료되었습니다!")
                self.log(f"📊 최종 논문 수: {len(unique_papers)}개")
                self.log(f"📁 파일: {filename}")
                self.log("=" * 60)

                # 완료 메시지
                if messagebox.askyesno("완료",
                    f"검색이 완료되었습니다!\n\n"
                    f"논문 수: {len(unique_papers)}개\n"
                    f"파일: {filename}\n\n"
                    f"파일을 여시겠습니까?"):
                    try:
                        os.startfile(filename)  # Windows
                    except:
                        try:
                            os.system(f'xdg-open "{filename}"')  # Linux
                        except:
                            try:
                                os.system(f'open "{filename}"')  # macOS
                            except:
                                pass
            else:
                self.update_status("❌ 저장 실패", "red")

        except Exception as e:
            self.log(f"❌ 오류 발생: {str(e)}")
            self.update_status("❌ 오류 발생", "red")
            messagebox.showerror("오류", f"검색 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.is_searching = False

    # 검색 관련 메서드들
    def search_semantic_scholar_single(self, keyword, limit=100, offset=0, max_retries=10):
        """단일 검색 요청"""
        params = {
            'query': keyword,
            'limit': min(limit, 100),
            'offset': offset,
            'fields': 'title,authors,year,abstract,url,venue,citationCount,publicationDate,paperId,externalIds'
        }

        headers = {'User-Agent': 'Mozilla/5.0 (Academic Research Tool)'}

        api_key = self.api_key.get().strip()
        if api_key:
            headers['x-api-key'] = api_key

        for attempt in range(max_retries):
            if not self.is_searching:
                return None

            try:
                if attempt > 0:
                    self.log(f"📌 재시도 {attempt + 1}/{max_retries}")

                response = requests.get(API_URL, params=params, headers=headers, timeout=300)

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.log(f"⚠️  Rate Limit 초과. {retry_after}초 대기...")

                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    else:
                        return None

                response.raise_for_status()
                results = response.json()

                if 'data' not in results:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None

                return results

            except requests.exceptions.Timeout:
                self.log(f"⚠️  타임아웃 ({attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                else:
                    return None

            except Exception as e:
                self.log(f"⚠️  오류: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
                else:
                    return None

        return None

    def search_with_pagination(self, keyword, max_results=1000):
        """페이지네이션 검색"""
        all_papers = []
        offset = 0
        batch_size = 100

        # 첫 번째 요청
        first_result = self.search_semantic_scholar_single(keyword, limit=batch_size, offset=0)

        if first_result is None or not self.is_searching:
            return []

        total_available = first_result.get('total', 0)
        papers = first_result.get('data', [])

        if not papers:
            return []

        all_papers.extend(papers)
        self.log(f"   배치 1: {len(papers)}개 (전체 {total_available}개)")

        if len(papers) < batch_size:
            return all_papers

        target = min(max_results, total_available)
        batch_num = 2

        while len(all_papers) < target and self.is_searching:
            offset += batch_size
            remaining = target - len(all_papers)
            current_limit = min(batch_size, remaining)

            # Rate limit
            if not self.api_key.get().strip():
                time.sleep(1.2)

            result = self.search_semantic_scholar_single(keyword, limit=current_limit, offset=offset)

            if result is None or not self.is_searching:
                break

            papers = result.get('data', [])

            if not papers:
                break

            all_papers.extend(papers)
            self.log(f"   배치 {batch_num}: {len(papers)}개 (누적 {len(all_papers)}개)")
            batch_num += 1

            if len(all_papers) >= total_available:
                break

        return all_papers

    def process_papers(self, papers_data, keyword_label=""):
        """논문 데이터 가공"""
        processed_list = []

        for paper in papers_data:
            authors_list = paper.get('authors', [])
            if authors_list:
                authors = ", ".join([author.get('name', 'Unknown') for author in authors_list])
            else:
                authors = "No authors listed"

            abstract = paper.get('abstract', 'No abstract available')
            if abstract and len(abstract) > 32767:
                abstract = abstract[:32760] + "..."

            doi = 'N/A'
            external_ids = paper.get('externalIds', {})
            if external_ids:
                doi = external_ids.get('DOI', 'N/A')

            processed_list.append({
                'Keyword': keyword_label,
                'Paper ID': paper.get('paperId', 'N/A'),
                'DOI': doi,
                'Title': paper.get('title', 'No title'),
                'Authors': authors,
                'Year': paper.get('year', 'N/A'),
                'Publication Date': paper.get('publicationDate', 'N/A'),
                'Venue': paper.get('venue', 'N/A'),
                'Citation Count': paper.get('citationCount', 0),
                'Abstract': abstract,
                'URL': paper.get('url', 'N/A'),
            })

        return processed_list

    def load_existing_excel(self, filepath):
        """기존 엑셀 파일 불러오기"""
        if not os.path.exists(filepath):
            self.log(f"⚠️  파일을 찾을 수 없습니다: {filepath}")
            return []

        try:
            df = pd.read_excel(filepath, sheet_name='Papers')
            existing_papers = df.to_dict('records')
            self.log(f"✅ 기존 논문 {len(existing_papers)}개 불러오기 완료")
            return existing_papers
        except Exception as e:
            self.log(f"❌ 파일 불러오기 오류: {str(e)}")
            return []

    def remove_duplicates_by_doi(self, all_papers_list):
        """DOI 기준 중복 제거"""
        self.log("-" * 60)
        self.log("중복 제거 처리 중...")

        original_count = len(all_papers_list)
        papers_with_doi = {}
        papers_without_doi = {}

        for paper in all_papers_list:
            doi = paper.get('DOI', 'N/A')
            paper_id = paper.get('Paper ID', 'N/A')

            if doi != 'N/A':
                if doi not in papers_with_doi:
                    papers_with_doi[doi] = paper
            else:
                if paper_id != 'N/A' and paper_id not in papers_without_doi:
                    papers_without_doi[paper_id] = paper

        unique_papers = list(papers_with_doi.values()) + list(papers_without_doi.values())
        removed_count = original_count - len(unique_papers)

        self.log(f"원본: {original_count}개")
        self.log(f"중복 제거: {removed_count}개")
        self.log(f"최종: {len(unique_papers)}개")

        return unique_papers

    def save_to_excel(self, papers_list, filename):
        """엑셀 파일로 저장"""
        if not papers_list:
            self.log("⚠️  저장할 데이터가 없습니다.")
            return False

        try:
            df = pd.DataFrame(papers_list)
            output_path = Path(filename).absolute()

            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Papers')
                worksheet = writer.sheets['Papers']

                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter

                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass

                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            self.log(f"✅ 파일 저장 완료: {output_path}")
            return True

        except Exception as e:
            self.log(f"❌ 파일 저장 오류: {str(e)}")
            return False


def main():
    root = tk.Tk()
    app = SemanticScholarGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
