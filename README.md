# Semantic Scholar 논문 검색 및 필터링 도구

Mac에서 사용 가능한 GUI 기반 논문 검색 및 필터링 프로그램입니다.

## 기능

### 1. 논문 검색 (Semantic Scholar API)
- 키워드 기반 논문 검색
- 연도 범위 지정 가능
- 검색 결과를 Excel 파일로 저장
- 컬럼 순서: 출판일, 제목, 저자, 저널, 인용수, DOI, 초록

### 2. 논문 필터링
- 키워드 기반 필터링
  - 모두 포함 (AND): 모든 키워드가 포함된 논문만 선택
  - 하나 이상 포함 (OR): 키워드 중 하나라도 포함된 논문 선택
  - 제외 (NOT): 특정 키워드가 포함된 논문 제외
- 연도 범위 필터링
- 인용 수 범위 필터링
- 검색 대상 선택 (제목, 초록, 저자, 저널)
- 대소문자 구분 옵션

## 설치 방법

### 1. 필수 요구사항
- Python 3.8 이상
- tkinter (Python 기본 내장, Mac에서는 기본 제공)

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

## 사용 방법

### 프로그램 실행
```bash
python paper_search_filter.py
```

### 1. 논문 검색 탭
1. 검색 키워드 입력 (예: "machine learning")
2. 결과 개수 설정 (기본값: 100)
3. (선택) 연도 범위 설정
4. 저장 경로 선택 (찾아보기 버튼 클릭)
5. "검색 시작" 버튼 클릭
6. 진행 상황 확인 후 완료 대기

### 2. 논문 필터링 탭
1. "찾아보기" 버튼으로 Excel/CSV 파일 선택
2. "파일 로드" 버튼 클릭
3. 필터 조건 설정:
   - 검색 대상 선택 (Title, Abstract, Authors, Journal)
   - 키워드 입력 (쉼표로 구분)
   - 연도 범위, 인용 수 범위 설정
4. "필터링 실행" 버튼 클릭
5. 결과 확인 후 "결과 저장" 버튼으로 저장

## 필터링 예시

### 예시 1: 특정 키워드 포함 논문 찾기
- 하나 이상 포함 (OR): `hastelloy, c276`
- 결과: "hastelloy" 또는 "c276"이 포함된 논문

### 예시 2: 복합 조건 필터링
- 모두 포함 (AND): `additive manufacturing, metal`
- 제외 (NOT): `polymer, plastic`
- 연도 범위: 2020 ~ 2024
- 결과: "additive manufacturing"과 "metal"이 모두 포함되고, "polymer"나 "plastic"은 포함되지 않은 2020-2024년 논문

### 예시 3: 인용 수 기반 필터링
- 하나 이상 포함 (OR): `deep learning`
- 최소 인용 수: 100
- 결과: "deep learning"이 포함되고 인용 수가 100 이상인 논문

## 저장 형식

검색 및 필터링 결과는 다음 컬럼 순서로 저장됩니다:
1. Publication Date (출판일)
2. Title (제목)
3. Authors (저자)
4. Journal (저널)
5. Citation Count (인용수)
6. DOI
7. Abstract (초록)

## 주의사항

- Semantic Scholar API는 rate limit이 있어 대량 검색 시 시간이 걸릴 수 있습니다
- 검색 중에는 프로그램이 응답하지 않을 수 있으나, 백그라운드에서 정상 작동 중입니다
- 인터넷 연결이 필요합니다 (검색 기능)

## 문제 해결

### Mac에서 tkinter가 없다는 오류
```bash
# Homebrew를 통한 Python 재설치
brew install python-tk@3.11
```

### openpyxl 관련 오류
```bash
pip install --upgrade openpyxl
```

## 라이선스
MIT License