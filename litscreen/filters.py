"""
filters.py — 텍스트/수치/메타 필터 함수 (순수 함수, DataFrame in/out)

Public API:
    apply_all_filters(df, filter_state, decisions) -> pd.DataFrame
    get_unique_keywords(df) -> list[str]
    get_year_range(df) -> tuple[int, int]
"""

from __future__ import annotations

import re
from typing import Optional

import pandas as pd


def apply_all_filters(
    df: pd.DataFrame,
    filter_state: dict,
    decisions: dict,
) -> pd.DataFrame:
    """모든 필터를 AND 조건으로 적용하여 필터링된 DataFrame 반환."""
    result = df.copy()

    # Decision 필터를 위해 decisions dict 반영
    result = _apply_decision_column(result, decisions)

    result = _apply_text_filter(result, filter_state)
    result = _apply_year_filter(result, filter_state)
    result = _apply_citation_filter(result, filter_state)
    result = _apply_meta_filters(result, filter_state)

    return result


def _apply_decision_column(df: pd.DataFrame, decisions: dict) -> pd.DataFrame:
    """decisions dict를 DataFrame Decision 컬럼에 반영."""
    result = df.copy()
    for i, row in result.iterrows():
        pid = str(row["Paper ID"])
        if pid in decisions:
            result.at[i, "Decision"] = decisions[pid]["decision"]
    return result


def _apply_text_filter(df: pd.DataFrame, fs: dict) -> pd.DataFrame:
    """텍스트 필터 적용."""
    raw = fs.get("search_text", "").strip()
    if not raw:
        return df

    # 쉼표 또는 줄바꿈으로 구분
    terms = [t.strip() for t in re.split(r"[,\n]", raw) if t.strip()]
    if not terms:
        return df

    cols = fs.get("search_columns", ["Title", "Abstract"])
    case = fs.get("case_sensitive", False)
    word_boundary = fs.get("word_boundary", False)
    mode = fs.get("match_mode", "포함 (OR)")

    flags = 0 if case else re.IGNORECASE

    def _build_pattern(term: str) -> re.Pattern:
        escaped = re.escape(term)
        if word_boundary:
            escaped = rf"\b{escaped}\b"
        return re.compile(escaped, flags)

    def _row_matches_term(row: pd.Series, pattern: re.Pattern) -> bool:
        for col in cols:
            if col in row and pd.notna(row[col]):
                if pattern.search(str(row[col])):
                    return True
        return False

    patterns = [_build_pattern(t) for t in terms]

    if mode == "포함 (OR)":
        mask = df.apply(
            lambda row: any(_row_matches_term(row, p) for p in patterns), axis=1
        )
    elif mode == "포함 (AND)":
        mask = df.apply(
            lambda row: all(_row_matches_term(row, p) for p in patterns), axis=1
        )
    elif mode == "제외 (NONE)":
        mask = df.apply(
            lambda row: not any(_row_matches_term(row, p) for p in patterns), axis=1
        )
    else:
        mask = pd.Series([True] * len(df), index=df.index)

    return df[mask]


def _apply_year_filter(df: pd.DataFrame, fs: dict) -> pd.DataFrame:
    """연도 범위 필터 적용."""
    year_min = fs.get("year_min")
    year_max = fs.get("year_max")
    include_no_year = fs.get("include_no_year", True)

    if year_min is None and year_max is None:
        return df

    def _year_ok(y) -> bool:
        if pd.isna(y):
            return include_no_year
        y_int = int(y)
        if year_min is not None and y_int < year_min:
            return False
        if year_max is not None and y_int > year_max:
            return False
        return True

    mask = df["Year"].apply(_year_ok)
    return df[mask]


def _apply_citation_filter(df: pd.DataFrame, fs: dict) -> pd.DataFrame:
    """최소 인용 횟수 필터 적용."""
    cmin = fs.get("citation_min", 0)
    if not cmin:
        return df
    return df[df["Citation Count"] >= cmin]


def _apply_meta_filters(df: pd.DataFrame, fs: dict) -> pd.DataFrame:
    """Decision 상태, Keyword, Abstract, DOI 메타 필터 적용."""
    result = df

    # Decision 상태 필터
    decisions_filter = fs.get("decisions_filter", [])
    if decisions_filter and len(decisions_filter) < 4:
        result = result[result["Decision"].isin(decisions_filter)]

    # Keyword 필터
    kw_filter = fs.get("keywords_filter", [])
    if kw_filter:
        result = result[result["Keyword"].isin(kw_filter)]

    # Abstract 있는 것만
    if fs.get("abstract_only", False):
        result = result[
            result["Abstract"].notna() &
            (result["Abstract"] != "No abstract available") &
            (result["Abstract"].str.strip() != "")
        ]

    # DOI 있는 것만
    if fs.get("doi_only", False):
        result = result[
            result["DOI"].notna() &
            (result["DOI"] != "N/A") &
            (result["DOI"].str.strip() != "")
        ]

    return result


def get_unique_keywords(df: pd.DataFrame) -> list[str]:
    """DataFrame에서 unique Keyword 값 목록 반환."""
    if "Keyword" not in df.columns:
        return []
    return sorted(df["Keyword"].dropna().unique().tolist())


def get_year_range(df: pd.DataFrame) -> tuple[Optional[int], Optional[int]]:
    """DataFrame의 Year 컬럼 min/max 반환 (NaN 제외)."""
    years = df["Year"].dropna()
    if years.empty:
        return None, None
    return int(years.min()), int(years.max())
