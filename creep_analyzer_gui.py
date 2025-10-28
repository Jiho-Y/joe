#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multistep Creep Test Analyzer - GUI Version
크리프 시험 데이터 분석 도구 (그래픽 사용자 인터페이스)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
from creep_analyzer import CreepAnalyzer
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class CreepAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Multistep Creep Test Analyzer")
        self.root.geometry("1000x700")

        # 분석기 객체
        self.analyzer = None
        self.csv_path = None

        # 탭 생성
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # 각 탭 생성
        self.create_main_tab()
        self.create_settings_tab()
        self.create_results_tab()

    def create_main_tab(self):
        """메인 탭: 기본 입력"""
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="메인")

        # 제목
        title_label = ttk.Label(main_frame, text="Multistep Creep Test Analyzer",
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        subtitle_label = ttk.Label(main_frame, text="2차 크리프 속도 측정 및 응력지수 n 계산",
                                  font=("Arial", 10))
        subtitle_label.pack(pady=5)

        # 입력 프레임
        input_frame = ttk.LabelFrame(main_frame, text="입력 설정", padding=20)
        input_frame.pack(fill='x', padx=20, pady=10)

        # 1. 하중 조건
        ttk.Label(input_frame, text="하중 조건 (MPa):", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky='w', pady=5)
        ttk.Label(input_frame, text="쉼표로 구분 (예: 15, 25, 35, 45)",
                 font=("Arial", 9), foreground="gray").grid(row=0, column=1, sticky='w', padx=5)

        self.stress_entry = ttk.Entry(input_frame, width=50)
        self.stress_entry.grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)
        self.stress_entry.insert(0, "15, 25, 35, 45")

        # 2. CSV 파일
        ttk.Label(input_frame, text="CSV 파일:", font=("Arial", 10, "bold")).grid(
            row=2, column=0, sticky='w', pady=(10, 5))

        csv_frame = ttk.Frame(input_frame)
        csv_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=5)

        self.csv_entry = ttk.Entry(csv_frame, width=50)
        self.csv_entry.pack(side='left', fill='x', expand=True)

        browse_btn = ttk.Button(csv_frame, text="찾아보기", command=self.browse_csv)
        browse_btn.pack(side='left', padx=5)

        # 3. 초기 안정화 시간
        ttk.Label(input_frame, text="초기 안정화 시간 (시간):",
                 font=("Arial", 10, "bold")).grid(row=4, column=0, sticky='w', pady=(10, 5))
        ttk.Label(input_frame, text="첫 번째 하중 증가 전 안정화 기간",
                 font=("Arial", 9), foreground="gray").grid(row=4, column=1, sticky='w', padx=5)

        self.stabilization_entry = ttk.Entry(input_frame, width=20)
        self.stabilization_entry.grid(row=5, column=0, sticky='w', pady=5)
        self.stabilization_entry.insert(0, "48")

        # 4. 하중 간격
        ttk.Label(input_frame, text="하중 간격 (시간):",
                 font=("Arial", 10, "bold")).grid(row=6, column=0, sticky='w', pady=(10, 5))
        ttk.Label(input_frame, text="하중 증가 사이의 시간 간격",
                 font=("Arial", 9), foreground="gray").grid(row=6, column=1, sticky='w', padx=5)

        self.interval_entry = ttk.Entry(input_frame, width=20)
        self.interval_entry.grid(row=7, column=0, sticky='w', pady=5)
        self.interval_entry.insert(0, "24")

        # 분석 버튼
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)

        self.analyze_btn = ttk.Button(button_frame, text="분석 시작",
                                      command=self.run_analysis,
                                      style='Accent.TButton')
        self.analyze_btn.pack(side='left', padx=5, ipadx=20, ipady=10)

        # 진행 상황 표시
        self.progress_frame = ttk.LabelFrame(main_frame, text="진행 상황", padding=10)
        self.progress_frame.pack(fill='both', expand=True, padx=20, pady=10)

        self.progress_text = scrolledtext.ScrolledText(self.progress_frame,
                                                       height=10,
                                                       state='disabled',
                                                       font=("Courier", 9))
        self.progress_text.pack(fill='both', expand=True)

    def create_settings_tab(self):
        """설정 탭: 고급 파라미터"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="고급 설정")

        # 제목
        title_label = ttk.Label(settings_frame, text="하중 구간 감지 알고리즘 파라미터",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=20)

        # 설정 프레임
        config_frame = ttk.LabelFrame(settings_frame, text="알고리즘 민감도 설정", padding=20)
        config_frame.pack(fill='x', padx=40, pady=10)

        # 1. 탐색 윈도우 크기
        row = 0
        ttk.Label(config_frame, text="탐색 윈도우 크기 (시간):",
                 font=("Arial", 10, "bold")).grid(row=row, column=0, sticky='w', pady=10)

        self.window_entry = ttk.Entry(config_frame, width=15)
        self.window_entry.grid(row=row, column=1, sticky='w', padx=10)
        self.window_entry.insert(0, "0.5")

        ttk.Label(config_frame, text="예상 시점 ± 이 값 범위 내에서 탐색 (단위: 시간)",
                 font=("Arial", 9), foreground="gray").grid(row=row, column=2, sticky='w', padx=5)

        # 2. 최소 변형률 가속도
        row += 1
        ttk.Label(config_frame, text="최소 변형률 가속도:",
                 font=("Arial", 10, "bold")).grid(row=row, column=0, sticky='w', pady=10)

        self.acceleration_entry = ttk.Entry(config_frame, width=15)
        self.acceleration_entry.grid(row=row, column=1, sticky='w', padx=10)
        self.acceleration_entry.insert(0, "1e-7")

        ttk.Label(config_frame, text="하중 전환으로 인정할 최소 가속도 값 (단위: %/s²)",
                 font=("Arial", 9), foreground="gray").grid(row=row, column=2, sticky='w', padx=5)

        # 3. 2차 미분 사용 여부
        row += 1
        ttk.Label(config_frame, text="2차 미분 사용:",
                 font=("Arial", 10, "bold")).grid(row=row, column=0, sticky='w', pady=10)

        self.derivative_var = tk.BooleanVar(value=True)
        derivative_check = ttk.Checkbutton(config_frame, text="변형률 가속도(2차 미분) 사용",
                                          variable=self.derivative_var)
        derivative_check.grid(row=row, column=1, columnspan=2, sticky='w', padx=10)

        ttk.Label(config_frame, text="체크 해제 시 변형률 속도(1차 미분) 사용",
                 font=("Arial", 9), foreground="gray").grid(row=row+1, column=1, columnspan=2,
                                                            sticky='w', padx=10)

        # 설명
        info_frame = ttk.LabelFrame(settings_frame, text="파라미터 설명", padding=20)
        info_frame.pack(fill='both', expand=True, padx=40, pady=10)

        info_text = """
민감도 조정 가이드:

1. 탐색 윈도우 크기:
   - 작을수록 정밀하지만 하중 증가 시점을 놓칠 수 있음
   - 클수록 안전하지만 오감지 가능성 증가
   - 권장값: 0.5시간 (±30분, 총 1시간)

2. 최소 변형률 가속도:
   - 작을수록 민감하게 감지 (작은 변화도 감지)
   - 클수록 둔감하게 감지 (큰 변화만 감지)
   - 권장값: 1e-7 ~ 1e-6

3. 2차 미분 사용:
   - 체크: 가속도 기반 (더 정확, 권장)
   - 체크 해제: 속도 기반 (단순)

문제 해결:
- 구간이 너무 많이 감지되면: 최소 가속도 값을 높이거나 윈도우 크기를 줄이세요
- 구간이 감지되지 않으면: 최소 가속도 값을 낮추거나 윈도우 크기를 늘리세요
        """

        info_label = ttk.Label(info_frame, text=info_text, justify='left',
                              font=("Arial", 9), foreground="navy")
        info_label.pack(anchor='w')

        # 기본값으로 재설정 버튼
        reset_btn = ttk.Button(settings_frame, text="기본값으로 재설정",
                              command=self.reset_settings)
        reset_btn.pack(pady=10)

    def create_results_tab(self):
        """결과 탭: 분석 결과 표시"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="결과")

        # 상단 프레임 (요약 정보)
        summary_frame = ttk.LabelFrame(results_frame, text="분석 결과 요약", padding=10)
        summary_frame.pack(fill='x', padx=10, pady=10)

        self.summary_text = tk.Text(summary_frame, height=8, font=("Courier", 10))
        self.summary_text.pack(fill='x')
        self.summary_text.insert('1.0', "분석을 실행하면 여기에 결과가 표시됩니다.")
        self.summary_text.config(state='disabled')

        # 하단 프레임 (그래프)
        graph_frame = ttk.LabelFrame(results_frame, text="그래프", padding=10)
        graph_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # matplotlib 캔버스
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # 툴바
        toolbar_frame = ttk.Frame(graph_frame)
        toolbar_frame.pack(fill='x')
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        # 내보내기 버튼
        export_frame = ttk.Frame(results_frame)
        export_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(export_frame, text="CSV로 저장",
                  command=self.export_csv).pack(side='left', padx=5)
        ttk.Button(export_frame, text="그래프 저장",
                  command=self.export_plot).pack(side='left', padx=5)

    def browse_csv(self):
        """CSV 파일 선택"""
        filename = filedialog.askopenfilename(
            title="CSV 파일 선택",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_entry.delete(0, tk.END)
            self.csv_entry.insert(0, filename)
            self.csv_path = filename

    def reset_settings(self):
        """설정을 기본값으로 재설정"""
        self.window_entry.delete(0, tk.END)
        self.window_entry.insert(0, "0.5")

        self.acceleration_entry.delete(0, tk.END)
        self.acceleration_entry.insert(0, "1e-7")

        self.derivative_var.set(True)

        messagebox.showinfo("설정 재설정", "모든 설정이 기본값으로 재설정되었습니다.")

    def log_message(self, message):
        """진행 상황 로그 출력"""
        self.progress_text.config(state='normal')
        self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state='disabled')
        self.root.update()

    def run_analysis(self):
        """분석 실행"""
        # 입력 검증
        try:
            stress_input = self.stress_entry.get().strip()
            stress_levels = [float(s.strip()) for s in stress_input.split(',')]

            csv_path = self.csv_entry.get().strip()
            if not csv_path or not os.path.exists(csv_path):
                messagebox.showerror("오류", "유효한 CSV 파일을 선택하세요.")
                return

            initial_stabilization_hours = float(self.stabilization_entry.get())
            load_interval_hours = float(self.interval_entry.get())

            # 고급 설정
            search_window_hours = float(self.window_entry.get())
            min_strain_acceleration = float(self.acceleration_entry.get())
            use_derivative = self.derivative_var.get()

        except ValueError as e:
            messagebox.showerror("입력 오류", f"입력값을 확인하세요: {str(e)}")
            return

        # 버튼 비활성화
        self.analyze_btn.config(state='disabled')

        # 진행 상황 초기화
        self.progress_text.config(state='normal')
        self.progress_text.delete('1.0', tk.END)
        self.progress_text.config(state='disabled')

        # 별도 스레드에서 분석 실행
        thread = threading.Thread(target=self._run_analysis_thread,
                                 args=(stress_levels, csv_path, initial_stabilization_hours,
                                       load_interval_hours, search_window_hours,
                                       min_strain_acceleration, use_derivative))
        thread.daemon = True
        thread.start()

    def _run_analysis_thread(self, stress_levels, csv_path, initial_stabilization_hours,
                            load_interval_hours, search_window_hours,
                            min_strain_acceleration, use_derivative):
        """분석 실행 (스레드)"""
        try:
            self.log_message("=" * 60)
            self.log_message("분석 시작...")
            self.log_message("=" * 60)

            # 분석기 생성
            self.log_message(f"\n하중 조건: {stress_levels} MPa")
            self.log_message(f"CSV 파일: {csv_path}")
            self.analyzer = CreepAnalyzer(stress_levels, csv_path)

            # 데이터 로드
            self.log_message("\n데이터 로딩 중...")
            self.analyzer.load_data()
            self.log_message(f"✓ 총 {len(self.analyzer.data)} 개의 데이터 포인트 로드됨")

            # 하중 구간 감지
            self.log_message("\n하중 구간 감지 중...")
            self.log_message(f"  - 초기 안정화: {initial_stabilization_hours}시간")
            self.log_message(f"  - 하중 간격: {load_interval_hours}시간")
            self.log_message(f"  - 탐색 윈도우: ±{search_window_hours}시간")
            self.log_message(f"  - 최소 가속도: {min_strain_acceleration:.2e} %/s²")
            self.log_message(f"  - 2차 미분 사용: {'예' if use_derivative else '아니오'}")

            self.analyzer.detect_load_segments(
                initial_stabilization_hours=initial_stabilization_hours,
                load_interval_hours=load_interval_hours,
                search_window_hours=search_window_hours,
                use_derivative=use_derivative,
                min_strain_acceleration=min_strain_acceleration
            )

            self.log_message(f"\n✓ {len(self.analyzer.segments)}개 구간 감지됨")

            # 2차 크리프 속도 계산
            self.log_message("\n2차 크리프 속도 계산 중...")
            self.analyzer.calculate_secondary_creep_rates()
            self.log_message(f"✓ {len(self.analyzer.secondary_creep_rates)}개 구간 분석 완료")

            # 응력지수 n 계산
            self.log_message("\n응력지수 n 계산 중...")
            n_value = self.analyzer.calculate_stress_exponent()

            if n_value is not None:
                self.log_message(f"\n{'=' * 60}")
                self.log_message("분석 결과:")
                self.log_message(f"{'=' * 60}")
                self.log_message(f"응력지수 n: {n_value:.3f}")
                self.log_message(f"log(A): {self.analyzer.log_A:.3f}")
                self.log_message(f"선형 적합도 (R²): {self.analyzer.n_r_squared:.4f}")
                self.log_message(f"{'=' * 60}")

            # 결과 표시
            self.root.after(0, self.display_results)

            # 그래프 생성
            self.log_message("\n그래프 생성 중...")
            self.root.after(0, self.plot_results)

            self.log_message("\n✓ 분석 완료!")

        except Exception as e:
            self.log_message(f"\n오류 발생: {str(e)}")
            import traceback
            self.log_message(traceback.format_exc())
            messagebox.showerror("분석 오류", f"분석 중 오류가 발생했습니다:\n{str(e)}")

        finally:
            # 버튼 활성화
            self.root.after(0, lambda: self.analyze_btn.config(state='normal'))

    def display_results(self):
        """결과 탭에 요약 정보 표시"""
        if not self.analyzer or not self.analyzer.stress_exponent_n:
            return

        # 결과 탭으로 전환
        self.notebook.select(2)

        # 요약 텍스트 작성
        summary = f"""
{'=' * 60}
분석 결과 요약
{'=' * 60}

응력지수 (n):        {self.analyzer.stress_exponent_n:.3f}
log(A):             {self.analyzer.log_A:.3f}
선형 적합도 (R²):    {self.analyzer.n_r_squared:.4f}

{'=' * 60}
구간별 2차 크리프 속도
{'=' * 60}
"""

        for rate_info in self.analyzer.secondary_creep_rates:
            summary += f"\n구간 {rate_info['segment_id']}: {rate_info['stress_MPa']} MPa"
            summary += f"\n  크리프 속도: {rate_info['creep_rate']:.2e} %/s"
            summary += f"\n  R²: {rate_info['r_squared']:.4f}\n"

        # 텍스트 업데이트
        self.summary_text.config(state='normal')
        self.summary_text.delete('1.0', tk.END)
        self.summary_text.insert('1.0', summary)
        self.summary_text.config(state='disabled')

    def plot_results(self):
        """그래프 생성"""
        if not self.analyzer:
            return

        self.figure.clear()

        # 2x2 서브플롯 생성
        axes = self.figure.subplots(2, 2)

        time = self.analyzer.data[self.analyzer.time_col].values
        strain = self.analyzer.data[self.analyzer.strain_col].values

        # 1. 전체 크리프 곡선
        ax1 = axes[0, 0]
        ax1.plot(time, strain, 'b-', linewidth=0.5, alpha=0.7)

        colors = plt.cm.rainbow(np.linspace(0, 1, len(self.analyzer.segments)))
        for i, segment in enumerate(self.analyzer.segments):
            start_idx = segment['start_idx']
            ax1.axvline(time[start_idx], color=colors[i], linestyle='--', alpha=0.5)
            ax1.text(time[start_idx], strain[start_idx],
                    f"{segment['stress_MPa']} MPa",
                    rotation=90, verticalalignment='bottom', fontsize=8)

        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Strain (%)')
        ax1.set_title('Multistep Creep Curve', fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # 2. 각 구간별 크리프 곡선
        ax2 = axes[0, 1]
        for i, rate_info in enumerate(self.analyzer.secondary_creep_rates):
            segment = self.analyzer.segments[rate_info['segment_id'] - 1]
            time_seg = segment['time']
            strain_seg = segment['strain']

            ax2.plot(time_seg, strain_seg, color=colors[i],
                    linewidth=1, alpha=0.5, label=f"{segment['stress_MPa']} MPa")

            secondary = rate_info['secondary_region']
            time_sec = secondary['time'] - secondary['time'][0]
            ax2.plot(time_sec, secondary['strain'],
                    color=colors[i], linewidth=2, marker='o', markersize=2)

        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Strain (%)')
        ax2.set_title('Secondary Creep Regions', fontweight='bold')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

        # 3. log(응력) vs log(변형률속도)
        ax3 = axes[1, 0]
        stresses = np.array([item['stress_MPa'] for item in self.analyzer.secondary_creep_rates])
        creep_rates = np.array([item['creep_rate'] for item in self.analyzer.secondary_creep_rates])

        log_stress = np.log10(stresses)
        log_creep_rate = np.log10(creep_rates)

        ax3.scatter(log_stress, log_creep_rate, s=80, c='red', marker='o',
                   edgecolors='black', linewidth=1.5, zorder=3)

        log_stress_line = np.linspace(log_stress.min(), log_stress.max(), 100)
        log_creep_rate_line = self.analyzer.stress_exponent_n * log_stress_line + self.analyzer.log_A
        ax3.plot(log_stress_line, log_creep_rate_line, 'b--', linewidth=2,
                label=f'n = {self.analyzer.stress_exponent_n:.3f}\\n$R^2$ = {self.analyzer.n_r_squared:.4f}')

        ax3.set_xlabel('log(Stress) [log(MPa)]')
        ax3.set_ylabel('log(Strain Rate) [log(%/s)]')
        ax3.set_title('Stress Exponent n', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 4. 응력 vs 변형률속도 (실제 스케일)
        ax4 = axes[1, 1]
        ax4.scatter(stresses, creep_rates, s=80, c='green', marker='s',
                   edgecolors='black', linewidth=1.5, zorder=3)

        stress_line = np.linspace(stresses.min(), stresses.max(), 100)
        creep_rate_line = 10**self.analyzer.log_A * stress_line**self.analyzer.stress_exponent_n
        ax4.plot(stress_line, creep_rate_line, 'b--', linewidth=2)

        ax4.set_xlabel('Stress (MPa)')
        ax4.set_ylabel('Strain Rate (%/s)')
        ax4.set_title('Stress vs Strain Rate', fontweight='bold')
        ax4.set_yscale('log')
        ax4.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()

    def export_csv(self):
        """결과를 CSV로 저장"""
        if not self.analyzer:
            messagebox.showwarning("경고", "분석을 먼저 실행하세요.")
            return

        filename = filedialog.asksaveasfilename(
            title="CSV 저장",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            self.analyzer.save_results(filename)
            messagebox.showinfo("저장 완료", f"결과가 저장되었습니다:\n{filename}")

    def export_plot(self):
        """그래프를 이미지로 저장"""
        if not self.analyzer:
            messagebox.showwarning("경고", "분석을 먼저 실행하세요.")
            return

        filename = filedialog.asksaveasfilename(
            title="그래프 저장",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("PDF files", "*.pdf"),
                      ("SVG files", "*.svg"), ("All files", "*.*")]
        )

        if filename:
            self.figure.savefig(filename, dpi=300, bbox_inches='tight')
            messagebox.showinfo("저장 완료", f"그래프가 저장되었습니다:\n{filename}")


def main():
    """GUI 메인 함수"""
    root = tk.Tk()

    # 스타일 설정
    style = ttk.Style()
    style.theme_use('clam')

    app = CreepAnalyzerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    import numpy as np  # plot_results에서 필요
    main()
