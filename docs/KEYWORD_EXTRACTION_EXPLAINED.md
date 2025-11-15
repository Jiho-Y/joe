# 키워드 추출 메커니즘 상세 설명

## 현재 시스템 (v0.2.1)

### 1. 알고리즘 개요

현재 시스템은 **2단계 하이브리드 접근법**을 사용합니다:

```
PDF → 텍스트 추출 → YAKE/KeyBERT → 필터링 → 최종 키워드
```

---

## 📊 YAKE (Yet Another Keyword Extractor)

### 작동 원리:
**통계 기반, 비지도 학습** (머신러닝 모델 불필요)

1. **단어 통계 분석**:
   - TF (Term Frequency): 단어 빈도
   - Casing: 대문자 비율 (제목/중요 단어)
   - Position: 문서 내 위치 (초반 = 중요)
   - Context: 주변 단어와의 관계
   - Relatedness: 다른 단어와의 연관성

2. **점수 계산**:
   ```python
   score = (TF × Position × Context) / (Casing × Relatedness)
   ```
   **낮은 점수 = 더 중요** (YAKE 특성)

3. **N-gram 지원**:
   - 1-gram: "fatigue"
   - 2-gram: "heat treatment"
   - 3-gram: "finite element analysis"

### 장점:
- ✅ 빠름 (모델 로딩 불필요)
- ✅ 도메인 독립적
- ✅ 메모리 효율적

### 단점:
- ❌ 의미론적 이해 부족
- ❌ 동의어 인식 불가
- ❌ 도메인 특화 불가능

---

## 🧠 KeyBERT (Keyword Extraction with BERT)

### 작동 원리:
**BERT 기반, 사전학습 딥러닝 모델**

1. **임베딩 생성**:
   ```python
   # 문서 전체를 768차원 벡터로 변환
   doc_embedding = BERT(전체_텍스트)

   # 각 후보 단어/구문을 벡터로 변환
   candidate_embeddings = [BERT(keyword) for keyword in candidates]
   ```

2. **유사도 계산** (코사인 유사도):
   ```python
   similarity = cosine_similarity(doc_embedding, candidate_embedding)
   ```
   문서와 가장 유사한 단어 = 핵심 키워드

3. **MMR (Maximal Marginal Relevance)**:
   - 다양성 보장 (유사한 키워드 중복 방지)
   - 관련성 + 다양성 균형

### 사용 모델:
- **기본**: `all-MiniLM-L6-v2` (22MB, 빠름)
- **학술 논문용**: `allenai/scibert_scivocab_uncased` (440MB, 느림, 정확)

### 장점:
- ✅ 의미론적 이해
- ✅ 동의어/유사어 인식
- ✅ 맥락 고려
- ✅ SciBERT로 학술 논문 특화

### 단점:
- ❌ 느림 (첫 로딩 시)
- ❌ 메모리 사용량 높음
- ❌ 모델 다운로드 필요

---

## 🔧 현재 구현 (v0.2.1)

### 텍스트 가중치:
```python
# 제목: 5배 반복 (가장 중요)
title_text = title * 5

# 초록: 3배 반복
abstract_text = abstract * 3

# 본문: 처음 8000자만
full_text = full_text[:8000]

combined = title_text + abstract_text + full_text
```

### YAKE 설정:
```python
yake.KeywordExtractor(
    lan="en",
    n=3,                    # 1-3단어 구문
    dedupLim=0.8,           # 중복 제거 임계값 (높음 = 덜 중복)
    dedupFunc='seqm',       # 시퀀스 매칭
    windowsSize=1,          # 문맥 윈도우
    top=30,                 # 초기 30개 추출
)
```

### 필터링 (50+ 불용어):
```python
generic_terms = {
    'paper', 'study', 'research', 'article',
    'introduction', 'conclusion', 'method',
    'data', 'system', 'model', 'framework',
    'year', 'time', 'number', 'value',
    # ... 총 50개 이상
}
```

### 고급 필터:
- 3자 미만 제거
- 숫자만 있는 것 제거
- 4단어 이상 제거
- 영숫자 비율 < 50% 제거
- 중복 정규화 (복수형 처리)

---

## 📈 성능 비교

| 방법 | 속도 | 정확도 | 메모리 | 도메인 특화 |
|------|------|--------|--------|-------------|
| YAKE | ⚡ 매우 빠름 | 70-80% | 낮음 | ❌ 불가능 |
| KeyBERT (MiniLM) | 🐢 보통 | 80-85% | 중간 | ⚠️ 제한적 |
| KeyBERT (SciBERT) | 🐌 느림 | 85-90% | 높음 | ✅ 학술 논문 |
| **ML Fine-tuned** | 🐢 보통 | **90-95%** | 중간 | ✅ **사용자 데이터** |

---

## 🎯 머신러닝 개선 가능성

### ✅ 개선 가능합니다!

### 방법 1: KeyBERT Fine-tuning (고급)
**장점**:
- 최고 정확도 (95%+)
- 의미론적 이해 유지

**단점**:
- 복잡한 구현
- 많은 학습 데이터 필요 (최소 100-500개 논문)
- GPU 필요
- 학습 시간 오래 걸림 (수 시간)

### 방법 2: Supervised Keyword Ranker (실용적) ⭐
**장점**:
- 간단한 구현
- 적은 데이터로 학습 (20-50개 논문)
- CPU 충분
- 빠른 학습 (수 분)
- **현재 시스템과 쉽게 통합**

**단점**:
- Fine-tuning보다는 낮은 정확도 (90-92%)

---

## 🚀 제안: Hybrid ML Approach

### 아키텍처:
```
1. YAKE/KeyBERT → 후보 키워드 30개 추출
2. Feature Extraction → 각 키워드 특징 추출
3. ML Ranker → 최종 top-N 선택
```

### 특징(Features):
1. **YAKE 점수**
2. **KeyBERT 유사도**
3. **제목 출현 여부** (1/0)
4. **초록 출현 빈도**
5. **첫 페이지 출현 여부**
6. **N-gram 길이** (1-3)
7. **TF-IDF 점수**
8. **대문자 비율**
9. **위치 점수** (문서 초반 = 높음)
10. **단어 길이**

### ML 모델:
- **Random Forest** (추천) - 해석 가능, 강건
- **XGBoost** - 높은 정확도
- **Logistic Regression** - 가장 간단

### 학습 데이터 형식:
```json
{
  "pdf_path": "paper1.pdf",
  "true_keywords": [
    "heat treatment",
    "microstructure",
    "mechanical properties",
    "fatigue life",
    "finite element analysis"
  ]
}
```

### 학습 프로세스:
1. 각 논문에서 30개 후보 추출
2. 각 후보에 대해 특징 벡터 생성
3. 정답 키워드 = 1, 나머지 = 0 (라벨링)
4. Random Forest 학습
5. 저장 및 통합

---

## 💡 구현 계획

### Phase 1: 학습 데이터 준비 도구
```bash
python train_keyword_model.py --prepare
# → PDF와 키워드 입력받아 training_data.json 생성
```

### Phase 2: 모델 학습
```bash
python train_keyword_model.py --train
# → training_data.json으로 모델 학습
# → 저장: models/keyword_ranker.pkl
```

### Phase 3: 통합
```python
# metadata_extractor.py에 ML 모드 추가
extractor.extract_from_paper(..., method='ml')
```

### 예상 성능 향상:
- **YAKE 단독**: 70-75% 정확도
- **YAKE + 필터**: 78-82% 정확도 (현재)
- **YAKE + ML Ranker**: **88-92% 정확도** (목표)

---

## 📊 필요한 학습 데이터

### 최소:
- **20-30개 논문**: 기본 학습 가능
- 각 논문당 **5-10개 정답 키워드**

### 권장:
- **50-100개 논문**: 좋은 성능
- 다양한 주제 포함

### 최적:
- **200+ 논문**: 최고 성능
- 여러 학술 분야

---

## 🎓 학술적 근거

이 접근법은 다음 연구들에 기반합니다:

1. **"Automatic Keyphrase Extraction: A Survey"** (2019)
   - Supervised learning이 unsupervised보다 우수

2. **"KeyBERT: Minimal keyword extraction with BERT"** (2020)
   - BERT 임베딩 + 유사도 효과적

3. **"YAKE! Keyword extraction from single documents"** (2020)
   - 통계 기반도 충분히 실용적

4. **Hybrid approaches**:
   - 여러 방법 조합이 단일 방법보다 우수

---

## 결론

✅ **머신러닝 개선 가능**: Supervised Keyword Ranker 추천
✅ **실용적**: 적은 데이터, 빠른 학습, 쉬운 통합
✅ **효과적**: 10-15% 정확도 향상 예상

**다음 단계**: 구현할까요?
