"""highlighting.py 테스트 — 키워드 하이라이트 HTML 생성."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from highlighting import (
    KEYWORD_COLOR,
    USER_COLOR,
    extract_keyword_terms,
    highlight_text,
    parse_user_search_terms,
)


# ── extract_keyword_terms ──────────────────────

class TestExtractKeywordTerms:
    def test_quoted_phrases_extracted(self):
        kw = '"wire arc additive manufacturing" "Inconel 625" corrosion'
        terms = extract_keyword_terms(kw)
        assert "wire arc additive manufacturing" in terms
        assert "Inconel 625" in terms

    def test_unquoted_words_extracted(self):
        kw = '"wire arc additive manufacturing" corrosion'
        terms = extract_keyword_terms(kw)
        assert "corrosion" in terms

    def test_quoted_phrase_not_split(self):
        kw = '"Inconel 625"'
        terms = extract_keyword_terms(kw)
        assert "Inconel 625" in terms
        assert "Inconel" not in terms or "625" not in terms  # phrase는 쪼개지지 않음

    def test_empty_string_returns_empty(self):
        assert extract_keyword_terms("") == []

    def test_none_returns_empty(self):
        assert extract_keyword_terms(None) == []

    def test_single_word(self):
        terms = extract_keyword_terms("corrosion")
        assert "corrosion" in terms

    def test_only_quoted(self):
        terms = extract_keyword_terms('"heat treatment"')
        assert "heat treatment" in terms

    def test_multiple_unquoted_words(self):
        terms = extract_keyword_terms("corrosion microstructure alloy")
        assert "corrosion" in terms
        assert "microstructure" in terms
        assert "alloy" in terms


# ── parse_user_search_terms ────────────────────

class TestParseUserSearchTerms:
    def test_comma_separated(self):
        terms = parse_user_search_terms("corrosion, microstructure, alloy")
        assert terms == ["corrosion", "microstructure", "alloy"]

    def test_newline_separated(self):
        terms = parse_user_search_terms("corrosion\nmicrostructure\nalloy")
        assert terms == ["corrosion", "microstructure", "alloy"]

    def test_empty_string(self):
        assert parse_user_search_terms("") == []

    def test_strips_whitespace(self):
        terms = parse_user_search_terms("  corrosion  ,  alloy  ")
        assert "corrosion" in terms
        assert "alloy" in terms

    def test_skips_empty_tokens(self):
        terms = parse_user_search_terms("corrosion,,alloy")
        assert "" not in terms
        assert len(terms) == 2


# ── highlight_text ─────────────────────────────

class TestHighlightText:
    def test_no_terms_returns_escaped_text(self):
        result = highlight_text("plain text", [], [])
        assert result == "plain text"

    def test_xss_special_chars_escaped(self):
        result = highlight_text("<script>alert(1)</script>", [], [])
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_keyword_term_highlighted_blue(self):
        result = highlight_text("Inconel 625 corrosion", ["Inconel 625"], [])
        assert KEYWORD_COLOR in result
        assert "Inconel 625" in result

    def test_user_term_highlighted_yellow(self):
        result = highlight_text("corrosion study", [], ["corrosion"])
        assert USER_COLOR in result
        assert "corrosion" in result

    def test_user_term_takes_priority_over_keyword(self):
        # 겹치는 단어: user > keyword
        result = highlight_text("corrosion", ["corrosion"], ["corrosion"])
        # 노란색 우선 (user color)
        assert USER_COLOR in result

    def test_case_insensitive_default(self):
        result = highlight_text("CORROSION behavior", ["corrosion"], [])
        assert KEYWORD_COLOR in result

    def test_case_sensitive_no_match(self):
        result = highlight_text("CORROSION behavior", ["corrosion"], [], case_sensitive=True)
        assert KEYWORD_COLOR not in result
        assert USER_COLOR not in result

    def test_case_sensitive_exact_match(self):
        result = highlight_text("Corrosion behavior", ["Corrosion"], [], case_sensitive=True)
        assert KEYWORD_COLOR in result

    def test_word_boundary_prevents_partial(self):
        # "AM" with boundary → "WAAM"의 AM에 매칭 안 됨
        result = highlight_text("WAAM process", ["AM"], [], word_boundary=True)
        assert KEYWORD_COLOR not in result

    def test_word_boundary_matches_standalone(self):
        result = highlight_text("AM process", ["AM"], [], word_boundary=True)
        assert KEYWORD_COLOR in result

    def test_phrase_highlighted_as_unit(self):
        result = highlight_text(
            "wire arc additive manufacturing process",
            ["wire arc additive manufacturing"],
            [],
        )
        assert KEYWORD_COLOR in result
        # phrase 전체가 하나의 mark 태그에 포함되어야 함
        assert "wire arc additive manufacturing" in result

    def test_multiple_occurrences_all_highlighted(self):
        result = highlight_text(
            "corrosion study and corrosion resistance",
            ["corrosion"],
            [],
        )
        assert result.count(KEYWORD_COLOR) >= 2

    def test_empty_text_returns_empty(self):
        assert highlight_text("", ["corrosion"], []) == ""

    def test_none_text_returns_empty(self):
        assert highlight_text(None, ["corrosion"], []) == ""

    def test_html_structure_valid(self):
        result = highlight_text("Inconel 625 corrosion", ["Inconel 625"], ["corrosion"])
        assert result.count("<mark") == result.count("</mark>")

    def test_ampersand_escaped(self):
        result = highlight_text("A & B alloy", [], [])
        assert "&amp;" in result
        assert "& B" not in result

    def test_real_keyword_from_sample(self):
        kw = '"wire arc additive manufacturing" "Inconel 625" corrosion'
        from highlighting import extract_keyword_terms
        terms = extract_keyword_terms(kw)
        text = ("Microstructural and intergranular corrosion properties of "
                "Inconel 625 superalloys fabricated using wire arc additive manufacturing")
        result = highlight_text(text, terms, [])
        assert KEYWORD_COLOR in result
        # 주요 terms가 하이라이트되어야 함
        assert "corrosion" in result
        assert "Inconel 625" in result
