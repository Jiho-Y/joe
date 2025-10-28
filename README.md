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

### 1. GUI 버전 (권장) 🎨

```bash
python3 creep_analyzer_gui.py
```

**특징:**
- 직관적인 그래픽 사용자 인터페이스
- 3개 탭 (메인/고급 설정/결과)
- 실시간 진행 상황 표시
- 고급 파라미터 직접 조정 가능
- 결과 그래프 실시간 표시
- CSV 및 그래프 내보내기

**사용 순서:**
1. **메인 탭**: 하중 조건, CSV 파일, 초기 안정화 시간, 하중 간격 입력
2. **고급 설정 탭** (선택사항): 알고리즘 민감도 파라미터 조정
3. **분석 시작** 버튼 클릭
4. **결과 탭**: 분석 결과 및 그래프 확인

### 2. 명령줄 버전 (대화형 모드)

```bash
python3 creep_analyzer.py
```

프로그램 실행 후 다음 정보를 입력:
1. 다단계 하중 조건 (쉼표로 구분, 예: `15, 25, 35, 45`)
2. 초기 안정화 시간 (시간, 기본값: 48시간)
3. 하중 간격 (시간, 기본값: 24시간)
4. CSV 파일 경로

### 3. Python 스크립트에서 사용

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

### 하중 구간 감지 (개선된 알고리즘)

**시간 기반 윈도우 탐색 방식**으로 하중 증가 지점을 정확하게 감지합니다:

1. **예상 시점 계산**
   - 하중 간격(기본 24시간)을 기준으로 예상 전환 시점 계산
   - 예: 24시간, 48시간, 72시간, ...

2. **탐색 윈도우 설정**
   - 각 예상 시점 ±1시간 범위 내에서 탐색
   - 예: 23~25시간, 47~49시간, ...
   - 과민 반응 방지: 특정 시간대만 집중 탐색

3. **2차 미분(변형률 가속도) 분석**
   - 변형률 → 변형률 속도 → 변형률 가속도 계산
   - 하중 증가 시 가속도가 급증
   - 미분 기반 평가로 정확도 향상

4. **최대 가속도 지점 선택**
   - 탐색 윈도우 내에서 가속도가 최대인 지점 선택
   - 임계값 이상의 후보 중 최대값 선택

5. **중복 제거**
   - 이전 전환점과 충분히 떨어진 지점만 선택
   - 최소 간격: 100개 데이터 포인트

**장점:**
- ✓ 64개 오감지 → 정확한 구간 감지
- ✓ 시간 기반 탐색으로 과민 반응 제거
- ✓ 미분 기반 평가로 정확도 향상
- ✓ 사용자 정의 하중 간격 지원

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
# 하중 간격 입력: 2.78 (샘플 데이터는 2.78시간 간격)
# CSV 경로 입력: sample_creep_data.csv
```

## 고급 설정

### 하중 구간 감지 파라미터 조정 (개선된 알고리즘)

```python
analyzer.detect_load_segments(
    initial_stabilization_hours=48,   # 초기 안정화 시간 (시간)
    load_interval_hours=24,           # 하중 증가 시간 간격 (시간)
    search_window_hours=0.5,          # 탐색 윈도우 크기 (±시간)
    use_derivative=True,              # 2차 미분 사용 여부
    min_strain_acceleration=1e-7      # 최소 변형률 가속도 임계값 (%/s²)
)
```

**파라미터 설명:**
- `initial_stabilization_hours`: 첫 번째 하중 증가 전 안정화 시간 (예: 48시간)
- `load_interval_hours`: 이후 하중이 증가하는 시간 간격 (예: 24시간)
- `search_window_hours`: 각 예상 시점에서 탐색할 범위 (예: ±0.5시간, 총 1시간)
- `use_derivative`: True면 2차 미분(가속도) 사용, False면 1차 미분(속도) 사용
- `min_strain_acceleration`: 하중 전환으로 인정할 최소 가속도 값

**💡 GUI 버전에서는 "고급 설정" 탭에서 이러한 파라미터를 직접 조정할 수 있습니다!**

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

### Q: 하중 구간이 너무 많이(또는 적게) 감지됩니다.
A:
- **너무 많이 감지되는 경우**: `load_interval_hours` 값을 실제 시험 조건에 맞게 설정하세요 (예: 24시간)
- **너무 적게 감지되는 경우**:
  - `search_window_hours`를 늘려보세요 (예: 1.0 → 2.0)
  - `min_strain_acceleration`을 낮춰보세요 (예: 1e-7 → 1e-8)
- **간격이 일정하지 않은 경우**: 각 전환 시점을 수동으로 확인하여 간격을 조정하세요

### Q: 64개 구간이 감지되었는데 실제는 6개입니다.
A: 이것이 바로 개선된 알고리즘이 해결한 문제입니다!
- `load_interval_hours` 파라미터를 사용하여 예상 하중 증가 시간을 지정하세요
- 시간 기반 윈도우 탐색으로 과민 반응을 제거했습니다
- 예: `analyzer.detect_load_segments(load_interval_hours=24)`

### Q: 2차 크리프 구간을 찾을 수 없다는 오류가 발생합니다.
A: 데이터 포인트가 부족하거나, 각 하중 단계의 지속 시간이 너무 짧을 수 있습니다. `window_size`를 줄여보세요.

### Q: n값이 비정상적으로 나옵니다.
A:
- 하중 조건이 올바르게 입력되었는지 확인하세요.
- 하중 간격(`load_interval_hours`)이 실제 시험과 일치하는지 확인하세요.
- 최소 3개 이상의 하중 단계가 필요합니다.
- 각 하중 구간의 R² 값을 확인하여 데이터 품질을 점검하세요.

### Q: "divide by zero" 경고가 발생합니다.
A: 이 문제는 최신 버전에서 수정되었습니다. 시간 간격이 0인 경우 자동으로 처리됩니다.

### Q: GUI 버전과 명령줄 버전의 차이는 무엇인가요?
A:
- **GUI 버전 (creep_analyzer_gui.py)**:
  - 그래픽 인터페이스로 사용하기 쉬움
  - 고급 파라미터 실시간 조정 가능
  - 결과 그래프 즉시 확인
  - 권장 방법
- **명령줄 버전 (creep_analyzer.py)**:
  - 터미널에서 실행
  - 자동화 스크립트에 적합
  - 서버 환경에서 사용 가능

## 스크린샷

### GUI 메인 화면
GUI 버전은 3개의 탭으로 구성되어 있습니다:
1. **메인 탭**: 기본 입력 파라미터 설정
2. **고급 설정 탭**: 알고리즘 민감도 파라미터 조정
3. **결과 탭**: 분석 결과 및 그래프 표시

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
