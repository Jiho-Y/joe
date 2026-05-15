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
import json
import csv

CONFIG_FILE = Path.home() / ".semantic_scholar_config.json"
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


class SemanticScholarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Semantic Scholar 논문 검색 도구 v4.0 (macOS)")
        self.root.geometry("1500x950")
        self.root.minsize(1200, 700)

        self.api_key = tk.StringVar()
        self.mode = tk.StringVar(value="new")
        self.existing_file = tk.StringVar()
        self.keywords = []
        self.is_searching = False
        self.existing_papers = []
        self.duplicate_stats = {}
        self.all_results = []
        self.filtered_results = []
        self._sort_col = None
        self._sort_reverse = False

        self._saved_settings = {}
        self.load_settings()
        self.setup_mac_shortcuts()
        self.create_widgets()
        self.restore_from_settings()

    def setup_mac_shortcuts(self):
        """macOS 표준 단축키 — Text, Entry, TEntry(ttk) 모두 커버"""
        for cls in ("Text", "Entry", "TEntry"):
            self.root.bind_class(cls, "<Command-c>", self._cmd_copy)
            self.root.bind_class(cls, "<Command-v>", self._cmd_paste)
            self.root.bind_class(cls, "<Command-a>", self._cmd_select_all)
            self.root.bind_class(cls, "<Command-x>", self._cmd_cut)
            self.root.bind_class(cls, "<Command-z>", self._cmd_undo)

    def _cmd_copy(self, event):
        try:
            event.widget.event_generate("<<Copy>>")
        except Exception:
            pass
        return "break"

    def _cmd_cut(self, event):
        try:
            event.widget.event_generate("<<Cut>>")
        except Exception:
            pass
        return "break"

    def _cmd_paste(self, event):
        try:
            event.widget.event_generate("<<Paste>>")
        except Exception:
            pass
        return "break"

    def _cmd_select_all(self, event):
        try:
            w = event.widget
            if hasattr(w, "tag_add"):
                w.tag_add("sel", "1.0", "end")
            elif hasattr(w, "select_range"):
                w.select_range(0, tk.END)
        except Exception:
            pass
        return "break"

    def _cmd_undo(self, event):
        try:
            event.widget.event_generate("<<Undo>>")
        except Exception:
            pass
        return "break"

    # ── Settings ────────────────────────────────────────────────────────────

    def load_settings(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._saved_settings = json.load(f)
                if "api_key" in self._saved_settings:
                    self.api_key.set(self._saved_settings["api_key"])
        except Exception:
            pass

    def save_settings(self, silent=False):
        try:
            settings = {
                "api_key": self.api_key.get().strip(),
                "keywords": self.keywords,
                "max_results": self.max_results.get(),
                "mode": self.mode.get(),
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            if not silent:
                self.log(f"설정 저장: {CONFIG_FILE}")
                messagebox.showinfo("저장 완료", "설정이 저장되었습니다.")
        except Exception as e:
            if not silent:
                messagebox.showerror("오류", f"설정 저장 실패:\n{e}")

    def load_settings_from_file(self):
        filename = filedialog.askopenfilename(
            title="설정 파일 선택",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                settings = json.load(f)
            if "api_key" in settings:
                self.api_key.set(settings["api_key"])
            if "max_results" in settings:
                self.max_results.set(settings["max_results"])
            if "keywords" in settings:
                for kw in settings["keywords"]:
                    if kw not in self.keywords:
                        self.keywords.append(kw)
                        self.keyword_listbox.insert(tk.END, kw)
                self._update_keyword_count()
            self.log(f"설정 불러오기: {filename}")
            messagebox.showinfo("완료", "설정을 불러왔습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"설정 불러오기 실패:\n{e}")

    def restore_from_settings(self):
        if "keywords" in self._saved_settings:
            for kw in self._saved_settings["keywords"]:
                if kw not in self.keywords:
                    self.keywords.append(kw)
                    self.keyword_listbox.insert(tk.END, kw)
            self._update_keyword_count()
        if "max_results" in self._saved_settings:
            try:
                self.max_results.set(self._saved_settings["max_results"])
            except Exception:
                pass
        if "mode" in self._saved_settings:
            self.mode.set(self._saved_settings["mode"])
            self.on_mode_change()

    # ── Widget creation ──────────────────────────────────────────────────────

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.search_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.search_tab, text="🔍 검색 설정")

        self.results_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.results_tab, text="📊 결과 보기")

        self.create_search_tab()
        self.create_results_tab()

        statusbar = ttk.Frame(self.root, relief=tk.SUNKEN)
        statusbar.pack(fill=tk.X, side=tk.BOTTOM)
        self.statusbar_label = ttk.Label(statusbar, text="준비", anchor=tk.W, padding=(6, 2))
        self.statusbar_label.pack(side=tk.LEFT)

    def create_search_tab(self):
        main_frame = ttk.Frame(self.search_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text="🔬 Semantic Scholar 논문 검색",
            font=("SF Pro Display", 16, "bold"),
        ).grid(row=0, column=0, columnspan=3, pady=(0, 10))

        # API 설정
        api_frame = ttk.LabelFrame(main_frame, text="API 설정", padding="8")
        api_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=3)
        api_frame.columnconfigure(1, weight=1)

        ttk.Label(api_frame, text="API 키:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Entry(api_frame, textvariable=self.api_key, width=55).grid(
            row=0, column=1, padx=5, sticky=(tk.W, tk.E)
        )
        ttk.Label(api_frame, text="(선택사항)", foreground="gray").grid(row=0, column=2)

        btn_row = ttk.Frame(api_frame)
        btn_row.grid(row=1, column=0, columnspan=3, pady=(5, 0), sticky=tk.W)
        ttk.Button(btn_row, text="💾 설정 저장", command=self.save_settings).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="📂 설정 불러오기", command=self.load_settings_from_file).pack(
            side=tk.LEFT, padx=2
        )

        # 작업 모드
        mode_frame = ttk.LabelFrame(main_frame, text="작업 모드", padding="8")
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=3)

        ttk.Radiobutton(
            mode_frame, text="새 검색", variable=self.mode, value="new", command=self.on_mode_change
        ).grid(row=0, column=0, sticky=tk.W, padx=10)
        ttk.Radiobutton(
            mode_frame,
            text="기존 파일에 추가",
            variable=self.mode,
            value="append",
            command=self.on_mode_change,
        ).grid(row=0, column=1, sticky=tk.W, padx=10)

        self.file_frame = ttk.Frame(mode_frame)
        self.file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=3)
        ttk.Label(self.file_frame, text="기존 파일:").grid(row=0, column=0, sticky=tk.W)
        self.file_entry = ttk.Entry(
            self.file_frame, textvariable=self.existing_file, width=52, state="disabled"
        )
        self.file_entry.grid(row=0, column=1, padx=5)
        self.file_button = ttk.Button(
            self.file_frame, text="찾기", command=self.browse_file, state="disabled"
        )
        self.file_button.grid(row=0, column=2)

        # 키워드 입력
        keyword_frame = ttk.LabelFrame(main_frame, text="검색 키워드", padding="8")
        keyword_frame.grid(
            row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=3
        )

        list_frame = ttk.Frame(keyword_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.keyword_listbox = tk.Listbox(
            list_frame,
            height=7,
            yscrollcommand=scrollbar.set,
            selectmode=tk.EXTENDED,
            activestyle="dotbox",
        )
        self.keyword_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.keyword_listbox.yview)
        self.keyword_listbox.bind("<Delete>", lambda e: self.remove_keyword())
        self.keyword_listbox.bind("<BackSpace>", lambda e: self.remove_keyword())

        input_row = ttk.Frame(keyword_frame)
        input_row.pack(fill=tk.X, pady=(5, 2))

        ttk.Label(input_row, text="키워드:").pack(side=tk.LEFT, padx=(0, 4))
        self.keyword_entry = ttk.Entry(input_row, width=38)
        self.keyword_entry.pack(side=tk.LEFT, padx=(0, 4))
        self.keyword_entry.bind("<Return>", lambda e: self.add_keyword())

        ttk.Button(input_row, text="추가", command=self.add_keyword, width=6).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(input_row, text="제거", command=self.remove_keyword, width=6).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(input_row, text="전체 삭제", command=self.clear_keywords).pack(
            side=tk.LEFT, padx=2
        )

        bulk_row = ttk.Frame(keyword_frame)
        bulk_row.pack(fill=tk.X, pady=(2, 0))

        ttk.Button(
            bulk_row,
            text="📋 클립보드에서 붙여넣기 (여러 줄)",
            command=self.paste_keywords_from_clipboard,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            bulk_row, text="📂 파일에서 불러오기", command=self.import_keywords_from_file
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(bulk_row, text="📤 키워드 내보내기", command=self.export_keywords).pack(
            side=tk.LEFT, padx=2
        )

        self.keyword_count_label = ttk.Label(bulk_row, text="0개 키워드", foreground="gray")
        self.keyword_count_label.pack(side=tk.RIGHT, padx=5)

        # 검색 옵션
        option_frame = ttk.LabelFrame(main_frame, text="검색 옵션", padding="8")
        option_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=3)

        ttk.Label(option_frame, text="최대 결과 수 (키워드당):").grid(
            row=0, column=0, sticky=tk.W, padx=5
        )
        self.max_results = tk.IntVar(value=1000)
        ttk.Spinbox(
            option_frame, from_=100, to=10000, increment=100, textvariable=self.max_results, width=10
        ).grid(row=0, column=1, padx=5)

        # 진행 상황
        progress_frame = ttk.LabelFrame(main_frame, text="진행 상황", padding="8")
        progress_frame.grid(
            row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=3
        )

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=4)

        self.status_label = ttk.Label(progress_frame, text="대기 중...", foreground="blue")
        self.status_label.pack(anchor=tk.W)

        self.log_text = scrolledtext.ScrolledText(
            progress_frame, height=8, wrap=tk.WORD, state="disabled", font=("Menlo", 11)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=4)

        # 버튼
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=8)

        self.start_button = ttk.Button(
            button_frame, text="🔍 검색 시작", command=self.start_search
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            button_frame, text="⏸ 중지", command=self.stop_search, state="disabled"
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(5, weight=1)

    def create_results_tab(self):
        main_frame = ttk.Frame(self.results_tab, padding="8")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 필터 행
        filter_frame = ttk.LabelFrame(main_frame, text="필터 및 검색", padding="5")
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        row1 = ttk.Frame(filter_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="텍스트 검색:").pack(side=tk.LEFT, padx=4)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.apply_filter)
        ttk.Entry(row1, textvariable=self.search_var, width=26).pack(side=tk.LEFT, padx=4)

        ttk.Label(row1, text="키워드:").pack(side=tk.LEFT, padx=4)
        self.filter_keyword = tk.StringVar(value="전체")
        self.keyword_filter_combo = ttk.Combobox(
            row1, textvariable=self.filter_keyword, state="readonly", width=18
        )
        self.keyword_filter_combo["values"] = ["전체"]
        self.keyword_filter_combo.pack(side=tk.LEFT, padx=4)
        self.keyword_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        ttk.Label(row1, text="연도:").pack(side=tk.LEFT, padx=4)
        self.year_from = tk.StringVar()
        self.year_to = tk.StringVar()
        ttk.Entry(row1, textvariable=self.year_from, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(row1, text="~").pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.year_to, width=6).pack(side=tk.LEFT, padx=2)
        self.year_from.trace("w", self.apply_filter)
        self.year_to.trace("w", self.apply_filter)

        ttk.Label(row1, text="최소 인용수:").pack(side=tk.LEFT, padx=4)
        self.min_citations = tk.StringVar()
        ttk.Entry(row1, textvariable=self.min_citations, width=8).pack(side=tk.LEFT, padx=2)
        self.min_citations.trace("w", self.apply_filter)

        ttk.Button(row1, text="초기화", command=self.clear_filter).pack(side=tk.LEFT, padx=6)
        self.stat_label = ttk.Label(row1, text="논문: 0개", foreground="gray")
        self.stat_label.pack(side=tk.RIGHT, padx=5)

        # 테이블 + 초록 미리보기 패널
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        table_frame = ttk.Frame(paned)
        paned.add(table_frame, weight=3)

        y_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        columns = ("Keyword", "Title", "Authors", "Year", "Venue", "Citations", "DOI")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
        )

        col_cfg = [
            ("Keyword", "키워드", 140),
            ("Title", "제목", 380),
            ("Authors", "저자", 190),
            ("Year", "연도", 58),
            ("Venue", "학회/저널", 190),
            ("Citations", "인용수", 72),
            ("DOI", "DOI", 150),
        ]
        for col, heading, width in col_cfg:
            self.tree.heading(col, text=heading, command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=width)

        self.tree.pack(fill=tk.BOTH, expand=True)
        y_scrollbar.config(command=self.tree.yview)
        x_scrollbar.config(command=self.tree.xview)
        self.tree.bind("<Double-1>", self.open_paper_url)
        self.tree.bind("<<TreeviewSelect>>", self.on_paper_select)
        self.create_context_menu()

        # 초록 미리보기 패널
        preview_frame = ttk.LabelFrame(paned, text="논문 상세 / 초록 미리보기", padding="5")
        paned.add(preview_frame, weight=1)

        self.preview_text = scrolledtext.ScrolledText(
            preview_frame, height=6, wrap=tk.WORD, state="disabled", font=("SF Pro Text", 12)
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        # 하단 버튼
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=4)

        ttk.Button(button_frame, text="📋 선택 복사", command=self.copy_selected).pack(
            side=tk.LEFT, padx=3
        )
        ttk.Button(button_frame, text="📄 전체 복사", command=self.copy_all).pack(
            side=tk.LEFT, padx=3
        )
        ttk.Button(button_frame, text="💾 Excel 저장", command=self.export_to_excel).pack(
            side=tk.LEFT, padx=3
        )
        ttk.Button(button_frame, text="📊 CSV 저장", command=self.export_to_csv).pack(
            side=tk.LEFT, padx=3
        )
        ttk.Button(button_frame, text="🔗 URL 열기", command=self.open_selected_url).pack(
            side=tk.LEFT, padx=3
        )
        ttk.Button(button_frame, text="🗑 결과 지우기", command=self.clear_results).pack(
            side=tk.RIGHT, padx=3
        )

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="복사", command=self.copy_selected)
        self.context_menu.add_command(label="URL 열기", command=self.open_selected_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="상세 정보 보기", command=self.show_paper_details)
        self.tree.bind("<Button-2>", self.show_context_menu)
        self.tree.bind("<Control-1>", self.show_context_menu)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # ── Mode ────────────────────────────────────────────────────────────────

    def on_mode_change(self):
        state = "normal" if self.mode.get() == "append" else "disabled"
        self.file_entry.config(state=state)
        self.file_button.config(state=state)

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="기존 엑셀 파일 선택",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if filename:
            self.existing_file.set(filename)
            self.log(f"선택: {filename}")

    # ── Keyword management ───────────────────────────────────────────────────

    def _update_keyword_count(self):
        self.keyword_count_label.config(text=f"{len(self.keywords)}개 키워드")

    def add_keyword(self):
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            return
        if keyword in self.keywords:
            messagebox.showwarning("중복", "이미 추가된 키워드입니다.")
            return
        self.keywords.append(keyword)
        self.keyword_listbox.insert(tk.END, keyword)
        self.keyword_entry.delete(0, tk.END)
        self._update_keyword_count()
        self.log(f"키워드 추가: {keyword}")

    def remove_keyword(self):
        selection = list(self.keyword_listbox.curselection())
        if not selection:
            return
        for index in reversed(selection):
            self.log(f"키워드 제거: {self.keywords[index]}")
            self.keywords.pop(index)
            self.keyword_listbox.delete(index)
        self._update_keyword_count()

    def clear_keywords(self):
        if self.keywords and messagebox.askyesno("확인", "모든 키워드를 삭제하시겠습니까?"):
            self.keywords.clear()
            self.keyword_listbox.delete(0, tk.END)
            self._update_keyword_count()
            self.log("전체 삭제됨")

    def paste_keywords_from_clipboard(self):
        """클립보드에서 여러 줄 키워드 붙여넣기"""
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("알림", "클립보드가 비어 있습니다.")
            return
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        added = sum(
            1
            for line in lines
            if line not in self.keywords
            and not self.keywords.append(line)  # side effect: append
            and not self.keyword_listbox.insert(tk.END, line)
        )
        self._update_keyword_count()
        if added:
            self.log(f"{added}개 키워드 붙여넣기 완료")
            messagebox.showinfo("완료", f"{added}개 키워드가 추가되었습니다.")
        else:
            messagebox.showinfo("알림", "새로운 키워드가 없습니다 (모두 중복).")

    def import_keywords_from_file(self):
        """텍스트 파일에서 키워드 불러오기 (한 줄 = 한 키워드)"""
        filename = filedialog.askopenfilename(
            title="키워드 파일 선택",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            added = 0
            for line in lines:
                if line not in self.keywords:
                    self.keywords.append(line)
                    self.keyword_listbox.insert(tk.END, line)
                    added += 1
            self._update_keyword_count()
            self.log(f"파일에서 {added}개 키워드 불러옴")
            messagebox.showinfo("완료", f"{added}개 키워드를 불러왔습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"파일 불러오기 실패:\n{e}")

    def export_keywords(self):
        if not self.keywords:
            messagebox.showinfo("알림", "내보낼 키워드가 없습니다.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="keywords.txt",
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(self.keywords))
            self.log(f"키워드 내보내기: {filename}")
            messagebox.showinfo("완료", f"{len(self.keywords)}개 키워드를 저장했습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패:\n{e}")

    # ── Log / Status ─────────────────────────────────────────────────────────

    def log(self, message):
        self.log_text.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.statusbar_label.config(text=message)
        self.root.update_idletasks()

    def update_status(self, message, color="blue"):
        self.status_label.config(text=message, foreground=color)
        self.statusbar_label.config(text=message)
        self.root.update_idletasks()

    def update_progress(self, value):
        self.progress_var.set(value)
        self.root.update_idletasks()

    def send_macos_notification(self, title, message):
        try:
            script = f'display notification "{message}" with title "{title}" sound name "Glass"'
            subprocess.call(["osascript", "-e", script])
        except Exception:
            pass

    # ── Results table ────────────────────────────────────────────────────────

    def populate_results_table(self, papers):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for paper in papers:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    paper.get("Keyword", ""),
                    paper.get("Title", "")[:120],
                    paper.get("Authors", "")[:60],
                    paper.get("Year", ""),
                    paper.get("Venue", "")[:50],
                    paper.get("Citation Count", 0),
                    paper.get("DOI", ""),
                ),
                tags=(paper.get("Paper ID", ""),),
            )
        self.stat_label.config(text=f"논문: {len(papers)}개")
        keywords = ["전체"] + sorted(
            set(p.get("Keyword", "") for p in papers if p.get("Keyword"))
        )
        self.keyword_filter_combo["values"] = keywords

    def on_paper_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        tags = self.tree.item(selection[0])["tags"]
        if not tags:
            return
        paper = next((p for p in self.all_results if p.get("Paper ID") == tags[0]), None)
        if not paper:
            return
        preview = (
            f"제목: {paper.get('Title', 'N/A')}\n"
            f"저자: {paper.get('Authors', 'N/A')}\n"
            f"연도: {paper.get('Year', 'N/A')}  |  "
            f"학회/저널: {paper.get('Venue', 'N/A')}  |  "
            f"인용수: {paper.get('Citation Count', 0)}\n"
            f"DOI: {paper.get('DOI', 'N/A')}\n"
            f"URL: {paper.get('URL', 'N/A')}\n\n"
            f"초록:\n{paper.get('Abstract', '초록 없음')}"
        )
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", preview)
        self.preview_text.config(state="disabled")

    def apply_filter(self, *args):
        search_text = self.search_var.get().lower()
        keyword_filter = self.filter_keyword.get()
        year_from = self.year_from.get().strip()
        year_to = self.year_to.get().strip()
        min_cit = self.min_citations.get().strip()

        filtered = self.all_results

        if keyword_filter != "전체":
            filtered = [p for p in filtered if p.get("Keyword") == keyword_filter]

        if year_from.isdigit():
            filtered = [
                p
                for p in filtered
                if str(p.get("Year", "")).isdigit()
                and int(p.get("Year", 0)) >= int(year_from)
            ]

        if year_to.isdigit():
            filtered = [
                p
                for p in filtered
                if str(p.get("Year", "")).isdigit()
                and int(p.get("Year", 0)) <= int(year_to)
            ]

        if min_cit.isdigit():
            filtered = [
                p for p in filtered if int(p.get("Citation Count", 0)) >= int(min_cit)
            ]

        if search_text:
            filtered = [
                p
                for p in filtered
                if search_text in p.get("Title", "").lower()
                or search_text in p.get("Authors", "").lower()
                or search_text in p.get("Venue", "").lower()
                or search_text in p.get("Abstract", "").lower()
                or search_text in str(p.get("Year", "")).lower()
            ]

        self.filtered_results = filtered
        self.populate_results_table(filtered)

    def clear_filter(self):
        self.search_var.set("")
        self.filter_keyword.set("전체")
        self.year_from.set("")
        self.year_to.set("")
        self.min_citations.set("")
        self.filtered_results = self.all_results
        self.populate_results_table(self.all_results)

    def sort_column(self, col):
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        data = [(self.tree.set(item, col), item) for item in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0]) if t[0] else 0, reverse=self._sort_reverse)
        except ValueError:
            data.sort(key=lambda t: t[0].lower(), reverse=self._sort_reverse)

        for index, (_, item) in enumerate(data):
            self.tree.move(item, "", index)

        heading_map = {
            "Keyword": "키워드",
            "Title": "제목",
            "Authors": "저자",
            "Year": "연도",
            "Venue": "학회/저널",
            "Citations": "인용수",
            "DOI": "DOI",
        }
        for c in heading_map:
            arrow = (" ▼" if self._sort_reverse else " ▲") if c == col else ""
            self.tree.heading(c, text=heading_map[c] + arrow)

    def clear_results(self):
        if messagebox.askyesno("확인", "결과를 모두 지우시겠습니까?"):
            self.all_results = []
            self.filtered_results = []
            self.populate_results_table([])
            self.preview_text.config(state="normal")
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.config(state="disabled")
            self.log("결과 지움")

    # ── Copy / Export ────────────────────────────────────────────────────────

    def copy_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("알림", "복사할 항목을 선택해주세요.")
            return
        lines = [
            "\t".join(str(v) for v in self.tree.item(item)["values"]) for item in selection
        ]
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.log(f"{len(selection)}개 항목 복사됨")

    def copy_all(self):
        if not self.filtered_results:
            messagebox.showinfo("알림", "복사할 데이터가 없습니다.")
            return
        header = "키워드\t제목\t저자\t연도\t학회/저널\t인용수\tDOI"
        lines = [header] + [
            "\t".join(str(v) for v in self.tree.item(item)["values"])
            for item in self.tree.get_children()
        ]
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.log(f"{len(self.filtered_results)}개 항목 복사됨")
        messagebox.showinfo("복사 완료", f"{len(self.filtered_results)}개 항목이 클립보드에 복사되었습니다.")

    def open_paper_url(self, event):
        self.open_selected_url()

    def open_selected_url(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("알림", "논문을 선택해주세요.")
            return
        for item in selection[:3]:
            tags = self.tree.item(item)["tags"]
            if tags:
                paper = next(
                    (p for p in self.all_results if p.get("Paper ID") == tags[0]), None
                )
                if paper and paper.get("URL") and paper.get("URL") != "N/A":
                    webbrowser.open(paper["URL"])

    def show_paper_details(self):
        selection = self.tree.selection()
        if not selection:
            return
        tags = self.tree.item(selection[0])["tags"]
        if not tags:
            return
        paper = next((p for p in self.all_results if p.get("Paper ID") == tags[0]), None)
        if not paper:
            return
        detail_window = tk.Toplevel(self.root)
        detail_window.title("논문 상세 정보")
        detail_window.geometry("820x640")
        text = scrolledtext.ScrolledText(
            detail_window, wrap=tk.WORD, padx=12, pady=10, font=("SF Pro Text", 13)
        )
        text.pack(fill=tk.BOTH, expand=True)
        details = (
            f"제목: {paper.get('Title', 'N/A')}\n\n"
            f"저자: {paper.get('Authors', 'N/A')}\n\n"
            f"연도: {paper.get('Year', 'N/A')}\n\n"
            f"학회/저널: {paper.get('Venue', 'N/A')}\n\n"
            f"인용수: {paper.get('Citation Count', 0)}\n\n"
            f"DOI: {paper.get('DOI', 'N/A')}\n\n"
            f"URL: {paper.get('URL', 'N/A')}\n\n"
            f"Chicago 인용:\n{paper.get('Chicago Citation', 'N/A')}\n\n"
            f"초록:\n{paper.get('Abstract', 'N/A')}"
        )
        text.insert("1.0", details)
        text.config(state="disabled")

    def export_to_excel(self):
        if not self.filtered_results:
            messagebox.showinfo("알림", "저장할 데이터가 없습니다.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"semantic_scholar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        )
        if not filename:
            return
        try:
            df = pd.DataFrame(self.filtered_results)
            with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Papers")
                ws = writer.sheets["Papers"]
                for col in ws.columns:
                    max_len = max(
                        (len(str(c.value)) for c in col if c.value is not None), default=0
                    )
                    ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
            self.log(f"Excel 저장: {filename}")
            messagebox.showinfo("저장 완료", f"{len(self.filtered_results)}개 논문이 저장되었습니다.")
            if messagebox.askyesno("파일 열기", "저장된 파일을 여시겠습니까?"):
                subprocess.call(["open", filename])
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패:\n{e}")

    def export_to_csv(self):
        if not self.filtered_results:
            messagebox.showinfo("알림", "저장할 데이터가 없습니다.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"semantic_scholar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not filename:
            return
        try:
            df = pd.DataFrame(self.filtered_results)
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            self.log(f"CSV 저장: {filename}")
            messagebox.showinfo("저장 완료", f"{len(self.filtered_results)}개 논문이 저장되었습니다.")
            if messagebox.askyesno("파일 열기", "저장된 파일을 여시겠습니까?"):
                subprocess.call(["open", filename])
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패:\n{e}")

    # ── Search ──────────────────────────────────────────────────────────────

    def start_search(self):
        if not self.keywords:
            messagebox.showerror("오류", "최소 1개 이상의 키워드를 입력해주세요.")
            return
        if self.mode.get() == "append" and not self.existing_file.get():
            messagebox.showerror("오류", "기존 파일을 선택해주세요.")
            return

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.is_searching = True

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

        self.save_settings(silent=True)

        threading.Thread(target=self.perform_search, daemon=True).start()

    def stop_search(self):
        self.is_searching = False
        self.update_status("중지됨", "orange")
        self.log("검색 중지")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def perform_search(self):
        try:
            self.log("=" * 50)
            self.log("검색 시작")
            self.log("=" * 50)

            if self.mode.get() == "append":
                self.update_status("기존 파일 불러오는 중...", "blue")
                self.existing_papers = self.load_existing_excel(self.existing_file.get())

            all_papers_processed = []
            total_keywords = len(self.keywords)

            for i, keyword in enumerate(self.keywords):
                if not self.is_searching:
                    break

                self.log(f"🔍 키워드 {i + 1}/{total_keywords}: '{keyword}'")
                self.update_status(f"검색 중... ({i + 1}/{total_keywords}) — {keyword}", "blue")
                self.update_progress(i / total_keywords * 100)

                papers_raw = self.search_with_pagination(keyword, self.max_results.get())

                if papers_raw and self.is_searching:
                    papers_processed = self.process_papers(papers_raw, keyword)
                    all_papers_processed.extend(papers_processed)
                    self.log(f"✅ {len(papers_processed)}개 수집")

                    # 실시간 미리보기: 현재까지 수집된 결과 즉시 표시
                    base = self.existing_papers if self.mode.get() == "append" else []
                    unique_so_far, _ = self.remove_duplicates_by_doi(
                        base + all_papers_processed, silent=True
                    )
                    self.all_results = unique_so_far
                    self.filtered_results = unique_so_far
                    self.root.after(0, lambda p=unique_so_far: self._refresh_table_from_thread(p))
                    if i == 0:
                        self.root.after(0, lambda: self.notebook.select(self.results_tab))

            if not self.is_searching:
                return

            self.log(f"새로 수집: {len(all_papers_processed)}개")

            if self.mode.get() == "append" and self.existing_papers:
                all_papers_combined = self.existing_papers + all_papers_processed
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
            self.update_status(f"✅ 완료! {len(unique_papers)}개 논문", "green")
            self.log(f"최종: {len(unique_papers)}개")

            self.notebook.select(self.results_tab)
            self.populate_results_table(unique_papers)
            self.send_macos_notification("검색 완료", f"{len(unique_papers)}개 논문")

            dup_msg = ""
            if keyword_duplicates:
                dup_lines = [f"• {kw}: {cnt}개" for kw, cnt in keyword_duplicates.items()]
                dup_msg = "\n\n[중복 제거]\n" + "\n".join(dup_lines)

            messagebox.showinfo(
                "완료",
                f"검색 완료!\n\n논문: {len(unique_papers)}개{dup_msg}\n\n결과 탭에서 확인하세요.",
            )

        except Exception as e:
            self.log(f"오류: {e}")
            self.update_status("오류 발생", "red")
            messagebox.showerror("오류", f"검색 중 오류:\n{e}")
        finally:
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.is_searching = False

    def _refresh_table_from_thread(self, papers):
        """스레드에서 안전하게 테이블 갱신 (root.after 로 호출)"""
        self.populate_results_table(papers)

    # ── API ──────────────────────────────────────────────────────────────────

    def search_semantic_scholar_single(self, keyword, limit=100, offset=0, max_retries=10):
        params = {
            "query": keyword,
            "limit": min(limit, 100),
            "offset": offset,
            "fields": "title,authors,year,abstract,url,venue,citationCount,publicationDate,paperId,externalIds",
        }
        headers = {"User-Agent": "Mozilla/5.0 (Academic Research Tool)"}
        api_key = self.api_key.get().strip()
        if api_key:
            headers["x-api-key"] = api_key

        for attempt in range(max_retries):
            if not self.is_searching:
                return None
            try:
                response = requests.get(
                    API_URL, params=params, headers=headers, timeout=300
                )
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self.log(f"⚠️ Rate Limit — {retry_after}초 대기...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    return None
                response.raise_for_status()
                results = response.json()
                if "data" in results:
                    return results
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
        return None

    def search_with_pagination(self, keyword, max_results=1000):
        all_papers = []
        batch_size = 100
        offset = 0

        first_result = self.search_semantic_scholar_single(keyword, limit=batch_size, offset=0)
        if not first_result or not self.is_searching:
            return []

        total_available = first_result.get("total", 0)
        papers = first_result.get("data", [])
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
            result = self.search_semantic_scholar_single(
                keyword, limit=min(batch_size, target - len(all_papers)), offset=offset
            )
            if not result or not self.is_searching:
                break
            papers = result.get("data", [])
            if not papers:
                break
            all_papers.extend(papers)
            self.log(f"  배치 {batch_num}: {len(papers)}개 (누적 {len(all_papers)}개)")
            batch_num += 1

        return all_papers

    def format_chicago_citation(self, paper_data):
        authors_list = paper_data.get("authors", [])
        if not authors_list:
            authors_str = "Unknown Author"
        elif len(authors_list) == 1:
            authors_str = authors_list[0].get("name", "Unknown")
        elif len(authors_list) == 2:
            authors_str = (
                f"{authors_list[0].get('name', 'Unknown')} and "
                f"{authors_list[1].get('name', 'Unknown')}"
            )
        else:
            authors_str = f"{authors_list[0].get('name', 'Unknown')} et al."

        year = paper_data.get("year", "n.d.")
        title = paper_data.get("title", "No title")
        venue = paper_data.get("venue", "")
        citation_count = paper_data.get("citationCount", 0)

        if venue:
            return f'{authors_str}. {year}. "{title}." {venue}. (Cited by: {citation_count})'
        return f'{authors_str}. {year}. "{title}." (Cited by: {citation_count})'

    def process_papers(self, papers_data, keyword_label=""):
        processed_list = []
        for paper in papers_data:
            authors_list = paper.get("authors", [])
            authors = (
                ", ".join(a.get("name", "Unknown") for a in authors_list)
                if authors_list
                else "No authors listed"
            )
            abstract = paper.get("abstract") or "No abstract available"
            if len(abstract) > 32767:
                abstract = abstract[:32760] + "..."
            doi = (paper.get("externalIds") or {}).get("DOI", "N/A")

            processed_list.append(
                {
                    "Keyword": keyword_label,
                    "Paper ID": paper.get("paperId", "N/A"),
                    "DOI": doi,
                    "Title": paper.get("title", "No title"),
                    "Authors": authors,
                    "Year": paper.get("year", "N/A"),
                    "Publication Date": paper.get("publicationDate", "N/A"),
                    "Venue": paper.get("venue", "N/A"),
                    "Citation Count": paper.get("citationCount", 0),
                    "Abstract": abstract,
                    "URL": paper.get("url", "N/A"),
                    "Chicago Citation": self.format_chicago_citation(paper),
                }
            )
        return processed_list

    def load_existing_excel(self, filepath):
        if not os.path.exists(filepath):
            return []
        try:
            df = pd.read_excel(filepath, sheet_name="Papers")
            papers = df.to_dict("records")
            self.log(f"기존 파일: {len(papers)}개")
            return papers
        except Exception:
            return []

    def remove_duplicates_by_doi(self, all_papers_list, silent=False):
        papers_with_doi = {}
        papers_without_doi = {}
        keyword_duplicates = {}

        for paper in all_papers_list:
            doi = paper.get("DOI", "N/A")
            paper_id = paper.get("Paper ID", "N/A")
            keyword = paper.get("Keyword", "Unknown")
            is_duplicate = False

            if doi != "N/A":
                if doi not in papers_with_doi:
                    papers_with_doi[doi] = paper
                else:
                    is_duplicate = True
            else:
                if paper_id != "N/A" and paper_id not in papers_without_doi:
                    papers_without_doi[paper_id] = paper
                else:
                    is_duplicate = True

            if is_duplicate:
                keyword_duplicates[keyword] = keyword_duplicates.get(keyword, 0) + 1

        unique_papers = list(papers_with_doi.values()) + list(papers_without_doi.values())
        removed = len(all_papers_list) - len(unique_papers)

        if not silent and removed > 0:
            self.log(f"중복 제거: {removed}개")

        return unique_papers, keyword_duplicates


def main():
    root = tk.Tk()
    app = SemanticScholarGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
