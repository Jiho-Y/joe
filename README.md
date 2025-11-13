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
1. (선택) API Key 입력 - 더 높은 rate limit을 위해 권장
2. 검색 키워드 입력 (예: "machine learning")
3. 결과 개수 설정 (기본값: 100)
4. (선택) 연도 범위 설정
5. 저장 경로 선택 (찾아보기 버튼 클릭)
6. "검색 시작" 버튼 클릭
7. 진행 상황 확인 후 완료 대기

### 2. 논문 필터링 탭
1. "찾아보기" 버튼으로 Excel/CSV 파일 선택
2. "파일 로드" 버튼 클릭
3. 필터 조건 설정:
   - 검색 대상 선택 (Title, Abstract, Authors, Journal)
   - 키워드 입력 (쉼표로 구분)
   - 연도 범위, 인용 수 범위 설정
4. "필터링 실행" 버튼 클릭
5. 결과 확인 후 "결과 저장" 버튼으로 저장

## Semantic Scholar API Key 얻기 (선택사항)

API 키를 사용하면 더 높은 rate limit을 받을 수 있어 대량 검색 시 유리합니다.

### API Key 발급 방법
1. [Semantic Scholar API](https://www.semanticscholar.org/product/api) 페이지 방문
2. "Get API Key" 또는 "Sign Up" 클릭
3. 계정 생성 또는 로그인
4. API Key 발급 받기
5. 프로그램의 "API Key" 필드에 입력

### API Key 사용 시 장점
- 더 높은 rate limit (분당 요청 수 증가)
- 안정적인 대량 검색 가능
- API 사용량 모니터링 가능

**참고**: API Key 없이도 프로그램 사용은 가능하지만, 기본 rate limit이 적용됩니다.

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
8. Paper ID (Semantic Scholar 고유 ID)
9. URL (논문 링크)

## 주요 개선 사항

### 견고한 에러 처리
- **지수 백오프 (Exponential Backoff)**: 네트워크 오류 시 점진적으로 대기 시간 증가
- **최대 10회 재시도**: 일시적 오류에 대한 자동 재시도
- **Rate Limit 처리**: API 429 에러 발생 시 자동 대기 후 재시도
- **타임아웃 관리**: 5분 타임아웃 설정으로 무한 대기 방지

### Pagination 지원
- **100개 이상 검색 가능**: API 제한을 우회하여 대량 논문 검색
- **배치 단위 진행 표시**: 각 100개 배치별로 진행 상황 표시
- **자동 rate limit 준수**: API 키 없을 시 배치 간 1.2초 대기

### 중복 제거
- **DOI 기반 중복 제거**: DOI를 우선으로 중복 논문 자동 제거
- **Paper ID 백업**: DOI 없는 논문은 Paper ID로 중복 확인
- **통계 제공**: 제거된 중복 논문 수 표시

### 상세한 로그
- 검색 진행 상황 실시간 표시
- 배치별 수집 통계
- 오류 발생 시 상세한 정보 제공

## 주의사항

- Semantic Scholar API는 rate limit이 있어 대량 검색 시 시간이 걸릴 수 있습니다
- API 키 사용 시 더 빠른 검색이 가능합니다
- 검색 중 네트워크 오류가 발생해도 자동으로 재시도됩니다
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