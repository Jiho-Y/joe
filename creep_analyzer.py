#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multistep Creep Test Analyzer
크리프 시험 데이터에서 2차 크리프 속도를 측정하고 응력지수 n을 계산하는 프로그램
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.signal import savgol_filter
import os


class CreepAnalyzer:
    """
    Multistep creep 시험 데이터를 분석하는 클래스
    """

    def __init__(self, stress_levels, csv_path, time_col='Time(s)', strain_col='Strain(%)'):
        """
        Parameters:
        -----------
        stress_levels : list
            다단계 하중 조건 리스트 (MPa) 예: [15, 25, 35, 45]
        csv_path : str
            CSV 파일 경로
        time_col : str
            시간 컬럼명 (기본값: 'Time(s)')
        strain_col : str
            변형률 컬럼명 (기본값: 'Strain(%)')
        """
        self.stress_levels = np.array(stress_levels)
        self.csv_path = csv_path
        self.time_col = time_col
        self.strain_col = strain_col

        self.data = None
        self.segments = []
        self.secondary_creep_rates = []
        self.stress_exponent_n = None

    def load_data(self):
        """CSV 파일로부터 데이터 로드"""
        print(f"데이터 로딩 중: {self.csv_path}")
        self.data = pd.read_csv(self.csv_path)
        print(f"총 {len(self.data)} 개의 데이터 포인트 로드됨")

        # 컬럼명 확인
        print(f"사용 가능한 컬럼: {list(self.data.columns)}")

        # 컬럼명이 정확하지 않은 경우 자동으로 찾기
        if self.time_col not in self.data.columns:
            time_candidates = [col for col in self.data.columns if 'time' in col.lower()]
            if time_candidates:
                self.time_col = time_candidates[0]
                print(f"시간 컬럼 자동 선택: {self.time_col}")

        if self.strain_col not in self.data.columns:
            strain_candidates = [col for col in self.data.columns if 'strain' in col.lower()]
            if strain_candidates:
                self.strain_col = strain_candidates[0]
                print(f"변형률 컬럼 자동 선택: {self.strain_col}")

        return self.data

    def detect_load_segments(self, initial_stabilization_hours=48, load_interval_hours=24,
                            search_window_hours=0.5, use_derivative=True, min_strain_acceleration=1e-6):
        """
        하중 구간 자동 감지 (개선된 알고리즘)

        Parameters:
        -----------
        initial_stabilization_hours : float
            초기 안정화 시간 (시간) - 기본값 48시간 (첫 번째 하중 증가 전 안정화 기간)
        load_interval_hours : float
            하중 증가 예상 시간 간격 (시간) - 기본값 24시간
        search_window_hours : float
            각 하중 증가 시점 탐색 윈도우 크기 (시간) - 기본값 ±0.5시간
        use_derivative : bool
            2차 미분(변형률 가속도) 사용 여부 - 기본값 True
        min_strain_acceleration : float
            최소 변형률 가속도 임계값 (%/s²) - 기본값 1e-6

        Returns:
        --------
        segments : list of dict
            각 하중 구간의 시작/끝 인덱스와 응력 레벨
        """
        print("\n하중 구간 감지 중 (개선된 알고리즘)...")
        print(f"설정: 초기 안정화 {initial_stabilization_hours}시간, 하중 간격 {load_interval_hours}시간, "
              f"탐색 윈도우 ±{search_window_hours}시간")

        time = self.data[self.time_col].values
        strain = self.data[self.strain_col].values

        # 시간을 시간 단위로 변환
        time_hours = time / 3600.0
        total_duration_hours = time_hours[-1]

        print(f"전체 시험 시간: {total_duration_hours:.2f}시간 ({time[-1]/3600:.2f}시간)")

        # 예상되는 하중 구간 개수 계산
        expected_segments = len(self.stress_levels)
        expected_transitions = expected_segments - 1

        print(f"예상 하중 전환 횟수: {expected_transitions}회 (총 {expected_segments}개 구간)")

        # 시간 간격 및 1차 미분 (변형률 속도) 계산
        time_diffs = np.diff(time)
        # 0으로 나누기 방지: 매우 작은 값으로 대체
        time_diffs = np.where(time_diffs == 0, 1e-10, time_diffs)
        strain_rate = np.diff(strain) / time_diffs

        # 2차 미분 (변형률 가속도) 계산 - 하중 증가 시점에서 급증
        if use_derivative and len(strain_rate) > 1:
            time_diffs_2 = np.diff(time[:-1])
            # 0으로 나누기 방지
            time_diffs_2 = np.where(time_diffs_2 == 0, 1e-10, time_diffs_2)
            strain_acceleration = np.diff(strain_rate) / time_diffs_2
            strain_acceleration_abs = np.abs(strain_acceleration)
            # inf 값 처리
            strain_acceleration_abs = np.where(np.isinf(strain_acceleration_abs),
                                              np.nanmax(strain_acceleration_abs[~np.isinf(strain_acceleration_abs)]) if np.any(~np.isinf(strain_acceleration_abs)) else 1e10,
                                              strain_acceleration_abs)
        else:
            strain_acceleration_abs = np.abs(strain_rate[:-1])

        # 각 예상 시점 근처에서 하중 증가 지점 탐색
        load_change_indices = [0]  # 시작점

        # 첫 번째 전환: 초기 안정화 이후, 이후는 load_interval_hours 간격으로 탐색
        for transition_idx in range(1, expected_segments):
            if transition_idx == 1:
                # 첫 번째 하중 증가: 초기 안정화 시간 이후
                expected_time_hours = initial_stabilization_hours
            else:
                # 이후 하중 증가: 첫 번째 이후 load_interval_hours 간격
                expected_time_hours = initial_stabilization_hours + load_interval_hours * (transition_idx - 1)

            # 탐색 범위 설정 (±search_window_hours)
            search_start_hours = expected_time_hours - search_window_hours
            search_end_hours = expected_time_hours + search_window_hours

            # 시간 범위를 인덱스로 변환
            search_start_idx = np.searchsorted(time_hours, search_start_hours)
            search_end_idx = np.searchsorted(time_hours, search_end_hours)

            # 범위 보정
            search_start_idx = max(1, min(search_start_idx, len(strain_acceleration_abs)))
            search_end_idx = max(search_start_idx + 1, min(search_end_idx, len(strain_acceleration_abs)))

            if search_start_idx >= search_end_idx:
                print(f"  경고: 전환 {transition_idx} ({expected_time_hours:.1f}시간) - 탐색 범위 부족")
                continue

            print(f"  탐색 중: 전환 {transition_idx} 예상시간 {expected_time_hours:.1f}시간 "
                  f"(범위: {search_start_hours:.1f}~{search_end_hours:.1f}시간)")

            # 탐색 범위 내에서 변형률 가속도가 최대인 지점 찾기
            search_region = strain_acceleration_abs[search_start_idx:search_end_idx]

            if len(search_region) == 0:
                print(f"    경고: 탐색 범위가 비어있음")
                continue

            # 가속도가 임계값 이상인 지점들 찾기
            candidates = np.where(search_region > min_strain_acceleration)[0]

            if len(candidates) == 0:
                # 임계값을 만족하는 지점이 없으면 최대값 사용
                max_idx_in_region = np.argmax(search_region)
                detected_idx = search_start_idx + max_idx_in_region
                max_acceleration = search_region[max_idx_in_region]
                print(f"    임계값 미달, 최대값 사용: 인덱스 {detected_idx}, "
                      f"시간 {time_hours[detected_idx]:.2f}시간, "
                      f"가속도 {max_acceleration:.2e} %/s²")
            else:
                # 가장 큰 가속도를 가진 지점 선택
                max_idx_among_candidates = candidates[np.argmax(search_region[candidates])]
                detected_idx = search_start_idx + max_idx_among_candidates
                max_acceleration = search_region[max_idx_among_candidates]
                print(f"    감지: 인덱스 {detected_idx}, "
                      f"시간 {time_hours[detected_idx]:.2f}시간, "
                      f"가속도 {max_acceleration:.2e} %/s²")

            # 중복 방지: 이전 지점과 충분히 떨어져 있는지 확인
            if detected_idx - load_change_indices[-1] > 100:
                load_change_indices.append(detected_idx)
            else:
                print(f"    경고: 이전 전환점과 너무 가까움 (건너뜀)")

        load_change_indices.append(len(strain) - 1)  # 끝점

        print(f"\n최종 감지된 하중 구간: {len(load_change_indices) - 1}개")

        # 구간별 데이터 분할
        self.segments = []
        num_segments = len(load_change_indices) - 1

        for i in range(num_segments):
            start_idx = load_change_indices[i]
            end_idx = load_change_indices[i + 1]

            # 응력 레벨 할당
            if i < len(self.stress_levels):
                stress = self.stress_levels[i]
            else:
                print(f"경고: {i+1}번째 구간의 응력 레벨이 지정되지 않았습니다.")
                stress = None

            segment = {
                'segment_id': i + 1,
                'start_idx': start_idx,
                'end_idx': end_idx,
                'stress_MPa': stress,
                'time': time[start_idx:end_idx] - time[start_idx],  # 구간별로 시간 0부터 시작
                'strain': strain[start_idx:end_idx]
            }

            self.segments.append(segment)

            duration = time[end_idx] - time[start_idx]
            strain_range = strain[end_idx] - strain[start_idx]
            print(f"  구간 {i+1}: 응력 {stress} MPa, "
                  f"지속시간 {duration:.1f}s, "
                  f"변형률 범위 {strain_range:.4f}%")

        return self.segments

    def find_secondary_creep_region(self, segment, window_size=50, poly_order=3):
        """
        2차 크리프(정상상태) 구간 찾기

        2차 크리프는 변형률 속도가 최소이면서 일정한 구간

        Parameters:
        -----------
        segment : dict
            분석할 하중 구간
        window_size : int
            Savitzky-Golay 필터 윈도우 크기
        poly_order : int
            Savitzky-Golay 필터 다항식 차수

        Returns:
        --------
        dict : 2차 크리프 구간 정보
        """
        time = segment['time']
        strain = segment['strain']

        if len(time) < window_size:
            window_size = len(time) // 2
            if window_size % 2 == 0:
                window_size -= 1
            if window_size < poly_order + 2:
                print(f"  경고: 구간 {segment['segment_id']} 데이터가 부족합니다.")
                return None

        # 변형률 속도 계산 (Savitzky-Golay 필터로 스무딩)
        try:
            strain_smooth = savgol_filter(strain, window_size, poly_order)
            time_diffs = np.diff(time)
            # 0으로 나누기 방지
            time_diffs = np.where(time_diffs == 0, 1e-10, time_diffs)
            strain_rate = np.diff(strain_smooth) / time_diffs
        except:
            # 필터 적용 실패 시 단순 미분
            time_diffs = np.diff(time)
            time_diffs = np.where(time_diffs == 0, 1e-10, time_diffs)
            strain_rate = np.diff(strain) / time_diffs

        # 변형률 속도를 다시 스무딩
        if len(strain_rate) >= window_size:
            try:
                strain_rate_smooth = savgol_filter(strain_rate, window_size, poly_order)
            except:
                strain_rate_smooth = strain_rate
        else:
            strain_rate_smooth = strain_rate

        # 1차 크리프 제외 (초기 20% 구간)
        start_search_idx = int(len(strain_rate_smooth) * 0.2)
        # 3차 크리프 제외 (마지막 10% 구간)
        end_search_idx = int(len(strain_rate_smooth) * 0.9)

        if start_search_idx >= end_search_idx:
            print(f"  경고: 구간 {segment['segment_id']} 분석 범위가 부족합니다.")
            return None

        search_region = strain_rate_smooth[start_search_idx:end_search_idx]

        # 2차 크리프: 변형률 속도가 최소이면서 가장 안정적인 구간
        # 이동 평균의 표준편차를 계산하여 가장 안정적인 구간 찾기
        stability_window = min(100, len(search_region) // 3)
        if stability_window < 10:
            stability_window = len(search_region) // 2

        min_std = float('inf')
        best_start = start_search_idx

        for i in range(start_search_idx, end_search_idx - stability_window):
            window_data = strain_rate_smooth[i:i + stability_window]
            std = np.std(window_data)
            if std < min_std:
                min_std = std
                best_start = i

        best_end = best_start + stability_window

        # 선형 회귀로 2차 크리프 속도 계산
        time_region = time[best_start:best_end]
        strain_region = strain[best_start:best_end]

        # 시간을 0부터 시작하도록 정규화
        time_normalized = time_region - time_region[0]

        slope, intercept, r_value, p_value, std_err = stats.linregress(time_normalized, strain_region)

        return {
            'start_idx': best_start,
            'end_idx': best_end,
            'time': time_region,
            'strain': strain_region,
            'creep_rate': slope,  # %/s
            'r_squared': r_value**2,
            'std_err': std_err
        }

    def calculate_secondary_creep_rates(self):
        """
        모든 하중 구간에서 2차 크리프 속도 계산
        """
        print("\n2차 크리프 속도 계산 중...")

        self.secondary_creep_rates = []

        for segment in self.segments:
            if segment['stress_MPa'] is None:
                continue

            print(f"\n구간 {segment['segment_id']} (응력: {segment['stress_MPa']} MPa)")

            secondary_region = self.find_secondary_creep_region(segment)

            if secondary_region is None:
                print(f"  2차 크리프 구간을 찾을 수 없습니다.")
                continue

            creep_rate = secondary_region['creep_rate']
            r_squared = secondary_region['r_squared']

            print(f"  2차 크리프 속도: {creep_rate:.2e} %/s")
            print(f"  선형 적합도 (R²): {r_squared:.4f}")

            self.secondary_creep_rates.append({
                'segment_id': segment['segment_id'],
                'stress_MPa': segment['stress_MPa'],
                'creep_rate': creep_rate,
                'r_squared': r_squared,
                'secondary_region': secondary_region
            })

        return self.secondary_creep_rates

    def calculate_stress_exponent(self):
        """
        응력지수 n 계산

        변형률속도 = A * 응력^n
        log(변형률속도) = log(A) + n * log(응력)

        Returns:
        --------
        n : float
            응력지수
        """
        print("\n응력지수 n 계산 중...")

        if len(self.secondary_creep_rates) < 2:
            print("경고: 최소 2개 이상의 하중 구간이 필요합니다.")
            return None

        stresses = np.array([item['stress_MPa'] for item in self.secondary_creep_rates])
        creep_rates = np.array([item['creep_rate'] for item in self.secondary_creep_rates])

        # 양수 값만 사용 (로그 계산을 위해)
        valid_mask = (stresses > 0) & (creep_rates > 0)
        stresses = stresses[valid_mask]
        creep_rates = creep_rates[valid_mask]

        if len(stresses) < 2:
            print("경고: 유효한 데이터가 부족합니다.")
            return None

        # 로그-로그 선형 회귀
        log_stress = np.log10(stresses)
        log_creep_rate = np.log10(creep_rates)

        slope, intercept, r_value, p_value, std_err = stats.linregress(log_stress, log_creep_rate)

        self.stress_exponent_n = slope
        self.log_A = intercept
        self.n_r_squared = r_value**2

        print(f"\n=== 분석 결과 ===")
        print(f"응력지수 n: {self.stress_exponent_n:.3f}")
        print(f"log(A): {self.log_A:.3f}")
        print(f"선형 적합도 (R²): {self.n_r_squared:.4f}")

        return self.stress_exponent_n

    def plot_results(self, save_path=None):
        """
        결과 시각화

        Parameters:
        -----------
        save_path : str, optional
            그래프 저장 경로
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # 1. 전체 크리프 곡선
        ax1 = axes[0, 0]
        time = self.data[self.time_col].values
        strain = self.data[self.strain_col].values
        ax1.plot(time, strain, 'b-', linewidth=0.5, alpha=0.7)

        # 하중 구간 표시
        colors = plt.cm.rainbow(np.linspace(0, 1, len(self.segments)))
        for i, segment in enumerate(self.segments):
            start_idx = segment['start_idx']
            end_idx = segment['end_idx']
            ax1.axvline(time[start_idx], color=colors[i], linestyle='--', alpha=0.5)
            ax1.text(time[start_idx], strain[start_idx],
                    f"{segment['stress_MPa']} MPa",
                    rotation=90, verticalalignment='bottom')

        ax1.set_xlabel('Time (s)', fontsize=12)
        ax1.set_ylabel('Strain (%)', fontsize=12)
        ax1.set_title('Multistep Creep Curve', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # 2. 각 구간별 크리프 곡선과 2차 크리프 영역
        ax2 = axes[0, 1]
        for i, rate_info in enumerate(self.secondary_creep_rates):
            segment = self.segments[rate_info['segment_id'] - 1]
            time_seg = segment['time']
            strain_seg = segment['strain']

            # 전체 구간
            ax2.plot(time_seg, strain_seg, color=colors[i],
                    linewidth=1, alpha=0.5, label=f"{segment['stress_MPa']} MPa")

            # 2차 크리프 영역 강조
            secondary = rate_info['secondary_region']
            time_sec = secondary['time'] - secondary['time'][0]
            ax2.plot(time_sec, secondary['strain'],
                    color=colors[i], linewidth=2, marker='o', markersize=3)

        ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('Strain (%)', fontsize=12)
        ax2.set_title('Secondary Creep Regions', fontsize=14, fontweight='bold')
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)

        # 3. log(응력) vs log(변형률속도) - 응력지수 n 계산
        ax3 = axes[1, 0]
        stresses = np.array([item['stress_MPa'] for item in self.secondary_creep_rates])
        creep_rates = np.array([item['creep_rate'] for item in self.secondary_creep_rates])

        log_stress = np.log10(stresses)
        log_creep_rate = np.log10(creep_rates)

        ax3.scatter(log_stress, log_creep_rate, s=100, c='red', marker='o',
                   edgecolors='black', linewidth=1.5, zorder=3)

        # 회귀선
        log_stress_line = np.linspace(log_stress.min(), log_stress.max(), 100)
        log_creep_rate_line = self.stress_exponent_n * log_stress_line + self.log_A
        ax3.plot(log_stress_line, log_creep_rate_line, 'b--', linewidth=2,
                label=f'n = {self.stress_exponent_n:.3f}\n$R^2$ = {self.n_r_squared:.4f}')

        ax3.set_xlabel('log(Stress) [log(MPa)]', fontsize=12)
        ax3.set_ylabel('log(Strain Rate) [log(%/s)]', fontsize=12)
        ax3.set_title('Stress Exponent n Calculation', fontsize=14, fontweight='bold')
        ax3.legend(loc='best', fontsize=11)
        ax3.grid(True, alpha=0.3)

        # 4. 응력 vs 변형률속도 (실제 스케일)
        ax4 = axes[1, 1]
        ax4.scatter(stresses, creep_rates, s=100, c='green', marker='s',
                   edgecolors='black', linewidth=1.5, zorder=3)

        # 멱함수 곡선
        stress_line = np.linspace(stresses.min(), stresses.max(), 100)
        creep_rate_line = 10**self.log_A * stress_line**self.stress_exponent_n
        ax4.plot(stress_line, creep_rate_line, 'b--', linewidth=2,
                label=f'$\\dot{{\\epsilon}}$ = A·$\\sigma^{{{self.stress_exponent_n:.2f}}}$')

        ax4.set_xlabel('Stress (MPa)', fontsize=12)
        ax4.set_ylabel('Strain Rate (%/s)', fontsize=12)
        ax4.set_title('Stress vs Strain Rate', fontsize=14, fontweight='bold')
        ax4.legend(loc='best', fontsize=11)
        ax4.grid(True, alpha=0.3)
        ax4.set_yscale('log')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"\n그래프 저장됨: {save_path}")

        plt.show()

    def save_results(self, output_path='creep_analysis_results.csv'):
        """
        분석 결과를 CSV 파일로 저장

        Parameters:
        -----------
        output_path : str
            출력 파일 경로
        """
        results_data = []

        for rate_info in self.secondary_creep_rates:
            results_data.append({
                'Segment': rate_info['segment_id'],
                'Stress (MPa)': rate_info['stress_MPa'],
                'Secondary Creep Rate (%/s)': rate_info['creep_rate'],
                'R-squared': rate_info['r_squared']
            })

        df_results = pd.DataFrame(results_data)

        # 응력지수 정보 추가
        summary_row = pd.DataFrame([{
            'Segment': 'Summary',
            'Stress (MPa)': f'Stress Exponent n = {self.stress_exponent_n:.3f}',
            'Secondary Creep Rate (%/s)': f'R² = {self.n_r_squared:.4f}',
            'R-squared': ''
        }])

        df_results = pd.concat([df_results, summary_row], ignore_index=True)

        df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n분석 결과 저장됨: {output_path}")

        return df_results


def main():
    """
    메인 실행 함수
    """
    print("=" * 60)
    print("Multistep Creep Test Analyzer")
    print("2차 크리프 속도 측정 및 응력지수 n 계산")
    print("=" * 60)

    # 1. 다단계 하중 조건 입력
    print("\n[1단계] 다단계 크리프 하중 조건 입력")
    print("예시: 15, 25, 35, 45")
    stress_input = input("하중 조건을 쉼표로 구분하여 입력하세요 (MPa): ")
    stress_levels = [float(s.strip()) for s in stress_input.split(',')]
    print(f"입력된 하중 조건: {stress_levels} MPa")

    # 1-1. 초기 안정화 시간 입력 (옵션)
    print("\n초기 안정화 시간을 입력하세요 (기본값: 48시간)")
    print("(첫 번째 하중 증가 전 안정화 기간)")
    stabilization_input = input("초기 안정화 시간 (시간, Enter키로 기본값 사용): ").strip()
    if stabilization_input:
        initial_stabilization_hours = float(stabilization_input)
    else:
        initial_stabilization_hours = 48.0
    print(f"초기 안정화 시간: {initial_stabilization_hours}시간")

    # 1-2. 하중 증가 간격 입력 (옵션)
    print("\n하중 증가 시간 간격을 입력하세요 (기본값: 24시간)")
    interval_input = input("하중 간격 (시간, Enter키로 기본값 사용): ").strip()
    if interval_input:
        load_interval_hours = float(interval_input)
    else:
        load_interval_hours = 24.0
    print(f"하중 간격: {load_interval_hours}시간")

    # 2. CSV 파일 경로 입력
    print("\n[2단계] CSV 파일 경로 입력")
    csv_path = input("CSV 파일 경로를 입력하세요: ").strip()

    if not os.path.exists(csv_path):
        print(f"오류: 파일을 찾을 수 없습니다 - {csv_path}")
        return

    # 3. 분석 실행
    print("\n[3단계] 데이터 분석 시작")

    analyzer = CreepAnalyzer(stress_levels, csv_path)

    # 데이터 로드
    analyzer.load_data()

    # 하중 구간 감지 (개선된 알고리즘)
    analyzer.detect_load_segments(
        initial_stabilization_hours=initial_stabilization_hours,
        load_interval_hours=load_interval_hours,
        search_window_hours=0.5,  # ±0.5시간 탐색 (총 1시간)
        use_derivative=True,
        min_strain_acceleration=1e-7  # 민감한 임계값
    )

    # 2차 크리프 속도 계산
    analyzer.calculate_secondary_creep_rates()

    # 응력지수 n 계산
    n_value = analyzer.calculate_stress_exponent()

    # 결과 저장
    analyzer.save_results()

    # 결과 시각화
    print("\n[4단계] 결과 시각화")
    output_dir = os.path.dirname(csv_path)
    plot_path = os.path.join(output_dir, 'creep_analysis_plot.png')
    analyzer.plot_results(save_path=plot_path)

    print("\n" + "=" * 60)
    print("분석 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
