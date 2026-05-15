"""
highlighting.py — 키워드 하이라이트 HTML 생성

Public API:
    highlight_text(text, keyword_terms, user_terms, case_sensitive, word_boundary) -> str
    extract_keyword_terms(keyword_str) -> list[str]
    parse_user_search_terms(search_text) -> list[str]
"""

from __future__ import annotations

import html
import re


KEYWORD_COLOR = "#a8d4ff"   # 파란 배경: Keyword 컬럼 출처
USER_COLOR = "#fff176"      # 노란 배경: 사용자 입력 필터


def extract_keyword_terms(keyword_str: str) -> list[str]:
    """
    Keyword 컬럼 값에서 단어/phrase 추출 (따옴표 phrase 우선, 나머지 개별 단어).

    예: '"wire arc additive manufacturing" "Inconel 625" corrosion'
        → ['wire arc additive manufacturing', 'Inconel 625', 'corrosion']
    """
    if not keyword_str or not isinstance(keyword_str, str):
        return []

    terms = []
    # 따옴표 phrase 먼저 추출
    remaining = keyword_str
    for phrase in re.findall(r'"([^"]+)"', keyword_str):
        stripped = phrase.strip()
        if stripped:
            terms.append(stripped)
        remaining = remaining.replace(f'"{phrase}"', " ", 1)

    # 나머지 개별 단어
    for word in remaining.split():
        word = word.strip()
        if len(word) > 1:
            terms.append(word)

    return terms


def parse_user_search_terms(search_text: str) -> list[str]:
    """사용자 검색 입력에서 쉼표/줄바꿈 구분 term 추출."""
    if not search_text:
        return []
    return [t.strip() for t in re.split(r"[,\n]", search_text) if t.strip()]


def highlight_text(
    text: str,
    keyword_terms: list[str],
    user_terms: list[str],
    case_sensitive: bool = False,
    word_boundary: bool = False,
) -> str:
    """
    텍스트에 두 종류 하이라이트를 적용하여 HTML 문자열 반환.

    keyword_terms: Keyword 컬럼 출처 → 파란 배경
    user_terms: 사용자 필터 입력 → 노란 배경
    겹치는 경우 user_terms(노란색) 우선.
    """
    if not text or not isinstance(text, str):
        return ""

    flags = 0 if case_sensitive else re.IGNORECASE

    def _build_pattern(terms: list[str]) -> re.Pattern | None:
        if not terms:
            return None
        # 긴 term 먼저 매칭하여 부분 덮어씌움 방지
        sorted_terms = sorted(terms, key=len, reverse=True)
        escaped = [re.escape(t) for t in sorted_terms]
        if word_boundary:
            escaped = [rf"\b{e}\b" for e in escaped]
        return re.compile("|".join(escaped), flags)

    # 전체 term을 합쳐 하나의 pass로 처리 (overlap 없이)
    all_terms_with_color: list[tuple[str, str]] = []
    for t in user_terms:
        all_terms_with_color.append((t, USER_COLOR))
    for t in keyword_terms:
        if not any(t.lower() == u.lower() for u in user_terms):
            all_terms_with_color.append((t, KEYWORD_COLOR))

    if not all_terms_with_color:
        return html.escape(text)

    # 정렬: 긴 것 먼저
    all_terms_with_color.sort(key=lambda x: len(x[0]), reverse=True)

    term_list = [t for t, _ in all_terms_with_color]
    color_map = {t.lower(): c for t, c in all_terms_with_color}

    pattern = _build_pattern(term_list)
    if pattern is None:
        return html.escape(text)

    result = []
    last_end = 0
    for m in pattern.finditer(text):
        start, end = m.start(), m.end()
        # 매치 전 텍스트 escape
        result.append(html.escape(text[last_end:start]))
        matched = m.group()
        color = color_map.get(matched.lower(), KEYWORD_COLOR)
        result.append(
            f'<mark style="background-color:{color};padding:0 2px;border-radius:2px;">'
            f"{html.escape(matched)}</mark>"
        )
        last_end = end
    result.append(html.escape(text[last_end:]))

    return "".join(result)
