#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트용 Multistep Creep 데이터 생성기
실제 크리프 시험을 시뮬레이션한 CSV 파일 생성
"""

import numpy as np
import pandas as pd


def generate_creep_curve(time, stress, n=5, A=1e-8, Q=200000, R=8.314, T=1000):
    """
    크리프 곡선 생성 (Norton's law 기반)

    Parameters:
    -----------
    time : array
        시간 배열 (초)
    stress : float
        응력 (MPa)
    n : float
        응력지수 (목표값)
    A : float
        재료 상수
    Q : float
        활성화 에너지 (J/mol)
    R : float
        기체 상수
    T : float
        온도 (K)

    Returns:
    --------
    strain : array
        변형률 (%)
    """
    # Norton's law: strain_rate = A * stress^n * exp(-Q/RT)
    strain_rate_secondary = A * (stress ** n) * np.exp(-Q / (R * T))

    strain = np.zeros_like(time)

    for i in range(1, len(time)):
        dt = time[i] - time[i - 1]
        t_local = time[i] - time[0]

        # 1차 크리프 (감소하는 변형률 속도)
        primary_factor = 2.0 * np.exp(-t_local / 1000)

        # 3차 크리프 (증가하는 변형률 속도) - 후반부
        tertiary_factor = 1.0 + 0.5 * (t_local / time[-1]) ** 4

        # 순간 변형률 속도
        instantaneous_rate = strain_rate_secondary * (1 + primary_factor) * tertiary_factor

        # 변형률 적분
        strain[i] = strain[i - 1] + instantaneous_rate * dt

    return strain


def generate_multistep_creep_data(stress_levels=[15, 25, 35, 45],
                                   duration_per_step=10000,
                                   normal_interval=30,
                                   transition_interval=1,
                                   transition_duration=300,
                                   output_path='sample_creep_data.csv'):
    """
    Multistep creep 데이터 생성

    Parameters:
    -----------
    stress_levels : list
        각 단계의 응력 레벨 (MPa)
    duration_per_step : float
        각 하중 단계의 지속 시간 (초)
    normal_interval : float
        정상 데이터 기록 주기 (초)
    transition_interval : float
        하중 전환 시 데이터 기록 주기 (초)
    transition_duration : float
        하중 전환 시 빠른 기록 지속 시간 (초)
    output_path : str
        출력 파일 경로
    """

    print("Multistep Creep 데이터 생성 중...")

    all_time = []
    all_strain = []
    current_time = 0

    for step_idx, stress in enumerate(stress_levels):
        print(f"\n단계 {step_idx + 1}: {stress} MPa")

        # 하중 전환 구간 (빠른 데이터 기록)
        transition_time = np.arange(0, transition_duration, transition_interval)
        transition_strain = generate_creep_curve(transition_time, stress)

        # 정상 구간 (느린 데이터 기록)
        normal_time = np.arange(transition_duration, duration_per_step, normal_interval)
        normal_strain = generate_creep_curve(normal_time, stress)

        # 시간 오프셋 적용
        step_time = np.concatenate([transition_time, normal_time]) + current_time
        step_strain = np.concatenate([transition_strain, normal_strain])

        # 이전 단계의 마지막 변형률에 누적
        if step_idx > 0:
            step_strain += all_strain[-1]

        all_time.extend(step_time)
        all_strain.extend(step_strain)

        current_time = step_time[-1]

    # 노이즈 추가 (실제 측정 데이터처럼)
    all_strain = np.array(all_strain, dtype=np.float64)
    noise = np.random.normal(0, 0.0001, len(all_strain))  # 0.0001% 수준의 노이즈
    all_strain = all_strain + noise

    # DataFrame 생성
    df = pd.DataFrame({
        'Time(s)': all_time,
        'Strain(%)': all_strain
    })

    # CSV 저장
    df.to_csv(output_path, index=False)
    print(f"\n생성 완료!")
    print(f"파일 경로: {output_path}")
    print(f"총 데이터 포인트: {len(df)}")
    print(f"총 시험 시간: {all_time[-1]:.1f} 초 ({all_time[-1]/3600:.2f} 시간)")

    return df


if __name__ == "__main__":
    # 샘플 데이터 생성
    df = generate_multistep_creep_data(
        stress_levels=[15, 25, 35, 45],
        duration_per_step=10000,  # 각 단계 약 2.8시간
        normal_interval=30,
        transition_interval=1,
        transition_duration=300,
        output_path='sample_creep_data.csv'
    )

    print("\n생성된 데이터 미리보기:")
    print(df.head(20))
    print("\n...")
    print(df.tail(10))
