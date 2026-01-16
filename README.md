# Semantic Scholar 논문 검색 도구 v3.0

Semantic Scholar API를 활용하여 학술 논문을 대량으로 검색하고 엑셀 파일로 저장하는 도구입니다.

## 주요 기능

### v3.0 업데이트 내용

1. **기존 엑셀 파일에 데이터 추가**
   - 기존 엑셀 파일을 불러와서 새로운 검색 결과를 추가할 수 있습니다
   - DOI 및 Paper ID 기준으로 중복을 자동 제거합니다

2. **유연한 키워드 입력**
   - 고정된 4개 키워드에서 벗어나 원하는 만큼 키워드를 입력할 수 있습니다
   - 키워드 개수를 미리 지정하거나, 하나씩 추가하면서 입력할 수 있습니다

3. **GUI 버전 제공**
   - tkinter 기반의 사용자 친화적인 그래픽 인터페이스
   - 실시간 진행 상황 모니터링
   - 로그 출력 및 작업 취소 기능

### 기존 기능

- Pagination을 통한 대량 논문 검색 (키워드당 최대 1000개)
- 강력한 재시도 메커니즘 (지수 백오프)
- DOI 및 Paper ID 기준 중복 제거
- 상세한 진행 상황 표시 및 오류 처리
- 엑셀 파일 자동 포맷팅

## 🚀 빠른 시작 (터미널 사용 없이!)

### 가장 쉬운 방법 - 3단계로 완료

1. **GitHub에서 ZIP 다운로드**
   - https://github.com/Jiho-Y/joe 접속
   - 브랜치: `claude/semantic-scholar-search-011CUQ5xnUkRVMHJH2FAaWqN` 선택
   - Code 버튼 → Download ZIP
   - 압축 해제

2. **패키지 설치 (최초 1회만)**
   - Windows: `install_packages.bat` 더블클릭
   - Mac/Linux: `install_packages.sh` 더블클릭

3. **프로그램 실행**
   - GUI 버전 (추천): `run_gui.bat` (또는 `run_gui.sh`) 더블클릭
   - CLI 버전: `run_cli.bat` (또는 `run_cli.sh`) 더블클릭

**그게 다입니다!** 이제 터미널 없이 더블클릭만으로 사용할 수 있습니다. 🎉

> 💡 바탕화면에 바로가기를 만들면 더욱 편리합니다!

### 다운로드 후 파일 구조
```
joe/
├── 실행 파일 (더블클릭!)
│   ├── run_gui.bat / run_gui.sh           ← GUI 버전 실행
│   ├── run_cli.bat / run_cli.sh           ← CLI 버전 실행
│   └── install_packages.bat / .sh         ← 패키지 설치
│
├── 프로그램 파일
│   ├── semantic_scholar_search_gui.py     ← GUI 프로그램
│   ├── semantic_scholar_search.py         ← CLI 프로그램
│   └── requirements.txt                   ← 필요한 패키지
│
└── 문서
    ├── README.md                          ← 이 파일
    └── 사용방법.txt                       ← 간단한 사용 가이드
```

---

## 설치 방법 (수동)

### 1. Python 요구사항
- Python 3.7 이상
- Python 설치 시 "Add Python to PATH" 체크 필수!

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

또는 개별 설치:

```bash
pip install requests pandas openpyxl
```

## 사용 방법

### CLI 버전 (명령줄 인터페이스)

```bash
python semantic_scholar_search.py
```

#### 실행 과정

1. **작업 모드 선택**
   - 새로운 검색: 새 엑셀 파일 생성
   - 기존 파일에 추가: 기존 엑셀 파일에 검색 결과 추가 (중복 제거)

2. **키워드 입력 방식 선택**
   - 방식 1: 키워드 개수를 미리 지정하고 입력
   - 방식 2: 하나씩 입력하면서 추가 여부 선택

3. **키워드 입력**
   - 검색할 키워드를 순서대로 입력
   - 예: `waam hastelloy`, `inconel 718`, `additive manufacturing`

4. **검색 진행**
   - 각 키워드별로 자동 검색
   - 진행 상황 실시간 표시
   - 네트워크 오류 시 자동 재시도

5. **결과 저장**
   - 중복 제거 후 엑셀 파일로 저장
   - 파일명: `semantic_scholar_results_YYYYMMDD_HHMMSS.xlsx` (새 파일)
   - 또는 선택한 기존 파일에 덮어쓰기

### GUI 버전 (그래픽 인터페이스)

```bash
python semantic_scholar_search_gui.py
```

#### GUI 사용법

1. **API 설정**
   - API 키 입력 (선택사항)
   - 미입력 시 Rate Limit 적용 (요청 간 1.2초 대기)

2. **작업 모드 선택**
   - 라디오 버튼으로 새로운 검색 또는 기존 파일에 추가 선택
   - 기존 파일 선택 시 "찾아보기" 버튼으로 파일 선택

3. **키워드 입력**
   - 텍스트 필드에 키워드 입력 후 "추가" 버튼 클릭
   - Enter 키로도 추가 가능
   - 리스트에서 선택 후 "제거" 버튼으로 삭제 가능

4. **검색 옵션**
   - 최대 결과 수 설정 (기본값: 1000)

5. **검색 시작**
   - "검색 시작" 버튼 클릭
   - 진행 상황이 프로그레스 바와 로그 창에 표시됨
   - "중지" 버튼으로 언제든 중단 가능

6. **결과 확인**
   - 검색 완료 후 파일 열기 선택 가능
   - 로그에서 상세 결과 확인

## API 키 설정 (선택사항)

Semantic Scholar API 키가 있으면 Rate Limit 제한을 완화할 수 있습니다.

### CLI 버전
파일 상단의 `API_KEY` 변수에 키 입력:

```python
API_KEY = "your-api-key-here"
```

### GUI 버전
프로그램 실행 후 "API 설정" 섹션에 입력

### API 키 발급
1. [Semantic Scholar API](https://www.semanticscholar.org/product/api) 페이지 방문
2. API 키 신청

## 출력 데이터 형식

엑셀 파일에 다음 정보가 저장됩니다:

| 컬럼명 | 설명 |
|--------|------|
| Keyword | 검색에 사용된 키워드 |
| Paper ID | Semantic Scholar 논문 ID |
| DOI | 논문 DOI |
| Title | 논문 제목 |
| Authors | 저자 목록 (쉼표로 구분) |
| Year | 출판 연도 |
| Publication Date | 출판 날짜 |
| Venue | 출판 장소/학회 |
| Citation Count | 인용 횟수 |
| Abstract | 초록 |
| URL | Semantic Scholar 논문 URL |

## 중복 제거 방식

1. **DOI가 있는 논문**: DOI를 기준으로 중복 제거
2. **DOI가 없는 논문**: Paper ID를 기준으로 중복 제거
3. 먼저 발견된 논문을 유지하고 나중 것은 제거

## 주요 개선 사항 요약

### 1. 기존 파일 추가 기능
```
기존 파일 (100개) + 새 검색 (150개) = 병합 (250개)
                                        ↓
                                  중복 제거 (200개)
```

### 2. 유연한 키워드 입력
- **이전**: 무조건 4개 키워드 입력
- **현재**: 1개부터 원하는 만큼 입력 가능

### 3. GUI 제공
- **CLI**: 명령줄 기반, 스크립트 실행
- **GUI**: 그래픽 인터페이스, 직관적 조작

## 재시도 메커니즘

네트워크 오류나 서버 오류 시 자동으로 재시도합니다:

- **최대 재시도**: 10회
- **대기 방식**: 지수 백오프 (Exponential Backoff)
- **최대 대기 시간**: 1048초 (약 17.5분)

## 주의사항

1. **Rate Limit**
   - API 키 없이 사용 시 요청 간 1.2초 대기
   - 대량 검색 시 시간이 오래 걸릴 수 있음

2. **파일 저장**
   - 엑셀 파일이 열려 있으면 저장 실패
   - 충분한 디스크 공간 필요

3. **중단**
   - CLI: `Ctrl+C`로 중단
   - GUI: "중지" 버튼 클릭

4. **기존 파일 덮어쓰기**
   - "기존 파일에 추가" 모드는 원본 파일을 덮어씀
   - 중요한 파일은 미리 백업 권장

## 문제 해결

### 네트워크 오류
- 안정적인 인터넷 연결 확인
- 프록시 설정 확인

### Rate Limit 초과
- API 키 사용 권장
- 또는 검색 간 대기 시간 증가

### 파일 저장 실패
- 엑셀 파일이 다른 프로그램에서 열려 있는지 확인
- 파일 쓰기 권한 확인

### GUI 실행 오류 (Linux)
```bash
sudo apt-get install python3-tk
```

## 라이선스

MIT License

## 기여

이슈나 개선 사항은 GitHub Issues를 통해 제안해주세요.

## 변경 이력

### v3.0 (2025-10-23)
- 기존 엑셀 파일에 데이터 추가 기능
- 유연한 키워드 입력 시스템
- GUI 버전 추가

### v2.0
- Pagination 지원
- 강력한 재시도 메커니즘
- DOI 중복 제거

### v1.0
- 초기 버전
- 기본 검색 기능
