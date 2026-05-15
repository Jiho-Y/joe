"""exporters.py 테스트 — xlsx / BibTeX / Markdown export."""

import io
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

SAMPLE_PATH = Path("/root/.claude/uploads/81ff8d91-5a3d-4197-bece-363cc2d2eb9d/9cc2082b-IN625_corrosion_Tier1.xlsx")


def _load_df():
    from state import load_excel
    df, _ = load_excel(io.BytesIO(SAMPLE_PATH.read_bytes()))
    return df


def _make_decisions(df, mapping: dict[int, str]) -> dict:
    """{row_index: decision} → decisions dict."""
    decisions = {}
    for idx, decision in mapping.items():
        pid = str(df.iloc[idx]["Paper ID"])
        decisions[pid] = {"decision": decision, "reason": f"reason_{decision}"}
    return decisions


def _apply_decisions_to_df(df, decisions):
    """decisions dict를 DataFrame에 직접 반영한 복사본 반환."""
    result = df.copy()
    for i, row in result.iterrows():
        pid = str(row["Paper ID"])
        if pid in decisions:
            result.at[i, "Decision"] = decisions[pid]["decision"]
            result.at[i, "Reason"] = decisions[pid]["reason"]
    return result


# build_export_df는 session_state를 사용하므로 mock 필요
def _with_decisions(df, decisions):
    """exporters가 build_export_df를 호출할 때 decisions가 반영되도록 df를 직접 수정."""
    return _apply_decisions_to_df(df, decisions)


# ── xlsx Export ────────────────────────────────

class TestXlsxExport:
    def setup_method(self):
        self.df = _load_df()
        self.decisions = _make_decisions(self.df, {0: "Keep", 1: "Keep", 2: "Maybe", 3: "Discard"})

    def test_export_all_returns_valid_excel(self):
        from exporters import export_xlsx
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            data = export_xlsx(self.df, self.decisions, scope="all")
        assert len(data) > 0
        reloaded = pd.read_excel(io.BytesIO(data), sheet_name="Papers")
        assert len(reloaded) == 16

    def test_export_keep_only(self):
        from exporters import export_xlsx
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            data = export_xlsx(self.df, self.decisions, scope="keep")
        reloaded = pd.read_excel(io.BytesIO(data), sheet_name="Papers")
        assert len(reloaded) == 2
        assert all(d == "Keep" for d in reloaded["Decision"])

    def test_export_keep_maybe(self):
        from exporters import export_xlsx
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            data = export_xlsx(self.df, self.decisions, scope="keep_maybe")
        reloaded = pd.read_excel(io.BytesIO(data), sheet_name="Papers")
        assert len(reloaded) == 3
        assert set(reloaded["Decision"].unique()).issubset({"Keep", "Maybe"})

    def test_export_preserves_all_columns(self):
        from exporters import export_xlsx
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            data = export_xlsx(self.df, self.decisions, scope="all")
        reloaded = pd.read_excel(io.BytesIO(data), sheet_name="Papers")
        for col in ["Title", "Authors", "Year", "Decision", "Reason"]:
            assert col in reloaded.columns


# ── BibTeX Export ──────────────────────────────

class TestBibtexExport:
    def setup_method(self):
        self.df = _load_df()
        self.decisions = _make_decisions(self.df, {0: "Keep", 1: "Keep"})

    def test_bibtex_returns_string(self):
        from exporters import export_bibtex
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_bibtex(self.df, self.decisions)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_bibtex_has_article_entries(self):
        from exporters import export_bibtex
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_bibtex(self.df, self.decisions)
        assert result.count("@article{") == 2

    def test_bibtex_has_required_fields(self):
        from exporters import export_bibtex
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_bibtex(self.df, self.decisions)
        assert "title" in result
        assert "author" in result
        assert "year" in result

    def test_bibtex_citation_key_format(self):
        from exporters import export_bibtex, _make_citation_key
        row = self.df.iloc[0]
        key = _make_citation_key(row)
        # 특수문자 없는 소문자 영숫자
        import re
        assert re.match(r"^[a-z0-9_]+$", key), f"Invalid key: {key}"

    def test_bibtex_no_doi_adds_note(self):
        from exporters import export_bibtex
        # DOI가 N/A인 논문 찾기
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        no_doi_rows = df_with[df_with["DOI"] == "N/A"]
        if not no_doi_rows.empty:
            no_doi_pid = str(no_doi_rows.iloc[0]["Paper ID"])
            decisions_no_doi = {no_doi_pid: {"decision": "Keep", "reason": ""}}
            df_single = no_doi_rows.iloc[:1].copy()
            df_single["Decision"] = "Keep"
            df_single["Reason"] = ""
            with patch("exporters.build_export_df", return_value=df_single):
                result = export_bibtex(df_single, decisions_no_doi)
            assert "Semantic Scholar paper ID" in result

    def test_bibtex_empty_when_no_keep(self):
        from exporters import export_bibtex
        df_with = self.df.copy()  # all Undecided
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_bibtex(self.df, {})
        assert result == ""

    def test_bibtex_citation_key_uses_first_author_year(self):
        from exporters import _make_citation_key
        row = pd.Series({
            "Authors": "Zhang, Y., Li, X., Wang, Z.",
            "Year": 2023,
            "Title": "Corrosion behavior study",
        })
        key = _make_citation_key(row)
        assert "zhang" in key
        assert "2023" in key

    def test_bibtex_doi_included_when_present(self):
        from exporters import export_bibtex
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_bibtex(self.df, self.decisions)
        # Keep된 논문 중 DOI 있는 것은 doi 필드 포함
        keep_rows = df_with[df_with["Decision"] == "Keep"]
        has_doi = keep_rows[keep_rows["DOI"].notna() & (keep_rows["DOI"] != "N/A")]
        if not has_doi.empty:
            assert "doi" in result


# ── Markdown Export ────────────────────────────

class TestMarkdownExport:
    def setup_method(self):
        self.df = _load_df()
        self.decisions = _make_decisions(self.df, {0: "Keep", 1: "Keep", 5: "Keep"})

    def test_markdown_returns_string(self):
        from exporters import export_markdown
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, self.decisions)
        assert isinstance(result, str)

    def test_markdown_has_header(self):
        from exporters import export_markdown
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, self.decisions)
        assert "# Literature Screening Results" in result

    def test_markdown_includes_total_count(self):
        from exporters import export_markdown
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, self.decisions)
        assert "Total kept**: 3" in result

    def test_markdown_group_by_year(self):
        from exporters import export_markdown
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, self.decisions, group_by="year")
        # 연도 섹션 헤더 존재 (## 2021, ## 2024 등)
        import re
        year_headers = re.findall(r"^## \d{4}", result, re.MULTILINE)
        assert len(year_headers) >= 1

    def test_markdown_group_by_venue(self):
        from exporters import export_markdown
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, self.decisions, group_by="venue")
        assert "## " in result

    def test_markdown_group_by_citation(self):
        from exporters import export_markdown
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, self.decisions, group_by="citation")
        assert "Citation Count" in result

    def test_markdown_group_by_keyword(self):
        from exporters import export_markdown
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, self.decisions, group_by="keyword")
        assert "## " in result

    def test_markdown_empty_when_no_keep(self):
        from exporters import export_markdown
        df_with = self.df.copy()
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, {})
        assert "No papers marked as Keep" in result

    def test_markdown_includes_title_in_bullets(self):
        from exporters import export_markdown
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, self.decisions)
        # Keep된 논문 제목이 포함되어야 함
        keep_title = df_with[df_with["Decision"] == "Keep"].iloc[0]["Title"]
        assert keep_title[:30] in result

    def test_markdown_includes_export_date(self):
        from exporters import export_markdown
        from datetime import date
        df_with = _apply_decisions_to_df(self.df, self.decisions)
        with patch("exporters.build_export_df", return_value=df_with):
            result = export_markdown(self.df, self.decisions)
        today = date.today().isoformat()
        assert today in result


# ── 헬퍼 함수 ──────────────────────────────────

class TestHelpers:
    def test_et_al_three_authors(self):
        from exporters import _et_al
        # Semantic Scholar 저자 형식: "FirstName LastName" 쉼표 구분
        result = _et_al("Jae Kim, Sang Lee, Hyun Park")
        assert "Jae Kim" in result
        assert "et al." not in result  # 3명은 et al. 없음

    def test_et_al_four_authors(self):
        from exporters import _et_al
        result = _et_al("Kim, J., Lee, S., Park, H., Choi, Y.")
        assert "et al." in result

    def test_et_al_empty(self):
        from exporters import _et_al
        result = _et_al("")
        assert result == "Unknown"

    def test_format_paper_bullet_structure(self):
        from exporters import _format_paper_bullet
        row = pd.Series({
            "Title": "Test Paper",
            "Year": 2023.0,
            "Authors": "Kim, J., Lee, S.",
            "Venue": "Journal A",
            "Citation Count": 10,
            "DOI": "10.1/test",
            "Reason": "good",
        })
        bullet = _format_paper_bullet(row)
        assert "**Test Paper**" in bullet
        assert "2023" in bullet
        assert "Cited by 10" in bullet
        assert "good" in bullet

    def test_format_paper_bullet_no_doi(self):
        from exporters import _format_paper_bullet
        row = pd.Series({
            "Title": "Test Paper",
            "Year": 2023.0,
            "Authors": "Kim, J.",
            "Venue": "",
            "Citation Count": 0,
            "DOI": "N/A",
            "Reason": "",
        })
        bullet = _format_paper_bullet(row)
        assert "No DOI" in bullet
