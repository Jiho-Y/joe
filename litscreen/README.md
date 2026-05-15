# LitScreen — 학술 문헌 스크리닝 도구

Semantic Scholar API로 수집한 논문 메타데이터(Excel)를 효율적으로 스크리닝하는 Streamlit 기반 도구입니다.

## 설치 및 실행

**요구사항**: Python 3.10+, macOS (또는 Linux/Windows)

```bash
# 의존성 설치
pip install -r requirements.txt

# 실행
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 열림.

## 입력 파일 형식

- 확장자: `.xlsx`
- 시트명: `Papers`
- 필수 컬럼 12개: `Keyword`, `Paper ID`, `DOI`, `Title`, `Authors`, `Year`, `Publication Date`, `Venue`, `Citation Count`, `Abstract`, `URL`, `Chicago Citation`
- `Decision`, `Reason` 컬럼이 이미 있으면 이전 작업을 자동으로 이어갑니다.

## 키보드 단축키

상세 패널이 활성화된 상태에서 (텍스트 입력 필드에 커서가 없을 때):

| 키 | 동작 |
|----|------|
| `K` | Keep으로 태깅 |
| `M` | Maybe로 태깅 |
| `D` | Discard로 태깅 |
| `U` | Undecided로 초기화 |

네비게이션 버튼으로 이전/다음/다음 Undecided 이동도 지원합니다.

## 추천 워크플로우

### 1단계: 업로드 & 1차 일괄 제거 (Batch Filter → Discard)
1. Excel 파일 업로드
2. 사이드바 → 텍스트 필터에서 무관한 키워드 입력 (제외 NONE 모드)
3. 연도 슬라이더, 최소 인용 횟수로 추가 필터링
4. 필터 결과를 전체 선택 → Export → 해당 논문들은 별도 작업 불필요

### 2단계: Title 스캔 (Keep / Maybe / Discard 태깅)
1. 필터를 초기화하거나 "Undecided"만 표시
2. 테이블에서 행 클릭 → 상세 패널에서 Title + 하이라이트 확인
3. `K` / `M` / `D` 로 빠르게 태깅
4. 애매한 논문은 `M`(Maybe)으로 표시하고 넘어가기

### 3단계: Abstract 정독 (Maybe → Keep/Discard)
1. 사이드바 Decision 필터 → "Maybe"만 선택
2. 각 논문 Abstract 정독 후 최종 결정
3. Reason 박스에 선택/제외 이유 기록

### 4단계: Export
- **Excel**: 전체 / 현재 필터 view / Keep만 / Keep+Maybe 선택 export
- **BibTeX**: Keep 논문만 `.bib` 파일로 export
- **Markdown**: Year/Venue/Citation/Keyword별 그룹화된 요약 문서

## 저장 방법

- **수동 저장**: 사이드바 "💾 Save" 클릭 → 상단에 다운로드 버튼 생성
- **자동 저장**: 사이드바 Autosave 토글 ON → N개 태깅마다 자동 저장
- 저장된 파일을 다시 업로드하면 Decision/Reason이 자동 복원됩니다.

## 하이라이트 색상

| 색상 | 의미 |
|------|------|
| 파란 배경 | 해당 논문의 검색 Keyword 출처 단어/phrase |
| 노란 배경 | 사이드바 텍스트 필터에 입력한 키워드 |

## 모듈 구조

```
litscreen/
├── app.py            메인 진입점, 레이아웃 조합
├── state.py          session_state 관리, 파일 로드/저장
├── filters.py        필터 순수 함수
├── highlighting.py   키워드 하이라이트 HTML 생성
├── ui_components.py  UI 컴포넌트 (사이드바, 테이블, 패널, 상태 바)
├── exporters.py      xlsx / BibTeX / Markdown export
├── requirements.txt
└── README.md
```
