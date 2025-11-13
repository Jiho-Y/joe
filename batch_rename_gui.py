#!/usr/bin/env python3
"""
파일 이름 일괄 변경 GUI 프로그램
맥 환경에서 사용 가능
"""

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
import re
from datetime import datetime


class BatchRenameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("파일 이름 일괄 변경")
        self.root.geometry("1200x800")

        self.selected_folder = None
        self.files_list = []
        self.all_files = []  # 필터링 전 전체 파일 목록
        self.undo_history = []  # 실행 취소 히스토리
        self.recent_folders = []  # 최근 폴더 목록
        self.config_file = os.path.expanduser("~/.batch_rename_config.json")
        self.manual_renames = {}  # 수동으로 변경된 파일 이름 저장

        # 다크모드 설정
        self.dark_mode = tk.BooleanVar(value=False)

        # 설정 로드
        self.load_config()

        # 테마 초기화
        self.setup_themes()

        # 위젯 생성
        self.create_widgets()

        # 초기 테마 적용
        self.apply_theme()

        # 실시간 미리보기 설정
        self.setup_realtime_preview()

    def setup_themes(self):
        """다크/라이트 모드 테마 설정"""
        self.themes = {
            'light': {
                'bg': '#f0f0f0',
                'fg': '#000000',
                'select_bg': '#0078d7',
                'select_fg': '#ffffff',
                'tree_bg': '#ffffff',
                'tree_fg': '#000000',
                'highlight': '#ffffcc',
                'button_bg': '#e1e1e1',
                'entry_bg': '#ffffff',
                'entry_fg': '#000000',
                'frame_bg': '#f0f0f0',
            },
            'dark': {
                'bg': '#2b2b2b',
                'fg': '#e0e0e0',
                'select_bg': '#0078d7',
                'select_fg': '#ffffff',
                'tree_bg': '#1e1e1e',
                'tree_fg': '#e0e0e0',
                'highlight': '#4a4a00',
                'button_bg': '#3c3c3c',
                'entry_bg': '#2d2d2d',
                'entry_fg': '#e0e0e0',
                'frame_bg': '#2b2b2b',
            }
        }

    def apply_theme(self):
        """현재 테마 적용"""
        theme = 'dark' if self.dark_mode.get() else 'light'
        colors = self.themes[theme]

        # 루트 윈도우 배경색
        self.root.configure(bg=colors['bg'])

        # 스타일 설정
        style = ttk.Style()

        # 프레임 스타일
        style.configure('TFrame', background=colors['bg'])
        style.configure('TLabelframe', background=colors['bg'], foreground=colors['fg'])
        style.configure('TLabelframe.Label', background=colors['bg'], foreground=colors['fg'])

        # 레이블 스타일
        style.configure('TLabel', background=colors['bg'], foreground=colors['fg'])

        # 버튼 스타일
        style.configure('TButton', background=colors['button_bg'], foreground=colors['fg'])
        style.map('TButton', background=[('active', colors['select_bg'])])

        # Entry 스타일
        style.configure('TEntry', fieldbackground=colors['entry_bg'], foreground=colors['entry_fg'])
        style.map('TEntry',
                 fieldbackground=[('readonly', colors['entry_bg'])],
                 foreground=[('readonly', colors['entry_fg'])])

        # Combobox 스타일
        style.configure('TCombobox',
                       fieldbackground=colors['entry_bg'],
                       background=colors['entry_bg'],
                       foreground=colors['entry_fg'])
        style.map('TCombobox',
                 fieldbackground=[('readonly', colors['entry_bg'])],
                 foreground=[('readonly', colors['entry_fg'])],
                 selectbackground=[('readonly', colors['select_bg'])],
                 selectforeground=[('readonly', colors['select_fg'])])

        # Spinbox 스타일
        style.configure('TSpinbox',
                       fieldbackground=colors['entry_bg'],
                       background=colors['entry_bg'],
                       foreground=colors['entry_fg'])
        style.map('TSpinbox',
                 fieldbackground=[('readonly', colors['entry_bg'])],
                 foreground=[('readonly', colors['entry_fg'])])

        # 체크버튼 스타일
        style.configure('TCheckbutton', background=colors['bg'], foreground=colors['fg'])

        # 라디오버튼 스타일
        style.configure('TRadiobutton', background=colors['bg'], foreground=colors['fg'])

        # Treeview 스타일
        style.configure('Treeview',
                       background=colors['tree_bg'],
                       foreground=colors['tree_fg'],
                       fieldbackground=colors['tree_bg'])
        style.map('Treeview',
                 background=[('selected', colors['select_bg'])],
                 foreground=[('selected', colors['select_fg'])])

        # Treeview 헤더
        style.configure('Treeview.Heading',
                       background=colors['button_bg'],
                       foreground=colors['fg'])
        style.map('Treeview.Heading',
                 background=[('active', colors['select_bg'])])

        # 변경된 항목 하이라이트
        if hasattr(self, 'tree'):
            self.tree.tag_configure('changed', background=colors['highlight'])
            self.tree.tag_configure('manual', background=colors['select_bg'], foreground=colors['select_fg'])

        # Notebook 스타일
        style.configure('TNotebook', background=colors['bg'])
        style.configure('TNotebook.Tab', background=colors['button_bg'], foreground=colors['fg'])
        style.map('TNotebook.Tab',
                 background=[('selected', colors['select_bg'])],
                 foreground=[('selected', colors['select_fg'])])

    def toggle_theme(self):
        """테마 토글"""
        self.apply_theme()
        self.save_config()

    def load_config(self):
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.recent_folders = config.get('recent_folders', [])
                    self.dark_mode.set(config.get('dark_mode', False))
        except Exception as e:
            print(f"설정 로드 오류: {e}")

    def save_config(self):
        """설정 파일 저장"""
        try:
            config = {
                'recent_folders': self.recent_folders[:10],  # 최근 10개만 저장
                'dark_mode': self.dark_mode.get()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"설정 저장 오류: {e}")

    def add_to_recent_folders(self, folder):
        """최근 폴더 목록에 추가"""
        if folder in self.recent_folders:
            self.recent_folders.remove(folder)
        self.recent_folders.insert(0, folder)
        self.recent_folders = self.recent_folders[:10]
        self.update_recent_menu()
        self.save_config()

    def update_recent_menu(self):
        """최근 폴더 메뉴 업데이트"""
        self.recent_menu.delete(0, tk.END)
        if not self.recent_folders:
            self.recent_menu.add_command(label="(비어있음)", state='disabled')
        else:
            for folder in self.recent_folders:
                self.recent_menu.add_command(
                    label=folder,
                    command=lambda f=folder: self.open_recent_folder(f)
                )

    def open_recent_folder(self, folder):
        """최근 폴더 열기"""
        if os.path.exists(folder):
            self.selected_folder = folder
            self.folder_label.config(text=folder)
            self.load_files()
        else:
            messagebox.showerror("오류", f"폴더를 찾을 수 없습니다:\n{folder}")
            self.recent_folders.remove(folder)
            self.update_recent_menu()
            self.save_config()

    def create_widgets(self):
        # 메뉴바
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 파일 메뉴
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="폴더 선택", command=self.select_folder)

        # 최근 폴더 메뉴
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="최근 폴더", menu=self.recent_menu)
        self.update_recent_menu()

        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.root.quit)

        # 편집 메뉴
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="편집", menu=edit_menu)
        edit_menu.add_command(label="실행 취소 (Undo)", command=self.undo_rename, accelerator="Cmd+Z")
        edit_menu.add_separator()
        edit_menu.add_command(label="모든 수동 변경 취소", command=self.clear_manual_renames)

        # 보기 메뉴
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="보기", menu=view_menu)
        view_menu.add_checkbutton(label="다크 모드", variable=self.dark_mode, command=self.toggle_theme)

        # 키보드 단축키
        self.root.bind('<Command-z>', lambda e: self.undo_rename())

        # 상단 프레임: 폴더 선택
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Label(top_frame, text="폴더:").grid(row=0, column=0, padx=5)

        self.folder_label = ttk.Label(top_frame, text="폴더를 선택하세요",
                                     relief=tk.SUNKEN, width=60)
        self.folder_label.grid(row=0, column=1, padx=5)

        ttk.Button(top_frame, text="폴더 선택",
                  command=self.select_folder).grid(row=0, column=2, padx=5)

        # 필터 프레임
        filter_frame = ttk.Frame(self.root, padding="10")
        filter_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Label(filter_frame, text="파일 필터:").grid(row=0, column=0, padx=5)

        self.filter_var = tk.StringVar(value="모든 파일")
        self.filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                        values=["모든 파일"], state="readonly", width=20)
        self.filter_combo.grid(row=0, column=1, padx=5)
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filter())

        ttk.Button(filter_frame, text="새로고침",
                  command=self.refresh_files).grid(row=0, column=2, padx=5)

        ttk.Label(filter_frame, text="💡 팁: 파일명을 더블클릭하여 수동으로 편집 가능",
                 font=('', 9, 'italic')).grid(row=0, column=3, padx=20)

        # 중간 프레임: 변경 옵션
        options_frame = ttk.LabelFrame(self.root, text="변경 옵션 (자동 미리보기)", padding="10")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E),
                          padx=10, pady=10)

        # 옵션 탭
        self.tab_control = ttk.Notebook(options_frame)

        # 탭 1: 접두사/접미사
        tab1 = ttk.Frame(self.tab_control)
        self.tab_control.add(tab1, text="접두사/접미사")

        ttk.Label(tab1, text="접두사:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.prefix_entry = ttk.Entry(tab1, width=30)
        self.prefix_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(tab1, text="접미사:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.suffix_entry = ttk.Entry(tab1, width=30)
        self.suffix_entry.grid(row=1, column=1, padx=5, pady=5)

        # 탭 2: 찾기/바꾸기
        tab2 = ttk.Frame(self.tab_control)
        self.tab_control.add(tab2, text="찾기/바꾸기")

        ttk.Label(tab2, text="찾을 텍스트:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.find_entry = ttk.Entry(tab2, width=30)
        self.find_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(tab2, text="바꿀 텍스트:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.replace_entry = ttk.Entry(tab2, width=30)
        self.replace_entry.grid(row=1, column=1, padx=5, pady=5)

        self.case_sensitive = tk.BooleanVar()
        ttk.Checkbutton(tab2, text="대소문자 구분",
                       variable=self.case_sensitive).grid(row=2, column=1,
                                                         padx=5, pady=5, sticky=tk.W)

        self.use_regex = tk.BooleanVar()
        ttk.Checkbutton(tab2, text="정규표현식 사용",
                       variable=self.use_regex).grid(row=3, column=1,
                                                     padx=5, pady=5, sticky=tk.W)

        # 탭 3: 순차 번호
        tab3 = ttk.Frame(self.tab_control)
        self.tab_control.add(tab3, text="순차 번호")

        self.add_numbering = tk.BooleanVar()
        ttk.Checkbutton(tab3, text="순차 번호 추가",
                       variable=self.add_numbering,
                       command=self.toggle_numbering).grid(row=0, column=0,
                                                           columnspan=2, padx=5,
                                                           pady=5, sticky=tk.W)

        ttk.Label(tab3, text="시작 번호:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.start_num = ttk.Spinbox(tab3, from_=0, to=9999, width=10)
        self.start_num.set(1)
        self.start_num.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(tab3, text="자릿수:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.padding = ttk.Spinbox(tab3, from_=1, to=10, width=10)
        self.padding.set(3)
        self.padding.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(tab3, text="위치:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.number_position = ttk.Combobox(tab3, values=["앞", "뒤"],
                                           state="readonly", width=10)
        self.number_position.set("뒤")
        self.number_position.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        # 탭 4: 대소문자 변환
        tab4 = ttk.Frame(self.tab_control)
        self.tab_control.add(tab4, text="대소문자")

        self.case_change = tk.StringVar(value="변경 안 함")
        ttk.Radiobutton(tab4, text="변경 안 함", variable=self.case_change,
                       value="변경 안 함").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(tab4, text="모두 대문자", variable=self.case_change,
                       value="대문자").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(tab4, text="모두 소문자", variable=self.case_change,
                       value="소문자").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(tab4, text="첫 글자만 대문자", variable=self.case_change,
                       value="타이틀").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)

        # 탭 5: 특수문자 처리
        tab5 = ttk.Frame(self.tab_control)
        self.tab_control.add(tab5, text="특수문자")

        self.remove_spaces = tk.BooleanVar()
        ttk.Checkbutton(tab5, text="공백 제거",
                       variable=self.remove_spaces).grid(row=0, column=0,
                                                         padx=5, pady=5, sticky=tk.W)

        self.replace_spaces = tk.BooleanVar()
        ttk.Checkbutton(tab5, text="공백을 '_'로 변경",
                       variable=self.replace_spaces).grid(row=1, column=0,
                                                          padx=5, pady=5, sticky=tk.W)

        self.remove_special = tk.BooleanVar()
        ttk.Checkbutton(tab5, text="특수문자 제거 (알파벳, 숫자, _, -, . 만 유지)",
                       variable=self.remove_special).grid(row=2, column=0,
                                                          padx=5, pady=5, sticky=tk.W)

        self.tab_control.pack(expand=1, fill="both")

        # 미리보기 버튼
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=3, column=0, columnspan=2)

        ttk.Button(button_frame, text="미리보기 새로고침",
                  command=self.preview_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="실행",
                  command=self.execute_rename).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="초기화",
                  command=self.reset_options).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="실행 취소",
                  command=self.undo_rename).pack(side=tk.LEFT, padx=5)

        # 하단 프레임: 파일 목록
        list_frame = ttk.Frame(self.root, padding="10")
        list_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Treeview로 변경 전/후 표시
        columns = ("original", "new")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        self.tree.heading("original", text="현재 이름")
        self.tree.heading("new", text="변경될 이름 (더블클릭으로 수동 편집)")

        self.tree.column("original", width=550)
        self.tree.column("new", width=550)

        # 더블클릭 이벤트 바인딩
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)

        # 스크롤바
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 상태바
        self.status_label = ttk.Label(self.root, text="준비", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E))

    def setup_realtime_preview(self):
        """실시간 미리보기 설정"""
        # Entry 위젯에 이벤트 바인딩
        self.prefix_entry.bind('<KeyRelease>', lambda e: self.auto_preview())
        self.suffix_entry.bind('<KeyRelease>', lambda e: self.auto_preview())
        self.find_entry.bind('<KeyRelease>', lambda e: self.auto_preview())
        self.replace_entry.bind('<KeyRelease>', lambda e: self.auto_preview())

        # BooleanVar에 trace 추가
        self.case_sensitive.trace('w', lambda *args: self.auto_preview())
        self.use_regex.trace('w', lambda *args: self.auto_preview())
        self.add_numbering.trace('w', lambda *args: self.auto_preview())
        self.remove_spaces.trace('w', lambda *args: self.auto_preview())
        self.replace_spaces.trace('w', lambda *args: self.auto_preview())
        self.remove_special.trace('w', lambda *args: self.auto_preview())

        # StringVar에 trace 추가
        self.case_change.trace('w', lambda *args: self.auto_preview())

        # Spinbox 이벤트
        self.start_num.bind('<KeyRelease>', lambda e: self.auto_preview())
        self.start_num.bind('<<Increment>>', lambda e: self.auto_preview())
        self.start_num.bind('<<Decrement>>', lambda e: self.auto_preview())
        self.padding.bind('<KeyRelease>', lambda e: self.auto_preview())
        self.padding.bind('<<Increment>>', lambda e: self.auto_preview())
        self.padding.bind('<<Decrement>>', lambda e: self.auto_preview())

        # Combobox 이벤트
        self.number_position.bind('<<ComboboxSelected>>', lambda e: self.auto_preview())

    def auto_preview(self):
        """자동 미리보기 (실시간)"""
        if self.files_list:
            self.preview_changes()

    def on_tree_double_click(self, event):
        """트리 더블클릭 시 수동 편집"""
        region = self.tree.identify('region', event.x, event.y)
        if region != 'cell':
            return

        column = self.tree.identify_column(event.x)
        if column != '#2':  # 두 번째 컬럼 (변경될 이름)만 편집 가능
            return

        item = self.tree.identify_row(event.y)
        if not item:
            return

        # 현재 값 가져오기
        values = self.tree.item(item, 'values')
        if not values or len(values) < 2:
            return

        original_name = values[0]
        current_new_name = values[1]

        # 편집 다이얼로그
        new_name = simpledialog.askstring(
            "파일명 수동 편집",
            f"원본: {original_name}\n\n새 파일명을 입력하세요:",
            initialvalue=current_new_name,
            parent=self.root
        )

        if new_name and new_name != original_name:
            # 수동 변경 저장
            self.manual_renames[original_name] = new_name
            # 미리보기 업데이트
            self.preview_changes()

    def clear_manual_renames(self):
        """모든 수동 변경 취소"""
        if self.manual_renames:
            self.manual_renames.clear()
            self.preview_changes()
            messagebox.showinfo("완료", "모든 수동 변경이 취소되었습니다.")

    def toggle_numbering(self):
        """순차 번호 옵션 활성화/비활성화"""
        enabled = self.add_numbering.get()
        state = 'normal' if enabled else 'disabled'
        self.start_num.config(state=state)
        self.padding.config(state=state)
        self.number_position.config(state='readonly' if enabled else 'disabled')

    def select_folder(self):
        """폴더 선택 다이얼로그"""
        folder = filedialog.askdirectory(title="파일 이름을 변경할 폴더 선택")
        if folder:
            self.selected_folder = folder
            self.folder_label.config(text=folder)
            self.add_to_recent_folders(folder)
            self.manual_renames.clear()  # 새 폴더 선택 시 수동 변경 초기화
            self.load_files()

    def load_files(self):
        """선택된 폴더의 파일 목록 로드"""
        if not self.selected_folder:
            return

        self.all_files = []
        try:
            for entry in os.listdir(self.selected_folder):
                full_path = os.path.join(self.selected_folder, entry)
                if os.path.isfile(full_path):
                    self.all_files.append(entry)

            self.all_files.sort()

            # 확장자 목록 추출
            extensions = set()
            for filename in self.all_files:
                ext = os.path.splitext(filename)[1]
                if ext:
                    extensions.add(ext)

            # 필터 콤보박스 업데이트
            filter_values = ["모든 파일"] + sorted(list(extensions))
            self.filter_combo['values'] = filter_values
            self.filter_var.set("모든 파일")

            # 파일 목록 적용
            self.apply_filter()

        except Exception as e:
            messagebox.showerror("오류", f"파일 목록을 불러올 수 없습니다:\n{str(e)}")

    def apply_filter(self):
        """파일 필터 적용"""
        filter_value = self.filter_var.get()

        if filter_value == "모든 파일":
            self.files_list = self.all_files.copy()
        else:
            self.files_list = [f for f in self.all_files
                             if os.path.splitext(f)[1] == filter_value]

        self.files_list.sort()
        self.auto_preview()  # 필터 변경 시 자동 미리보기
        self.status_label.config(text=f"{len(self.files_list)}개의 파일 (전체: {len(self.all_files)}개)")

    def refresh_files(self):
        """파일 목록 새로고침"""
        if self.selected_folder:
            self.load_files()

    def update_tree_view(self, new_names=None):
        """Treeview 업데이트"""
        # 기존 항목 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 새 항목 추가
        for i, original in enumerate(self.files_list):
            new_name = new_names[i] if new_names else original
            # 변경사항이 있으면 태그 추가
            if original in self.manual_renames:
                tag = 'manual'  # 수동 변경
            elif new_name != original:
                tag = 'changed'  # 자동 변경
            else:
                tag = ''
            self.tree.insert("", tk.END, values=(original, new_name), tags=(tag,))

        # 변경된 항목 하이라이트 (테마에 맞게)
        self.apply_theme()

    def generate_new_name(self, original_name, index):
        """새 파일 이름 생성"""
        # 수동으로 변경된 경우 우선
        if original_name in self.manual_renames:
            return self.manual_renames[original_name]

        name, ext = os.path.splitext(original_name)
        new_name = name

        # 찾기/바꾸기
        find_text = self.find_entry.get()
        replace_text = self.replace_entry.get()
        if find_text:
            if self.use_regex.get():
                # 정규표현식 사용
                try:
                    flags = 0 if self.case_sensitive.get() else re.IGNORECASE
                    new_name = re.sub(find_text, replace_text, new_name, flags=flags)
                except re.error as e:
                    # 정규표현식 오류 시 일반 텍스트로 처리
                    if self.case_sensitive.get():
                        new_name = new_name.replace(find_text, replace_text)
                    else:
                        pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                        new_name = pattern.sub(replace_text, new_name)
            else:
                # 일반 텍스트 찾기/바꾸기
                if self.case_sensitive.get():
                    new_name = new_name.replace(find_text, replace_text)
                else:
                    pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                    new_name = pattern.sub(replace_text, new_name)

        # 대소문자 변환
        case_option = self.case_change.get()
        if case_option == "대문자":
            new_name = new_name.upper()
        elif case_option == "소문자":
            new_name = new_name.lower()
        elif case_option == "타이틀":
            new_name = new_name.title()

        # 특수문자 처리
        if self.remove_spaces.get():
            new_name = new_name.replace(" ", "")
        elif self.replace_spaces.get():
            new_name = new_name.replace(" ", "_")

        if self.remove_special.get():
            # 알파벳, 숫자, 언더스코어, 하이픈만 유지
            new_name = re.sub(r'[^\w\-]', '', new_name)

        # 접두사
        prefix = self.prefix_entry.get()
        if prefix:
            new_name = prefix + new_name

        # 접미사
        suffix = self.suffix_entry.get()
        if suffix:
            new_name = new_name + suffix

        # 순차 번호
        if self.add_numbering.get():
            try:
                start = int(self.start_num.get())
                padding = int(self.padding.get())
                number = str(start + index).zfill(padding)

                if self.number_position.get() == "앞":
                    new_name = number + "_" + new_name
                else:
                    new_name = new_name + "_" + number
            except ValueError:
                pass  # 숫자 변환 오류 시 무시

        return new_name + ext

    def preview_changes(self):
        """변경 사항 미리보기"""
        if not self.files_list:
            return

        new_names = []
        for i, original in enumerate(self.files_list):
            new_name = self.generate_new_name(original, i)
            new_names.append(new_name)

        self.update_tree_view(new_names)

        # 변경된 파일 개수 계산
        changed_count = sum(1 for i, orig in enumerate(self.files_list)
                          if orig != new_names[i])
        manual_count = len(self.manual_renames)

        status_text = f"{changed_count}개의 파일이 변경될 예정"
        if manual_count > 0:
            status_text += f" (수동 편집: {manual_count}개)"
        self.status_label.config(text=status_text)

    def execute_rename(self):
        """실제 파일 이름 변경 실행"""
        if not self.files_list:
            messagebox.showwarning("경고", "먼저 폴더를 선택하세요.")
            return

        # 확인 다이얼로그
        new_names = []
        for i, original in enumerate(self.files_list):
            new_name = self.generate_new_name(original, i)
            new_names.append(new_name)

        changed_count = sum(1 for i, orig in enumerate(self.files_list)
                          if orig != new_names[i])

        if changed_count == 0:
            messagebox.showinfo("정보", "변경할 파일이 없습니다.")
            return

        manual_count = len(self.manual_renames)
        msg = f"{changed_count}개의 파일 이름을 변경하시겠습니까?"
        if manual_count > 0:
            msg += f"\n(수동 편집: {manual_count}개 포함)"
        msg += "\n\n실행 취소 기능으로 되돌릴 수 있습니다."

        result = messagebox.askyesno("확인", msg)

        if not result:
            return

        # 파일 이름 변경 실행
        success_count = 0
        error_count = 0
        errors = []
        rename_log = []  # 실행 취소를 위한 로그

        for i, original in enumerate(self.files_list):
            new_name = new_names[i]
            if original == new_name:
                continue

            old_path = os.path.join(self.selected_folder, original)
            new_path = os.path.join(self.selected_folder, new_name)

            try:
                # 이미 같은 이름의 파일이 있는지 확인
                if os.path.exists(new_path):
                    raise FileExistsError(f"'{new_name}' 파일이 이미 존재합니다.")

                os.rename(old_path, new_path)
                success_count += 1
                rename_log.append((new_name, original))  # 새이름, 원래이름
            except Exception as e:
                error_count += 1
                errors.append(f"{original}: {str(e)}")

        # 실행 취소 히스토리에 추가
        if rename_log:
            self.undo_history.append({
                'folder': self.selected_folder,
                'renames': rename_log,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        # 수동 변경 내역 초기화
        self.manual_renames.clear()

        # 결과 메시지
        message = f"성공: {success_count}개\n실패: {error_count}개"
        if errors:
            message += "\n\n오류 목록:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                message += f"\n... 외 {len(errors) - 10}개"

        if error_count > 0:
            messagebox.showwarning("완료", message)
        else:
            messagebox.showinfo("완료", message)

        # 파일 목록 다시 로드
        self.load_files()

    def undo_rename(self):
        """마지막 이름 변경 실행 취소"""
        if not self.undo_history:
            messagebox.showinfo("정보", "실행 취소할 작업이 없습니다.")
            return

        last_action = self.undo_history[-1]

        result = messagebox.askyesno("실행 취소",
                                    f"다음 작업을 취소하시겠습니까?\n"
                                    f"시간: {last_action['timestamp']}\n"
                                    f"폴더: {last_action['folder']}\n"
                                    f"파일 수: {len(last_action['renames'])}개")

        if not result:
            return

        success_count = 0
        error_count = 0
        errors = []

        for new_name, original_name in last_action['renames']:
            new_path = os.path.join(last_action['folder'], new_name)
            old_path = os.path.join(last_action['folder'], original_name)

            try:
                if os.path.exists(new_path):
                    os.rename(new_path, old_path)
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"{new_name}: 파일을 찾을 수 없습니다.")
            except Exception as e:
                error_count += 1
                errors.append(f"{new_name}: {str(e)}")

        # 히스토리에서 제거
        self.undo_history.pop()

        # 결과 메시지
        message = f"실행 취소 완료\n성공: {success_count}개\n실패: {error_count}개"
        if errors:
            message += "\n\n오류 목록:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                message += f"\n... 외 {len(errors) - 10}개"

        messagebox.showinfo("실행 취소", message)

        # 파일 목록 다시 로드
        if self.selected_folder == last_action['folder']:
            self.load_files()

    def reset_options(self):
        """옵션 초기화"""
        self.prefix_entry.delete(0, tk.END)
        self.suffix_entry.delete(0, tk.END)
        self.find_entry.delete(0, tk.END)
        self.replace_entry.delete(0, tk.END)
        self.case_sensitive.set(False)
        self.use_regex.set(False)
        self.add_numbering.set(False)
        self.start_num.set(1)
        self.padding.set(3)
        self.number_position.set("뒤")
        self.case_change.set("변경 안 함")
        self.remove_spaces.set(False)
        self.replace_spaces.set(False)
        self.remove_special.set(False)
        self.manual_renames.clear()
        self.toggle_numbering()

        # 미리보기 초기화
        if self.files_list:
            self.update_tree_view()
            self.status_label.config(text=f"{len(self.files_list)}개의 파일")


def main():
    root = tk.Tk()
    app = BatchRenameGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
