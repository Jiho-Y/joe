#!/usr/bin/env python3
"""
파일 이름 일괄 변경 GUI 프로그램
맥 환경에서 사용 가능
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import re


class BatchRenameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("파일 이름 일괄 변경")
        self.root.geometry("1000x700")

        self.selected_folder = None
        self.files_list = []

        self.create_widgets()

    def create_widgets(self):
        # 상단 프레임: 폴더 선택
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Label(top_frame, text="폴더:").grid(row=0, column=0, padx=5)

        self.folder_label = ttk.Label(top_frame, text="폴더를 선택하세요",
                                     relief=tk.SUNKEN, width=60)
        self.folder_label.grid(row=0, column=1, padx=5)

        ttk.Button(top_frame, text="폴더 선택",
                  command=self.select_folder).grid(row=0, column=2, padx=5)

        # 중간 프레임: 변경 옵션
        options_frame = ttk.LabelFrame(self.root, text="변경 옵션", padding="10")
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E),
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

        self.tab_control.pack(expand=1, fill="both")

        # 미리보기 버튼
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=2, column=0, columnspan=2)

        ttk.Button(button_frame, text="미리보기",
                  command=self.preview_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="실행",
                  command=self.execute_rename,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="초기화",
                  command=self.reset_options).pack(side=tk.LEFT, padx=5)

        # 하단 프레임: 파일 목록
        list_frame = ttk.Frame(self.root, padding="10")
        list_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Treeview로 변경 전/후 표시
        columns = ("original", "new")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        self.tree.heading("original", text="현재 이름")
        self.tree.heading("new", text="변경될 이름")

        self.tree.column("original", width=450)
        self.tree.column("new", width=450)

        # 스크롤바
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 상태바
        self.status_label = ttk.Label(self.root, text="준비", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))

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
            self.load_files()

    def load_files(self):
        """선택된 폴더의 파일 목록 로드"""
        if not self.selected_folder:
            return

        self.files_list = []
        try:
            for entry in os.listdir(self.selected_folder):
                full_path = os.path.join(self.selected_folder, entry)
                if os.path.isfile(full_path):
                    self.files_list.append(entry)

            self.files_list.sort()
            self.update_tree_view()
            self.status_label.config(text=f"{len(self.files_list)}개의 파일 로드됨")

        except Exception as e:
            messagebox.showerror("오류", f"파일 목록을 불러올 수 없습니다:\n{str(e)}")

    def update_tree_view(self, new_names=None):
        """Treeview 업데이트"""
        # 기존 항목 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 새 항목 추가
        for i, original in enumerate(self.files_list):
            new_name = new_names[i] if new_names else original
            # 변경사항이 있으면 태그 추가
            tag = 'changed' if new_name != original else ''
            self.tree.insert("", tk.END, values=(original, new_name), tags=(tag,))

        # 변경된 항목 하이라이트
        self.tree.tag_configure('changed', background='#ffffcc')

    def generate_new_name(self, original_name, index):
        """새 파일 이름 생성"""
        name, ext = os.path.splitext(original_name)
        new_name = name

        # 찾기/바꾸기
        find_text = self.find_entry.get()
        replace_text = self.replace_entry.get()
        if find_text:
            if self.case_sensitive.get():
                new_name = new_name.replace(find_text, replace_text)
            else:
                # 대소문자 구분 없이 바꾸기
                pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                new_name = pattern.sub(replace_text, new_name)

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
            start = int(self.start_num.get())
            padding = int(self.padding.get())
            number = str(start + index).zfill(padding)

            if self.number_position.get() == "앞":
                new_name = number + "_" + new_name
            else:
                new_name = new_name + "_" + number

        return new_name + ext

    def preview_changes(self):
        """변경 사항 미리보기"""
        if not self.files_list:
            messagebox.showwarning("경고", "먼저 폴더를 선택하세요.")
            return

        new_names = []
        for i, original in enumerate(self.files_list):
            new_name = self.generate_new_name(original, i)
            new_names.append(new_name)

        self.update_tree_view(new_names)

        # 변경된 파일 개수 계산
        changed_count = sum(1 for i, orig in enumerate(self.files_list)
                          if orig != new_names[i])
        self.status_label.config(text=f"{changed_count}개의 파일이 변경될 예정입니다.")

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

        result = messagebox.askyesno("확인",
                                    f"{changed_count}개의 파일 이름을 변경하시겠습니까?\n"
                                    "이 작업은 되돌릴 수 없습니다.")

        if not result:
            return

        # 파일 이름 변경 실행
        success_count = 0
        error_count = 0
        errors = []

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
            except Exception as e:
                error_count += 1
                errors.append(f"{original}: {str(e)}")

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

    def reset_options(self):
        """옵션 초기화"""
        self.prefix_entry.delete(0, tk.END)
        self.suffix_entry.delete(0, tk.END)
        self.find_entry.delete(0, tk.END)
        self.replace_entry.delete(0, tk.END)
        self.case_sensitive.set(False)
        self.add_numbering.set(False)
        self.start_num.set(1)
        self.padding.set(3)
        self.number_position.set("뒤")
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
