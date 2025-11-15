# Tier 3 고급 기능 구현 계획

## 개요

ML 키워드 학습은 나중으로 미루고, 다음 고급 기능들을 구현합니다:

1. ✅ Reference Parsing (참고문헌 추출 및 파싱)
2. ✅ Citation Matching (인용 매칭)
3. ✅ Citation Network Visualization (인용 네트워크 시각화)
4. ✅ Advanced Search & Filters (고급 검색 및 필터)
5. ✅ Tags & Notes System (태그 및 노트 시스템)

---

## 1. Reference Parsing (참고문헌 추출)

### 목표
PDF에서 References 섹션을 찾아 각 참고문헌을 파싱합니다.

### 구현 내용

#### A. References 섹션 감지
```python
def _find_references_section(full_text: str) -> str:
    """
    PDF 텍스트에서 References 섹션 찾기

    패턴:
    - "References", "REFERENCES", "Bibliography"
    - 보통 논문 끝부분
    - 번호 매겨진 목록
    """
```

#### B. 개별 참고문헌 파싱 (강화)
```python
def parse_reference(ref_text: str) -> dict:
    """
    참고문헌 하나를 파싱

    추출 정보:
    - 제목 (따옴표 안 또는 강조)
    - 저자 (성명 패턴)
    - 연도 (4자리 숫자)
    - 저널/학회 (italic 또는 패턴)
    - DOI (10.xxxx/yyyy 패턴)
    - arXiv ID (arXiv:xxxx.xxxxx)
    """
```

#### C. 데이터베이스 저장
```python
# PaperReferences 테이블에 저장
db.add_reference(
    paper_id=paper_id,
    raw_text=ref_text,
    parsed_title=title,
    parsed_authors=authors,
    parsed_year=year,
    parsed_doi=doi
)
```

### 예상 정확도
- **DOI 있는 경우**: 90-95% (DOI로 정확한 매칭 가능)
- **제목+연도**: 70-80% (유사도 매칭)
- **전체 평균**: 75-85%

---

## 2. Citation Matching (인용 매칭)

### 목표
추출된 참고문헌을 데이터베이스의 다른 논문들과 매칭합니다.

### 매칭 전략 (우선순위)

1. **DOI 매칭** (신뢰도: 100%)
   ```python
   if ref_doi and paper_doi == ref_doi:
       match!
   ```

2. **제목 + 연도 매칭** (신뢰도: 90%)
   ```python
   if ref_year == paper_year and title_similarity > 0.8:
       match!
   ```

3. **저자 + 제목 부분 매칭** (신뢰도: 70%)
   ```python
   if first_author_match and title_words_overlap > 0.6:
       match!
   ```

### 유사도 계산
- Levenshtein distance (편집 거리)
- Jaccard similarity (단어 집합)
- TF-IDF cosine similarity (고급)

### Citations 테이블
```python
db.add_citation(
    citing_paper_id=paper_a_id,    # 인용하는 논문
    cited_paper_id=paper_b_id,      # 인용되는 논문
    confidence=0.95                 # 매칭 신뢰도
)
```

---

## 3. Citation Network Visualization

### 목표
논문 간 인용 관계를 그래프로 시각화합니다.

### 기술 스택
- **NetworkX**: 그래프 생성 및 분석
- **Matplotlib**: 기본 시각화
- **Pyvis** (선택): 인터랙티브 HTML 그래프

### 그래프 구조
```python
import networkx as nx

# 방향 그래프 (A → B: A가 B를 인용)
G = nx.DiGraph()

# 노드: 논문
G.add_node(paper_id, title=title, year=year)

# 엣지: 인용 관계
G.add_edge(citing_id, cited_id, weight=confidence)
```

### 시각화 요소
1. **노드 크기**: 인용 횟수 (많이 인용된 논문 = 큰 노드)
2. **노드 색**: 연도 (gradient)
3. **엣지 굵기**: 신뢰도
4. **레이아웃**: Spring layout, Hierarchical layout

### 분석 기능
```python
# 가장 많이 인용된 논문 (hub)
most_cited = sorted(G.in_degree(), key=lambda x: x[1], reverse=True)

# 가장 많이 인용하는 논문
most_citing = sorted(G.out_degree(), key=lambda x: x[1], reverse=True)

# 중심성 (Centrality)
betweenness = nx.betweenness_centrality(G)
pagerank = nx.pagerank(G)
```

### UI 통합
```python
# main_window.py에 메뉴 추가
view_network_action = QAction("View Citation Network", self)
view_network_action.triggered.connect(self.show_citation_network)

def show_citation_network(self):
    # 새 창으로 시각화 표시
    dialog = CitationNetworkDialog(self.db)
    dialog.exec()
```

---

## 4. Advanced Search & Filters

### 목표
제목/키워드 검색에 다양한 필터를 추가합니다.

### 필터 종류

#### A. 연도 범위
```python
def search_papers(query, year_from=None, year_to=None):
    WHERE title MATCH ?
    AND year BETWEEN ? AND ?
```

#### B. 저널 필터
```python
journal_filter = ["Nature", "Science", "Cell"]
WHERE journal IN (?, ?, ?)
```

#### C. 저자 필터
```python
# JSON 배열에서 검색
WHERE json_extract(authors, '$') LIKE '%Einstein%'
```

#### D. 인용 횟수
```python
# Citations 테이블 JOIN
SELECT Papers.*, COUNT(Citations.id) as citation_count
WHERE citation_count >= min_citations
```

#### E. 태그 필터
```python
WHERE paper_id IN (
    SELECT paper_id FROM PaperTags WHERE tag = ?
)
```

### UI: Advanced Search Dialog
```python
class AdvancedSearchDialog(QDialog):
    """
    고급 검색 대화상자

    필드:
    - 검색어 (제목/키워드)
    - 연도 범위 (from-to)
    - 저널 (드롭다운/검색)
    - 저자 (텍스트)
    - 최소 인용 횟수
    - 태그 (다중 선택)
    """
```

---

## 5. Tags & Notes System

### 목표
사용자가 논문에 태그와 노트를 추가할 수 있습니다.

### 데이터베이스 스키마

#### A. Tags 테이블
```sql
CREATE TABLE IF NOT EXISTS PaperTags (
    id INTEGER PRIMARY KEY,
    paper_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    color TEXT,  -- 태그 색상 (hex)
    created_date INTEGER,
    FOREIGN KEY(paper_id) REFERENCES Papers(id) ON DELETE CASCADE,
    UNIQUE(paper_id, tag)
);

CREATE INDEX idx_tags_paper ON PaperTags(paper_id);
CREATE INDEX idx_tags_tag ON PaperTags(tag);
```

#### B. Notes 필드 (이미 Papers 테이블에 있음)
```sql
-- Papers.notes 필드 활용
UPDATE Papers SET notes = ? WHERE id = ?
```

### UI 기능

#### A. 태그 추가/삭제
```python
# 논문 상세 페이지에 태그 섹션
tag_input = QLineEdit()
add_tag_btn = QPushButton("Add Tag")

# 자동완성 (기존 태그)
completer = QCompleter(existing_tags)
tag_input.setCompleter(completer)

# 태그 표시 (색상 칩)
for tag in paper.tags:
    tag_chip = TagChip(tag, color)
    tag_chip.close_clicked.connect(lambda: remove_tag(tag))
```

#### B. 노트 편집
```python
# 텍스트 에디터
notes_editor = QTextEdit()
notes_editor.setPlainText(paper.notes)

# 저장
save_btn.clicked.connect(lambda:
    db.update_notes(paper_id, notes_editor.toPlainText())
)
```

#### C. 태그 관리 대화상자
```python
class TagManagerDialog(QDialog):
    """
    모든 태그 관리

    기능:
    - 태그 목록 보기
    - 태그 이름 변경
    - 태그 색상 변경
    - 태그 삭제 (확인 메시지)
    - 태그 병합
    """
```

---

## 구현 순서

### Phase 1: Reference Parsing (1-2일)
1. ✅ References 섹션 감지 알고리즘
2. ✅ 강화된 참고문헌 파싱
3. ✅ UI에 "Extract References" 버튼 추가
4. ✅ 진행 상황 표시

### Phase 2: Citation Matching (1일)
1. ✅ 매칭 알고리즘 구현 (DOI, 제목, 저자)
2. ✅ Citations 테이블 채우기
3. ✅ UI에 인용 정보 표시

### Phase 3: Citation Network (2일)
1. ✅ NetworkX 그래프 생성
2. ✅ Matplotlib 시각화
3. ✅ 인터랙티브 기능 (확대/축소)
4. ✅ 분석 통계 표시

### Phase 4: Advanced Search (1일)
1. ✅ 필터 UI 구현
2. ✅ 데이터베이스 쿼리 수정
3. ✅ 결과 표시

### Phase 5: Tags & Notes (1일)
1. ✅ 데이터베이스 스키마 추가
2. ✅ 태그 UI 구현
3. ✅ 노트 에디터 추가
4. ✅ 태그 관리 기능

---

## 기대 효과

### 1. Reference Parsing
- 논문 간 관계 자동 파악
- 수동 입력 불필요
- 연구 흐름 추적 가능

### 2. Citation Network
- 영향력 있는 논문 발견
- 연구 분야 구조 파악
- 관련 논문 추천 가능

### 3. Advanced Search
- 정확한 논문 찾기
- 다중 조건 필터링
- 연구 효율 향상

### 4. Tags & Notes
- 개인화된 관리
- 프로젝트별 분류
- 아이디어 메모

---

## 기술적 과제

### 1. Reference Parsing 정확도
- **문제**: PDF 포맷 다양성
- **해결**: 여러 패턴 시도, 신뢰도 표시

### 2. Citation Matching 성능
- **문제**: 많은 논문 = 느린 매칭
- **해결**: 인덱싱, 후보 제한 (DOI 우선)

### 3. Network 시각화 성능
- **문제**: 100+ 논문 = 복잡한 그래프
- **해결**:
  - 노드 필터링 (연도, 인용 횟수)
  - 부분 그래프 표시
  - WebGL 기반 렌더링 (pyvis)

### 4. UI 복잡도
- **문제**: 너무 많은 기능 = 혼란
- **해결**:
  - 단계별 공개 (progressive disclosure)
  - 기본값 제공
  - 도움말 툴팁

---

## 다음 단계

1. **Phase 1부터 시작**: Reference Parsing 구현
2. **점진적 배포**: 각 Phase 완료 시 커밋
3. **사용자 피드백**: 각 단계마다 테스트

시작할까요?
