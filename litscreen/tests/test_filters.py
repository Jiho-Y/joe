"""filters.py 테스트 — 텍스트/수치/메타 필터."""

import io
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from filters import apply_all_filters, get_unique_keywords, get_year_range
from state import load_excel

SAMPLE_PATH = Path("/root/.claude/uploads/81ff8d91-5a3d-4197-bece-363cc2d2eb9d/9cc2082b-IN625_corrosion_Tier1.xlsx")


@pytest.fixture
def df():
    loaded, _ = load_excel(io.BytesIO(SAMPLE_PATH.read_bytes()))
    return loaded


def _fs(**kwargs) -> dict:
    """기본 필터 상태에 kwargs 오버라이드."""
    base = {
        "search_text": "",
        "search_columns": ["Title", "Abstract"],
        "match_mode": "포함 (OR)",
        "case_sensitive": False,
        "word_boundary": False,
        "year_min": None,
        "year_max": None,
        "include_no_year": True,
        "citation_min": 0,
        "decisions_filter": ["Undecided", "Keep", "Maybe", "Discard"],
        "keywords_filter": [],
        "abstract_only": False,
        "doi_only": False,
    }
    base.update(kwargs)
    return base


# ── 텍스트 필터 ────────────────────────────────

class TestTextFilter:
    def test_no_filter_returns_all(self, df):
        result = apply_all_filters(df, _fs(), {})
        assert len(result) == 16

    def test_or_filter_finds_matching_rows(self, df):
        result = apply_all_filters(df, _fs(search_text="oxidation"), {})
        assert len(result) >= 1
        assert all("oxidation" in t.lower() or "oxidation" in a.lower()
                   for t, a in zip(result["Title"], result["Abstract"]))

    def test_and_filter_requires_all_terms(self, df):
        # "corrosion" AND "heat treatment" — 두 단어 모두 포함된 논문만
        result_and = apply_all_filters(
            df, _fs(search_text="corrosion, heat treatment", match_mode="포함 (AND)"), {}
        )
        result_or = apply_all_filters(
            df, _fs(search_text="corrosion, heat treatment", match_mode="포함 (OR)"), {}
        )
        assert len(result_and) <= len(result_or)

    def test_none_filter_excludes_matching(self, df):
        # "oxidation" 제외 → oxidation 포함 행이 없어야 함
        result = apply_all_filters(
            df, _fs(search_text="oxidation", match_mode="제외 (NONE)"), {}
        )
        for t in result["Title"]:
            assert "oxidation" not in t.lower()

    def test_case_insensitive_default(self, df):
        lower = apply_all_filters(df, _fs(search_text="inconel"), {})
        upper = apply_all_filters(df, _fs(search_text="INCONEL"), {})
        assert len(lower) == len(upper)

    def test_case_sensitive_distinguishes(self, df):
        lower = apply_all_filters(df, _fs(search_text="inconel", case_sensitive=True), {})
        upper = apply_all_filters(df, _fs(search_text="INCONEL", case_sensitive=True), {})
        # "Inconel"(대문자 I)이 있으므로 소문자 inconel 은 더 적어야 함
        assert len(lower) <= len(upper)

    def test_word_boundary_prevents_partial_match(self, df):
        # "AM" → word_boundary=True 면 "WAAM" 안의 AM에 매칭 안 됨
        without_boundary = apply_all_filters(
            df, _fs(search_text="AM", word_boundary=False), {}
        )
        with_boundary = apply_all_filters(
            df, _fs(search_text="AM", word_boundary=True), {}
        )
        assert len(with_boundary) <= len(without_boundary)

    def test_multiterm_comma_split(self, df):
        result = apply_all_filters(
            df, _fs(search_text="oxidation, friction"), {}
        )
        assert len(result) >= 2

    def test_multiterm_newline_split(self, df):
        result = apply_all_filters(
            df, _fs(search_text="oxidation\nfriction"), {}
        )
        assert len(result) >= 2

    def test_empty_search_after_strip(self, df):
        result = apply_all_filters(df, _fs(search_text="   "), {})
        assert len(result) == 16

    def test_search_in_title_only(self, df):
        # Abstract 컬럼에만 있는 단어를 Title만 검색하면 0개
        result_title = apply_all_filters(
            df, _fs(search_text="Inconel", search_columns=["Title"]), {}
        )
        result_abstract = apply_all_filters(
            df, _fs(search_text="Inconel", search_columns=["Abstract"]), {}
        )
        # Title에는 거의 다 있으므로 >=1, Abstract도 마찬가지
        assert len(result_title) >= 1
        assert len(result_abstract) >= 1


# ── 수치 필터 ──────────────────────────────────

class TestNumericFilter:
    def test_year_min_filter(self, df):
        result = apply_all_filters(df, _fs(year_min=2023, year_max=2026), {})
        valid = result["Year"].dropna()
        assert (valid >= 2023).all()

    def test_year_max_filter(self, df):
        result = apply_all_filters(df, _fs(year_min=2019, year_max=2022), {})
        valid = result["Year"].dropna()
        assert (valid <= 2022).all()

    def test_year_range_2021_2023(self, df):
        result = apply_all_filters(df, _fs(year_min=2021, year_max=2023), {})
        valid = result["Year"].dropna()
        assert ((valid >= 2021) & (valid <= 2023)).all()

    def test_citation_min_filter(self, df):
        result = apply_all_filters(df, _fs(citation_min=20), {})
        assert (result["Citation Count"] >= 20).all()

    def test_citation_min_zero_returns_all(self, df):
        result = apply_all_filters(df, _fs(citation_min=0), {})
        assert len(result) == 16

    def test_citation_min_very_high_returns_empty(self, df):
        result = apply_all_filters(df, _fs(citation_min=9999), {})
        assert len(result) == 0

    def test_get_year_range(self, df):
        ymin, ymax = get_year_range(df)
        assert ymin == 2019
        assert ymax == 2026


# ── 메타 필터 ──────────────────────────────────

class TestMetaFilter:
    def test_decision_filter_keep_only(self, df):
        # Keep으로 태깅된 논문만
        decisions = {str(df.iloc[0]["Paper ID"]): {"decision": "Keep", "reason": ""}}
        result = apply_all_filters(df, _fs(decisions_filter=["Keep"]), decisions)
        assert len(result) == 1
        assert result.iloc[0]["Decision"] == "Keep"

    def test_decision_filter_undecided_only(self, df):
        decisions = {str(df.iloc[0]["Paper ID"]): {"decision": "Keep", "reason": ""}}
        result = apply_all_filters(df, _fs(decisions_filter=["Undecided"]), decisions)
        assert len(result) == 15

    def test_decision_filter_all_shows_all(self, df):
        result = apply_all_filters(
            df, _fs(decisions_filter=["Undecided", "Keep", "Maybe", "Discard"]), {}
        )
        assert len(result) == 16

    def test_keyword_filter_single(self, df):
        unique_kws = get_unique_keywords(df)
        result = apply_all_filters(df, _fs(keywords_filter=[unique_kws[0]]), {})
        assert all(row == unique_kws[0] for row in result["Keyword"])

    def test_abstract_only_toggle(self, df):
        # 샘플 데이터에는 abstract가 모두 있어야 함
        result = apply_all_filters(df, _fs(abstract_only=True), {})
        assert len(result) >= 1
        for abstract in result["Abstract"]:
            assert str(abstract).strip() not in ("", "No abstract available", "nan")

    def test_doi_only_toggle(self, df):
        result = apply_all_filters(df, _fs(doi_only=True), {})
        for doi in result["DOI"]:
            assert str(doi) not in ("N/A", "", "nan")

    def test_get_unique_keywords(self, df):
        kws = get_unique_keywords(df)
        assert isinstance(kws, list)
        assert len(kws) >= 1

    def test_get_unique_keywords_sorted(self, df):
        kws = get_unique_keywords(df)
        assert kws == sorted(kws)


# ── 복합 필터 (AND 조합) ───────────────────────

class TestCombinedFilters:
    def test_text_and_year_combined(self, df):
        result = apply_all_filters(
            df, _fs(search_text="corrosion", year_min=2023, year_max=2026), {}
        )
        for _, row in result.iterrows():
            assert "corrosion" in str(row["Title"]).lower() or "corrosion" in str(row["Abstract"]).lower()
            if pd.notna(row["Year"]):
                assert 2023 <= int(row["Year"]) <= 2026

    def test_text_and_citation_combined(self, df):
        result = apply_all_filters(
            df, _fs(search_text="corrosion", citation_min=10), {}
        )
        assert (result["Citation Count"] >= 10).all()

    def test_all_filters_produce_subset(self, df):
        full = apply_all_filters(df, _fs(), {})
        filtered = apply_all_filters(
            df, _fs(search_text="corrosion", citation_min=5, year_min=2021, year_max=2026), {}
        )
        assert len(filtered) <= len(full)
        # 필터 결과가 원본의 부분집합인지 확인
        assert set(filtered.index).issubset(set(full.index))
