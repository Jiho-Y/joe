#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트 스크립트: 개선된 creep analyzer 테스트
"""

from creep_analyzer import CreepAnalyzer

# 테스트: 샘플 데이터로 분석
print("개선된 알고리즘 테스트 시작...")

analyzer = CreepAnalyzer(
    stress_levels=[15, 25, 35, 45],
    csv_path='sample_creep_data.csv'
)

# 데이터 로드
analyzer.load_data()

# 하중 구간 감지 (개선된 알고리즘)
# 샘플 데이터는 약 2.8시간 간격이므로 테스트용으로 조정
print("\n=== 개선된 알고리즘 테스트 (샘플 데이터: 2.8시간 간격) ===")
analyzer.detect_load_segments(
    initial_stabilization_hours=2.78,  # 첫 번째: 2.78시간 후
    load_interval_hours=2.78,  # 이후: 2.78시간 간격
    search_window_hours=0.5,
    use_derivative=True,
    min_strain_acceleration=1e-8
)

# 결과 확인
print(f"\n감지된 구간 수: {len(analyzer.segments)}")
print(f"예상 구간 수: {len(analyzer.stress_levels)}")

if len(analyzer.segments) == len(analyzer.stress_levels):
    print("✓ 하중 구간 감지 성공!")
else:
    print(f"⚠ 경고: 예상({len(analyzer.stress_levels)})과 감지({len(analyzer.segments)})가 다릅니다.")

# 2차 크리프 속도 계산
analyzer.calculate_secondary_creep_rates()

# 응력지수 n 계산
n_value = analyzer.calculate_stress_exponent()

print("\n테스트 완료!")
