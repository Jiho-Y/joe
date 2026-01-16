import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
import pandas as pd
import openpyxl
import time
import subprocess
from pathlib import Path
from datetime import datetime
import threading
import os
import webbrowser

# Semantic Scholar API v1 엔드포인트
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


class SemanticScholarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Semantic Scholar 논문 검색 도구 v3.1 (macOS)")
        self.root.geometry("1400x900")

        # 변수 초기화
        self.api_key = tk.StringVar()
        self.mode = tk.StringVar(value="new")
        self.existing_file = tk.StringVar()
        self.keywords = []
        self.is_searching = False
        self.existing_papers = []
        self.duplicate_stats = {}
        self.all_results = []  # 모든 검색 결과 저장
        self.filtered_results = []  # 필터링된 결과

        # macOS 복사 붙여넣기 단축키 활성화
        self.setup_mac_shortcuts()

        # 탭 기반 UI 생성
        self.create_widgets()

    def setup_mac_shortcuts(self):
        """macOS 표준 단축키 설정"""
        # Cmd+C, Cmd+V, Cmd+A 등 macOS 단축키 활성화
        self.root.bind_class("Text", "<Command-c>", self.copy_text)
        self.root.bind_class("Text", "<Command-v>", self.paste_text)
        self.root.bind_class("Text", "<Command-a>", self.select_all_text)
        self.root.bind_class("Entry", "<Command-c>", self.copy_entry)
        self.root.bind_class("Entry", "<Command-v>", self.paste_entry)
        self.root.bind_class("Entry", "<Command-a>", self.select_all_entry)

    def copy_text(self, event):
        try:
            event.widget.event_generate("<<Copy>>")
        except:
            pass
        return "break"

    def paste_text(self, event):
        try:
            event.widget.event_generate("<<Paste>>")
        except:
            pass
        return "break"

    def select_all_text(self, event):
        try:
            event.widget.tag_add("sel", "1.0", "end")
        except:
            pass
        return "break"

    def copy_entry(self, event):
        try:
            event.widget.event_generate("<<Copy>>")
        except:
            pass
        return "break"

    def paste_entry(self, event):
        try:
            event.widget.event_generate("<<Paste>>")
        except:
            pass
        return "break"

    def select_all_entry(self, event):
        try:
            event.widget.select_range(0, tk.END)
        except:
            pass
        return "break"

    def create_widgets(self):
        # 노트북 (탭) 생성
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 탭 1: 검색 설정
        self.search_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.search_tab, text="🔍 검색 설정")

        # 탭 2: 결과 보기
        self.results_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.results_tab, text="📊 결과 보기")

        # 각 탭 초기화
        self.create_search_tab()
        self.create_results_tab()

    def create_search_tab(self):
        """검색 설정 탭"""
        main_frame = ttk.Frame(self.search_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 제목
        title_label = ttk.Label(main_frame, text="🔬 Semantic Scholar 논문 검색",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        # API 키 섹션
        api_frame = ttk.LabelFrame(main_frame, text="API 설정", padding="10")
        api_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(api_frame, text="API 키:").grid(row=0, column=0, sticky=tk.W, padx=5)
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=50)
        api_entry.grid(row=0, column=1, padx=5)
        ttk.Label(api_frame, text="(선택사항)", foreground="gray").grid(row=0, column=2)

        # 작업 모드
        mode_frame = ttk.LabelFrame(main_frame, text="작업 모드", padding="10")
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Radiobutton(mode_frame, text="새 검색", variable=self.mode, value="new",
                       command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W, padx=10)
        ttk.Radiobutton(mode_frame, text="기존 파일에 추가", variable=self.mode, value="append",
                       command=self.on_mode_change).grid(row=0, column=1, sticky=tk.W, padx=10)

        self.file_frame = ttk.Frame(mode_frame)
        self.file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(self.file_frame, text="기존 파일:").grid(row=0, column=0, sticky=tk.W)
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.existing_file, width=50, state='disabled')
        self.file_entry.grid(row=0, column=1, padx=5)
        self.file_button = ttk.Button(self.file_frame, text="찾기", command=self.browse_file, state='disabled')
        self.file_button.grid(row=0, column=2)

        # 키워드 입력
        keyword_frame = ttk.LabelFrame(main_frame, text="검색 키워드 (복사 붙여넣기 가능)", padding="10")
        keyword_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # 키워드 리스트
        list_frame = ttk.Frame(keyword_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.keyword_listbox = tk.Listbox(list_frame, height=8, yscrollcommand=scrollbar.set)
        self.keyword_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.keyword_listbox.yview)

        # 키워드 입력
        input_frame = ttk.Frame(keyword_frame)
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="키워드:").pack(side=tk.LEFT, padx=5)
        self.keyword_entry = ttk.Entry(input_frame, width=40)
        self.keyword_entry.pack(side=tk.LEFT, padx=5)
        self.keyword_entry.bind('<Return>', lambda e: self.add_keyword())
        self.keyword_entry.bind('<Command-Return>', lambda e: self.add_keyword())

        ttk.Button(input_frame, text="추가", command=self.add_keyword).pack(side=tk.LEFT, padx=2)
        ttk.Button(input_frame, text="제거", command=self.remove_keyword).pack(side=tk.LEFT, padx=2)
        ttk.Button(input_frame, text="전체 삭제", command=self.clear_keywords).pack(side=tk.LEFT, padx=2)

        # 검색 옵션
        option_frame = ttk.LabelFrame(main_frame, text="검색 옵션", padding="10")
        option_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(option_frame, text="최대 결과 수 (키워드당):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.max_results = tk.IntVar(value=1000)
        ttk.Spinbox(option_frame, from_=100, to=10000, increment=100,
                   textvariable=self.max_results, width=10).grid(row=0, column=1, padx=5)

        # 진행 상황
        progress_frame = ttk.LabelFrame(main_frame, text="진행 상황", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.status_label = ttk.Label(progress_frame, text="대기 중...", foreground="blue")
        self.status_label.pack(anchor=tk.W)

        # 로그
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=10, wrap=tk.WORD, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 버튼
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)

        self.start_button = ttk.Button(button_frame, text="🔍 검색 시작", command=self.start_search)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="⏸ 중지", command=self.stop_search, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # 그리드 가중치
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(5, weight=1)

    def create_results_tab(self):
        """결과 보기 탭"""
        main_frame = ttk.Frame(self.results_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 상단: 필터 및 통계
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)

        # 필터
        filter_frame = ttk.LabelFrame(top_frame, text="필터 및 검색", padding="5")
        filter_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(filter_frame, text="검색:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.apply_filter)
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="키워드:").pack(side=tk.LEFT, padx=5)
        self.filter_keyword = tk.StringVar(value="전체")
        self.keyword_filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_keyword,
                                                 state='readonly', width=20)
        self.keyword_filter_combo['values'] = ["전체"]
        self.keyword_filter_combo.pack(side=tk.LEFT, padx=5)
        self.keyword_filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filter())

        ttk.Button(filter_frame, text="필터 초기화", command=self.clear_filter).pack(side=tk.LEFT, padx=5)

        # 통계
        stat_frame = ttk.LabelFrame(top_frame, text="통계", padding="5")
        stat_frame.pack(side=tk.LEFT, padx=5)

        self.stat_label = ttk.Label(stat_frame, text="논문: 0개")
        self.stat_label.pack()

        # 테이블
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 스크롤바
        y_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        x_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview
        columns = ('Keyword', 'Title', 'Authors', 'Year', 'Venue', 'Citations', 'DOI')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=y_scrollbar.set,
                                xscrollcommand=x_scrollbar.set)

        # 열 설정
        self.tree.heading('Keyword', text='키워드', command=lambda: self.sort_column('Keyword'))
        self.tree.heading('Title', text='제목', command=lambda: self.sort_column('Title'))
        self.tree.heading('Authors', text='저자', command=lambda: self.sort_column('Authors'))
        self.tree.heading('Year', text='연도', command=lambda: self.sort_column('Year'))
        self.tree.heading('Venue', text='학회/저널', command=lambda: self.sort_column('Venue'))
        self.tree.heading('Citations', text='인용수', command=lambda: self.sort_column('Citations'))
        self.tree.heading('DOI', text='DOI', command=lambda: self.sort_column('DOI'))

        self.tree.column('Keyword', width=150)
        self.tree.column('Title', width=400)
        self.tree.column('Authors', width=200)
        self.tree.column('Year', width=60)
        self.tree.column('Venue', width=200)
        self.tree.column('Citations', width=80)
        self.tree.column('DOI', width=150)

        self.tree.pack(fill=tk.BOTH, expand=True)

        y_scrollbar.config(command=self.tree.yview)
        x_scrollbar.config(command=self.tree.xview)

        # 더블클릭으로 URL 열기
        self.tree.bind('<Double-1>', self.open_paper_url)

        # 우클릭 메뉴
        self.create_context_menu()

        # 하단: 버튼
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="📋 선택 항목 복사", command=self.copy_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📄 전체 복사", command=self.copy_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="💾 엑셀로 저장", command=self.export_to_excel).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔗 URL 열기", command=self.open_selected_url).pack(side=tk.LEFT, padx=5)

    def create_context_menu(self):
        """우클릭 컨텍스트 메뉴"""
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="복사", command=self.copy_selected)
        self.context_menu.add_command(label="URL 열기", command=self.open_selected_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="상세 정보 보기", command=self.show_paper_details)

        self.tree.bind('<Button-2>', self.show_context_menu)  # macOS 우클릭
        self.tree.bind('<Control-1>', self.show_context_menu)  # Ctrl+클릭

    def show_context_menu(self, event):
        """컨텍스트 메뉴 표시"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def on_mode_change(self):
        """작업 모드 변경"""
        if self.mode.get() == "append":
            self.file_entry.config(state='normal')
            self.file_button.config(state='normal')
        else:
            self.file_entry.config(state='disabled')
            self.file_button.config(state='disabled')

    def browse_file(self):
        """파일 찾기"""
        filename = filedialog.askopenfilename(
            title="기존 엑셀 파일 선택",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.existing_file.set(filename)
            self.log(f"선택: {filename}")

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

    def remove_keyword(self):
        """키워드 제거"""
        selection = self.keyword_listbox.curselection()
        if selection:
            index = selection[0]
            keyword = self.keywords[index]
            self.keywords.pop(index)
            self.keyword_listbox.delete(index)
            self.log(f"키워드 제거: {keyword}")

    def clear_keywords(self):
        """전체 삭제"""
        if self.keywords and messagebox.askyesno("확인", "모든 키워드를 삭제하시겠습니까?"):
            self.keywords.clear()
            self.keyword_listbox.delete(0, tk.END)
            self.log("전체 삭제됨")

    def log(self, message):
        """로그 출력"""
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def update_status(self, message, color="blue"):
        """상태 업데이트"""
        self.status_label.config(text=message, foreground=color)
        self.root.update_idletasks()

    def update_progress(self, value):
        """진행바 업데이트"""
        self.progress_var.set(value)
        self.root.update_idletasks()

    def send_macos_notification(self, title, message):
        """macOS 알림"""
        try:
            script = f'display notification "{message}" with title "{title}" sound name "Glass"'
            subprocess.call(['osascript', '-e', script])
        except:
            pass

    def populate_results_table(self, papers):
        """결과 테이블 채우기"""
        # 기존 항목 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 데이터 추가
        for paper in papers:
            self.tree.insert('', tk.END, values=(
                paper.get('Keyword', ''),
                paper.get('Title', '')[:100],  # 제목은 100자로 제한
                paper.get('Authors', '')[:50],  # 저자 50자
                paper.get('Year', ''),
                paper.get('Venue', '')[:50],
                paper.get('Citation Count', 0),
                paper.get('DOI', '')
            ), tags=(paper.get('Paper ID', ''),))  # Paper ID를 태그로 저장

        # 통계 업데이트
        self.stat_label.config(text=f"논문: {len(papers)}개")

        # 키워드 필터 콤보박스 업데이트
        keywords = ["전체"] + sorted(set(p.get('Keyword', '') for p in papers))
        self.keyword_filter_combo['values'] = keywords

    def apply_filter(self, *args):
        """필터 적용"""
        search_text = self.search_var.get().lower()
        keyword_filter = self.filter_keyword.get()

        filtered = self.all_results

        # 키워드 필터
        if keyword_filter != "전체":
            filtered = [p for p in filtered if p.get('Keyword') == keyword_filter]

        # 텍스트 검색
        if search_text:
            filtered = [p for p in filtered if
                       search_text in p.get('Title', '').lower() or
                       search_text in p.get('Authors', '').lower() or
                       search_text in p.get('Venue', '').lower() or
                       search_text in str(p.get('Year', '')).lower()]

        self.filtered_results = filtered
        self.populate_results_table(filtered)

    def clear_filter(self):
        """필터 초기화"""
        self.search_var.set("")
        self.filter_keyword.set("전체")
        self.filtered_results = self.all_results
        self.populate_results_table(self.all_results)

    def sort_column(self, col):
        """열 정렬"""
        # 현재 표시된 데이터 가져오기
        data = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]

        # 정렬
        try:
            # 숫자형 정렬 시도
            data.sort(key=lambda t: float(t[0]) if t[0] else 0, reverse=True)
        except:
            # 문자열 정렬
            data.sort(reverse=False)

        # 재배치
        for index, (val, item) in enumerate(data):
            self.tree.move(item, '', index)

    def copy_selected(self):
        """선택 항목 복사"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("알림", "복사할 항목을 선택해주세요.")
            return

        copied_text = []
        for item in selection:
            values = self.tree.item(item)['values']
            copied_text.append('\t'.join(str(v) for v in values))

        text = '\n'.join(copied_text)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log(f"{len(selection)}개 항목 복사됨")
        messagebox.showinfo("복사 완료", f"{len(selection)}개 항목이 클립보드에 복사되었습니다.")

    def copy_all(self):
        """전체 복사"""
        if not self.filtered_results:
            messagebox.showinfo("알림", "복사할 데이터가 없습니다.")
            return

        copied_text = ["키워드\t제목\t저자\t연도\t학회/저널\t인용수\tDOI"]  # 헤더
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            copied_text.append('\t'.join(str(v) for v in values))

        text = '\n'.join(copied_text)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log(f"{len(self.filtered_results)}개 항목 복사됨")
        messagebox.showinfo("복사 완료", f"{len(self.filtered_results)}개 항목이 클립보드에 복사되었습니다.")

    def open_paper_url(self, event):
        """더블클릭으로 URL 열기"""
        self.open_selected_url()

    def open_selected_url(self):
        """선택된 논문 URL 열기"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("알림", "논문을 선택해주세요.")
            return

        # Paper ID로 원본 데이터 찾기
        for item in selection[:3]:  # 최대 3개만
            tags = self.tree.item(item)['tags']
            if tags:
                paper_id = tags[0]
                # all_results에서 해당 논문 찾기
                paper = next((p for p in self.all_results if p.get('Paper ID') == paper_id), None)
                if paper and paper.get('URL') and paper.get('URL') != 'N/A':
                    webbrowser.open(paper['URL'])

    def show_paper_details(self):
        """논문 상세 정보"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("알림", "논문을 선택해주세요.")
            return

        item = selection[0]
        tags = self.tree.item(item)['tags']
        if tags:
            paper_id = tags[0]
            paper = next((p for p in self.all_results if p.get('Paper ID') == paper_id), None)
            if paper:
                details = f"""
제목: {paper.get('Title', 'N/A')}

저자: {paper.get('Authors', 'N/A')}

연도: {paper.get('Year', 'N/A')}

학회/저널: {paper.get('Venue', 'N/A')}

인용수: {paper.get('Citation Count', 0)}

DOI: {paper.get('DOI', 'N/A')}

초록:
{paper.get('Abstract', 'N/A')}

Chicago 인용:
{paper.get('Chicago Citation', 'N/A')}

URL: {paper.get('URL', 'N/A')}
                """
                # 새 창으로 표시
                detail_window = tk.Toplevel(self.root)
                detail_window.title("논문 상세 정보")
                detail_window.geometry("800x600")

                text = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD, padx=10, pady=10)
                text.pack(fill=tk.BOTH, expand=True)
                text.insert(1.0, details.strip())
                text.config(state='disabled')

    def export_to_excel(self):
        """엑셀로 저장"""
        if not self.filtered_results:
            messagebox.showinfo("알림", "저장할 데이터가 없습니다.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"semantic_scholar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

        if filename:
            try:
                df = pd.DataFrame(self.filtered_results)
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
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

                self.log(f"엑셀 저장 완료: {filename}")
                messagebox.showinfo("저장 완료", f"{len(self.filtered_results)}개 논문이 저장되었습니다.")

                if messagebox.askyesno("파일 열기", "저장된 파일을 여시겠습니까?"):
                    subprocess.call(['open', filename])

            except Exception as e:
                messagebox.showerror("오류", f"저장 실패:\n{str(e)}")

    def start_search(self):
        """검색 시작"""
        if not self.keywords:
            messagebox.showerror("오류", "최소 1개 이상의 키워드를 입력해주세요.")
            return

        if self.mode.get() == "append" and not self.existing_file.get():
            messagebox.showerror("오류", "기존 파일을 선택해주세요.")
            return

        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.is_searching = True

        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

        search_thread = threading.Thread(target=self.perform_search, daemon=True)
        search_thread.start()

    def stop_search(self):
        """검색 중지"""
        self.is_searching = False
        self.update_status("중지됨", "orange")
        self.log("검색 중지")
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')

    def perform_search(self):
        """검색 수행"""
        try:
            self.log("=" * 60)
            self.log("검색 시작")
            self.log("=" * 60)

            if self.mode.get() == "append":
                self.update_status("기존 파일 불러오는 중...", "blue")
                self.existing_papers = self.load_existing_excel(self.existing_file.get())

            all_papers_processed = []
            total_keywords = len(self.keywords)

            for i, keyword in enumerate(self.keywords):
                if not self.is_searching:
                    break

                self.log(f"🔍 키워드 {i+1}/{total_keywords}: '{keyword}'")
                self.update_status(f"검색 중... ({i+1}/{total_keywords})", "blue")
                self.update_progress((i / total_keywords) * 100)

                papers_raw = self.search_with_pagination(keyword, self.max_results.get())

                if papers_raw and self.is_searching:
                    papers_processed = self.process_papers(papers_raw, keyword)
                    all_papers_processed.extend(papers_processed)
                    self.log(f"✅ {len(papers_processed)}개 수집")

            if not self.is_searching:
                return

            self.log(f"새로 수집: {len(all_papers_processed)}개")

            if self.mode.get() == "append" and self.existing_papers:
                all_papers_combined = self.existing_papers + all_papers_processed
                self.log(f"기존: {len(self.existing_papers)}개, 병합: {len(all_papers_combined)}개")
            else:
                all_papers_combined = all_papers_processed

            if not all_papers_combined:
                self.log("검색 결과 없음")
                self.update_status("결과 없음", "orange")
                return

            self.update_status("중복 제거 중...", "blue")
            unique_papers, keyword_duplicates = self.remove_duplicates_by_doi(all_papers_combined)

            self.duplicate_stats = keyword_duplicates
            self.all_results = unique_papers
            self.filtered_results = unique_papers

            self.update_progress(100)
            self.update_status("✅ 완료!", "green")
            self.log(f"최종: {len(unique_papers)}개")

            # 결과 탭으로 전환 및 테이블 채우기
            self.notebook.select(self.results_tab)
            self.populate_results_table(unique_papers)

            # 알림
            self.send_macos_notification("검색 완료", f"{len(unique_papers)}개 논문")

            # 완료 메시지
            dup_msg = ""
            if keyword_duplicates:
                dup_lines = [f"• {kw}: {cnt}개" for kw, cnt in keyword_duplicates.items()]
                dup_msg = "\n\n[중복 제거]\n" + "\n".join(dup_lines)

            messagebox.showinfo("완료",
                f"검색 완료!\n\n"
                f"논문: {len(unique_papers)}개{dup_msg}\n\n"
                f"결과 탭에서 확인하세요.")

        except Exception as e:
            self.log(f"오류: {str(e)}")
            self.update_status("오류 발생", "red")
            messagebox.showerror("오류", f"검색 중 오류:\n{str(e)}")
        finally:
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.is_searching = False

    # API 메서드들 (이전과 동일)
    def search_semantic_scholar_single(self, keyword, limit=100, offset=0, max_retries=10):
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
                response = requests.get(API_URL, params=params, headers=headers, timeout=300)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.log(f"⚠️ Rate Limit. {retry_after}초 대기...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    return None
                response.raise_for_status()
                results = response.json()
                if 'data' in results:
                    return results
            except:
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
        return None

    def search_with_pagination(self, keyword, max_results=1000):
        all_papers = []
        offset = 0
        batch_size = 100

        first_result = self.search_semantic_scholar_single(keyword, limit=batch_size, offset=0)
        if not first_result or not self.is_searching:
            return []

        total_available = first_result.get('total', 0)
        papers = first_result.get('data', [])
        if not papers:
            return []

        all_papers.extend(papers)
        self.log(f"  배치 1: {len(papers)}개 (전체 {total_available}개)")

        if len(papers) < batch_size:
            return all_papers

        target = min(max_results, total_available)
        batch_num = 2

        while len(all_papers) < target and self.is_searching:
            offset += batch_size
            if not self.api_key.get().strip():
                time.sleep(1.2)

            result = self.search_semantic_scholar_single(keyword, limit=min(batch_size, target - len(all_papers)), offset=offset)
            if not result or not self.is_searching:
                break

            papers = result.get('data', [])
            if not papers:
                break

            all_papers.extend(papers)
            self.log(f"  배치 {batch_num}: {len(papers)}개 (누적 {len(all_papers)}개)")
            batch_num += 1

        return all_papers

    def format_chicago_citation(self, paper_data):
        authors_list = paper_data.get('authors', [])
        if authors_list:
            if len(authors_list) == 1:
                authors_str = authors_list[0].get('name', 'Unknown')
            elif len(authors_list) == 2:
                authors_str = f"{authors_list[0].get('name', 'Unknown')} and {authors_list[1].get('name', 'Unknown')}"
            elif len(authors_list) > 2:
                authors_str = f"{authors_list[0].get('name', 'Unknown')} et al."
            else:
                authors_str = "Unknown Author"
        else:
            authors_str = "Unknown Author"

        year = paper_data.get('year', 'n.d.')
        title = paper_data.get('title', 'No title')
        venue = paper_data.get('venue', 'Unknown venue')
        citation_count = paper_data.get('citationCount', 0)

        if venue and venue != 'Unknown venue':
            citation = f'{authors_str}. {year}. "{title}." {venue}. (Cited by: {citation_count})'
        else:
            citation = f'{authors_str}. {year}. "{title}." (Cited by: {citation_count})'
        return citation

    def process_papers(self, papers_data, keyword_label=""):
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

            chicago_citation = self.format_chicago_citation(paper)

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
                'Chicago Citation': chicago_citation,
            })
        return processed_list

    def load_existing_excel(self, filepath):
        if not os.path.exists(filepath):
            return []
        try:
            df = pd.read_excel(filepath, sheet_name='Papers')
            existing_papers = df.to_dict('records')
            self.log(f"기존 파일: {len(existing_papers)}개")
            return existing_papers
        except:
            return []

    def remove_duplicates_by_doi(self, all_papers_list):
        original_count = len(all_papers_list)
        papers_with_doi = {}
        papers_without_doi = {}
        keyword_duplicates = {}

        for paper in all_papers_list:
            doi = paper.get('DOI', 'N/A')
            paper_id = paper.get('Paper ID', 'N/A')
            keyword = paper.get('Keyword', 'Unknown')
            is_duplicate = False

            if doi != 'N/A':
                if doi not in papers_with_doi:
                    papers_with_doi[doi] = paper
                else:
                    is_duplicate = True
            else:
                if paper_id != 'N/A' and paper_id not in papers_without_doi:
                    papers_without_doi[paper_id] = paper
                else:
                    is_duplicate = True

            if is_duplicate:
                keyword_duplicates[keyword] = keyword_duplicates.get(keyword, 0) + 1

        unique_papers = list(papers_with_doi.values()) + list(papers_without_doi.values())
        removed_count = original_count - len(unique_papers)

        self.log(f"중복 제거: {removed_count}개")
        if keyword_duplicates:
            for keyword, count in keyword_duplicates.items():
                self.log(f"  • {keyword}: {count}개")

        return unique_papers, keyword_duplicates


def main():
    root = tk.Tk()
    app = SemanticScholarGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
