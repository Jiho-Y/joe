# Multistep Creep Test Analyzer

**크리프(Creep) 시험 데이터 분석 도구**

이 프로그램은 다단계(multistep) 크리프 시험 데이터에서 2차 크리프(정상상태 크리프) 속도를 자동으로 측정하고, 응력지수 n을 계산하는 Python 기반 분석 도구입니다.

## 주요 기능

1. **하중 구간 자동 감지**
   - Strain 급증 구간 감지
   - 데이터 기록 주기 변화 감지 (30s → 1s)
   - 다단계 하중 조건 자동 분할

2. **2차 크리프 속도 측정**
   - 각 하중 구간에서 정상상태 크리프 구간 자동 식별
   - Savitzky-Golay 필터를 이용한 노이즈 제거
   - 선형 회귀를 통한 정확한 변형률 속도 계산

3. **응력지수 n 계산**
   - Norton's law 기반: ε̇ = A·σⁿ
   - log-log 선형 회귀로 응력지수 도출
   - 통계적 신뢰도(R²) 제공

4. **결과 시각화 및 저장**
   - 전체 크리프 곡선 플롯
   - 2차 크리프 구간 강조 표시
   - 응력-변형률속도 관계 그래프
   - CSV 형식으로 결과 저장

## 설치 방법

### 필수 요구사항
- Python 3.7 이상
- pip (Python 패키지 관리자)

### 패키지 설치

```bash
pip install -r requirements.txt
```

필요한 패키지:
- `numpy`: 수치 계산
- `pandas`: 데이터 처리
- `matplotlib`: 그래프 시각화
- `scipy`: 통계 분석 및 신호 처리

## 사용 방법

### 1. 기본 사용법 (대화형 모드)

```bash
python3 creep_analyzer.py
```

프로그램 실행 후 다음 정보를 입력:
1. 다단계 하중 조건 (쉼표로 구분, 예: `15, 25, 35, 45`)
2. CSV 파일 경로

### 2. Python 스크립트에서 사용

```python
from creep_analyzer import CreepAnalyzer

# 분석기 초기화
analyzer = CreepAnalyzer(
    stress_levels=[15, 25, 35, 45],  # MPa
    csv_path='path/to/your/data.csv'
)

# 데이터 로드
analyzer.load_data()

# 하중 구간 감지
analyzer.detect_load_segments()

# 2차 크리프 속도 계산
analyzer.calculate_secondary_creep_rates()

# 응력지수 n 계산
n_value = analyzer.calculate_stress_exponent()

# 결과 저장
analyzer.save_results('results.csv')

# 결과 시각화
analyzer.plot_results(save_path='analysis_plot.png')
```

## CSV 파일 형식

입력 CSV 파일은 다음 형식이어야 합니다:

```csv
Time(s),Strain(%)
0,0.0001
1,0.0002
2,0.0003
...
```

- **Time(s)**: 시간 (초 단위)
- **Strain(%)**: 변형률 (% 단위)

> **참고**: 컬럼명이 다른 경우 자동으로 감지됩니다. 'time'이나 'strain'이 포함된 컬럼을 자동으로 찾습니다.

## 알고리즘 설명

### 하중 구간 감지

프로그램은 다음 두 가지 방법으로 하중 증가 지점을 감지합니다:

1. **변형률 급증 감지**
   - 순간 변형률 속도가 평균의 10배 이상일 때
   - 하중이 증가하면 즉각적인 탄성 변형 발생

2. **데이터 기록 주기 변화**
   - 시간 간격이 중앙값의 1/5 이하로 감소할 때
   - 시험 장비가 급격한 변화 감지 시 기록 주기 변경 (30s → 1s)

### 2차 크리프 구간 식별

각 하중 구간에서:

1. **1차 크리프 제외**: 초기 20% 구간 제외
2. **3차 크리프 제외**: 마지막 10% 구간 제외
3. **안정적인 구간 탐색**: 변형률 속도의 표준편차가 최소인 구간
4. **선형 회귀**: 선택된 구간에서 strain vs time의 기울기 계산

### 응력지수 계산

Norton's law를 기반으로:

```
ε̇ = A·σⁿ

log(ε̇) = log(A) + n·log(σ)
```

- 각 하중 구간의 2차 크리프 속도(ε̇)와 응력(σ)을 로그 변환
- 선형 회귀로 기울기 n 계산
- R² 값으로 적합도 평가

## 출력 결과

### 1. 콘솔 출력
```
=== 분석 결과 ===
응력지수 n: 5.123
log(A): -7.456
선형 적합도 (R²): 0.9876
```

### 2. CSV 파일 (`creep_analysis_results.csv`)
```csv
Segment,Stress (MPa),Secondary Creep Rate (%/s),R-squared
1,15,1.23e-06,0.9845
2,25,4.56e-06,0.9912
3,35,1.12e-05,0.9889
4,45,2.34e-05,0.9901
Summary,Stress Exponent n = 5.123,R² = 0.9876,
```

### 3. 그래프 (`creep_analysis_plot.png`)
- 좌상: 전체 Multistep 크리프 곡선
- 우상: 2차 크리프 구간 강조
- 좌하: log(응력) vs log(변형률속도) - 응력지수 계산
- 우하: 응력 vs 변형률속도 (실제 스케일)

## 테스트용 샘플 데이터 생성

프로젝트에 샘플 데이터 생성기가 포함되어 있습니다:

```bash
python3 generate_sample_creep_data.py
```

이 스크립트는 실제 multistep creep 시험을 시뮬레이션한 CSV 파일(`sample_creep_data.csv`)을 생성합니다.

### 샘플 데이터로 테스트

```bash
# 1. 샘플 데이터 생성
python3 generate_sample_creep_data.py

# 2. 분석 실행
python3 creep_analyzer.py
# 하중 조건 입력: 15, 25, 35, 45
# CSV 경로 입력: sample_creep_data.csv
```

## 고급 설정

### 하중 구간 감지 파라미터 조정

```python
analyzer.detect_load_segments(
    strain_jump_threshold=0.01,  # 변형률 급증 임계값 (%)
    time_diff_threshold=5         # 시간 간격 변화 임계값 (배수)
)
```

### 2차 크리프 탐색 파라미터 조정

```python
analyzer.find_secondary_creep_region(
    segment,
    window_size=50,    # Savitzky-Golay 필터 윈도우 크기
    poly_order=3       # 다항식 차수
)
```

## 이론적 배경

### 크리프의 3단계

1. **1차 크리프 (Primary Creep)**
   - 변형률 속도 감소
   - 재료의 가공경화

2. **2차 크리프 (Secondary/Steady-State Creep)**
   - 일정한 변형률 속도
   - 가공경화와 회복의 균형

3. **3차 크리프 (Tertiary Creep)**
   - 변형률 속도 증가
   - 손상 축적, 최종 파괴

### Norton's Law

```
ε̇ = A·σⁿ·exp(-Q/RT)
```

- ε̇: 변형률 속도
- A: 재료 상수
- σ: 응력
- n: 응력지수 (재료의 크리프 특성)
- Q: 활성화 에너지
- R: 기체 상수
- T: 절대 온도

## 문제 해결

### Q: 하중 구간이 제대로 감지되지 않습니다.
A: `strain_jump_threshold`나 `time_diff_threshold` 값을 조정해보세요.

### Q: 2차 크리프 구간을 찾을 수 없다는 오류가 발생합니다.
A: 데이터 포인트가 부족하거나, 각 하중 단계의 지속 시간이 너무 짧을 수 있습니다. `window_size`를 줄여보세요.

### Q: n값이 비정상적으로 나옵니다.
A:
- 하중 조건이 올바르게 입력되었는지 확인하세요.
- 최소 3개 이상의 하중 단계가 필요합니다.
- 각 하중 구간의 R² 값을 확인하여 데이터 품질을 점검하세요.

## 라이센스

MIT License

## 기여

버그 리포트나 기능 제안은 GitHub Issues를 통해 제출해주세요.

## 작성자

Claude Code - Creep Analysis Tool

## 참고 문헌

1. Norton, F.H. (1929). "Creep of Steel at High Temperatures"
2. Kassner, M.E. (2015). "Fundamentals of Creep in Metals and Alloys"
3. Frost, H.J., Ashby, M.F. (1982). "Deformation Mechanism Maps"
