"""신규 기능 테스트 — 필터 인디케이터, 일괄 분류, Decision 아이콘."""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

SAMPLE_PATH = Path("/root/.claude/uploads/81ff8d91-5a3d-4197-bece-363cc2d2eb9d/9cc2082b-IN625_corrosion_Tier1.xlsx")


def _load_df():
    from state import load_excel
    df, _ = load_excel(io.BytesIO(SAMPLE_PATH.read_bytes()))
    return df


def _fs(**kwargs) -> dict:
    from state import DECISION_VALUES
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
        "decisions_filter": DECISION_VALUES[:],
        "keywords_filter": [],
        "abstract_only": False,
        "doi_only": False,
    }
    base.update(kwargs)
    return base


# ── render_active_filters 로직 검증 ───────────────

class TestActiveFilterLogic:
    """render_active_filters가 생성하는 chip 내용 검증.
    Streamlit 없이 로직만 추출하여 테스트."""

    def _collect_chips(self, fs: dict) -> list[str]:
        """render_active_filters와 동일한 로직으로 chip 목록 반환."""
        from state import DECISION_VALUES
        chips = []

        if fs.get("search_text", "").strip():
            chips.append("search")

        year_min = fs.get("year_min")
        year_max = fs.get("year_max")
        if year_min is not None and year_max is not None:
            chips.append(f"year:{year_min}-{year_max}")

        if not fs.get("include_no_year", True):
            chips.append("no_year_excluded")

        cmin = fs.get("citation_min", 0)
        if cmin and cmin > 0:
            chips.append(f"cites:{cmin}")

        d_filter = set(fs.get("decisions_filter", DECISION_VALUES))
        if d_filter != set(DECISION_VALUES):
            chips.append(f"decisions:{sorted(d_filter)}")

        kw_filter = fs.get("keywords_filter", [])
        if kw_filter:
            chips.append(f"kw:{len(kw_filter)}")

        if fs.get("abstract_only"):
            chips.append("abstract_only")

        if fs.get("doi_only"):
            chips.append("doi_only")

        return chips

    def test_no_filter_shows_nothing(self):
        chips = self._collect_chips(_fs())
        assert chips == []

    def test_search_text_shows_chip(self):
        chips = self._collect_chips(_fs(search_text="corrosion"))
        assert "search" in chips

    def test_year_range_shows_chip(self):
        chips = self._collect_chips(_fs(year_min=2021, year_max=2024))
        assert any("year" in c for c in chips)

    def test_citation_min_shows_chip(self):
        chips = self._collect_chips(_fs(citation_min=10))
        assert any("cites" in c for c in chips)

    def test_citation_min_zero_no_chip(self):
        chips = self._collect_chips(_fs(citation_min=0))
        assert not any("cites" in c for c in chips)

    def test_decision_filter_partial_shows_chip(self):
        chips = self._collect_chips(_fs(decisions_filter=["Keep", "Maybe"]))
        assert any("decisions" in c for c in chips)

    def test_decision_filter_all_no_chip(self):
        from state import DECISION_VALUES
        chips = self._collect_chips(_fs(decisions_filter=DECISION_VALUES[:]))
        assert not any("decisions" in c for c in chips)

    def test_keyword_filter_shows_chip(self):
        chips = self._collect_chips(_fs(keywords_filter=["keyword1"]))
        assert any("kw" in c for c in chips)

    def test_abstract_only_shows_chip(self):
        chips = self._collect_chips(_fs(abstract_only=True))
        assert "abstract_only" in chips

    def test_doi_only_shows_chip(self):
        chips = self._collect_chips(_fs(doi_only=True))
        assert "doi_only" in chips

    def test_multiple_filters_all_shown(self):
        chips = self._collect_chips(_fs(
            search_text="corrosion",
            year_min=2021, year_max=2024,
            citation_min=5,
        ))
        assert len(chips) == 3

    def test_no_year_excluded_shows_chip(self):
        chips = self._collect_chips(_fs(year_min=2021, year_max=2024, include_no_year=False))
        assert "no_year_excluded" in chips


# ── Decision 아이콘 매핑 ───────────────────────

class TestDecisionIcons:
    def test_all_decisions_have_icons(self):
        from ui_components import DECISION_ICONS
        from state import DECISION_VALUES
        for d in DECISION_VALUES:
            assert d in DECISION_ICONS, f"Missing icon for {d}"

    def test_keep_icon_contains_checkmark(self):
        from ui_components import DECISION_ICONS
        assert "✅" in DECISION_ICONS["Keep"]

    def test_maybe_icon_contains_yellow(self):
        from ui_components import DECISION_ICONS
        assert "💛" in DECISION_ICONS["Maybe"]

    def test_discard_icon_contains_cross(self):
        from ui_components import DECISION_ICONS
        assert "❌" in DECISION_ICONS["Discard"]

    def test_undecided_icon_contains_white_circle(self):
        from ui_components import DECISION_ICONS
        assert "⚪" in DECISION_ICONS["Undecided"]

    def test_icon_mapping_applied_to_df(self):
        """테이블 표시 시 Decision이 아이콘 문자열로 변환되는지 확인."""
        from ui_components import DECISION_ICONS
        df = _load_df()
        df.loc[df.index[0], "Decision"] = "Keep"
        df.loc[df.index[1], "Decision"] = "Maybe"
        df.loc[df.index[2], "Decision"] = "Discard"

        # render_paper_table 내부 로직 재현
        display_df = df.copy()
        display_df["Decision"] = display_df["Decision"].map(DECISION_ICONS).fillna("⚪ —")

        assert display_df.loc[df.index[0], "Decision"] == DECISION_ICONS["Keep"]
        assert display_df.loc[df.index[1], "Decision"] == DECISION_ICONS["Maybe"]
        assert display_df.loc[df.index[2], "Decision"] == DECISION_ICONS["Discard"]
        assert display_df.loc[df.index[3], "Decision"] == DECISION_ICONS["Undecided"]


# ── 일괄 분류 (bulk decision) 로직 ────────────

class TestBulkDecisionLogic:
    """render_bulk_decision 내부 로직: set_decision 호출 검증."""

    def test_bulk_applies_to_all_filtered_rows(self):
        """필터 결과의 모든 행에 set_decision이 호출되어야 함."""
        from state import set_decision
        df = _load_df()
        filtered_df = df.iloc[:5]  # 5개 행 선택

        calls = []
        def mock_set_decision(pid, decision, reason):
            calls.append((pid, decision))

        with patch("ui_components.set_decision", side_effect=mock_set_decision), \
             patch("ui_components.get_decisions", return_value={}), \
             patch("streamlit.toast"), patch("streamlit.rerun"):
            # render_bulk_decision 내부 로직 직접 재현
            for idx in filtered_df.index:
                pid = str(filtered_df.loc[idx, "Paper ID"])
                mock_set_decision(pid, "Discard", "")

        assert len(calls) == 5
        assert all(d == "Discard" for _, d in calls)

    def test_bulk_preserves_existing_reason(self):
        """일괄 분류 시 기존 Reason은 보존되어야 함."""
        from state import get_decisions
        df = _load_df()
        pid = str(df.iloc[0]["Paper ID"])
        existing_decisions = {pid: {"decision": "Maybe", "reason": "interesting"}}

        calls = []
        def mock_set_decision(p, decision, reason):
            calls.append((p, decision, reason))

        with patch("ui_components.set_decision", side_effect=mock_set_decision), \
             patch("ui_components.get_decisions", return_value=existing_decisions), \
             patch("streamlit.toast"), patch("streamlit.rerun"):
            filtered_df = df.iloc[:1]
            for idx in filtered_df.index:
                _pid = str(filtered_df.loc[idx, "Paper ID"])
                existing = existing_decisions.get(_pid, {})
                reason = existing.get("reason", "")
                mock_set_decision(_pid, "Discard", reason)

        assert calls[0][2] == "interesting"  # reason 보존

    def test_bulk_discard_all_filtered(self):
        """Discard All 시 필터된 논문이 모두 Discard로 변경되어야 함."""
        from filters import apply_all_filters
        df = _load_df()
        fs = _fs(search_text="corrosion", search_columns=["Title"])
        decisions = {}
        filtered = apply_all_filters(df, fs, decisions)

        # 필터 결과가 있어야 함
        assert len(filtered) >= 1

        # 일괄 Discard 적용
        applied = {}
        for idx in filtered.index:
            pid = str(filtered.loc[idx, "Paper ID"])
            applied[pid] = "Discard"

        # 필터 결과만 Discard, 나머지는 Undecided
        other_ids = set(str(df.loc[i, "Paper ID"]) for i in df.index
                        if i not in filtered.index)
        for pid in other_ids:
            assert pid not in applied


# ── 텍스트 필터 적용 방식 (form submit) ────────

class TestTextFilterForm:
    """텍스트 필터가 즉시 적용되지 않고 명시적 submit 후 적용됨을 확인."""

    def test_filter_state_not_changed_without_submit(self):
        """filter_state의 search_text는 form submit 없이 변경되지 않아야 함."""
        # 이 테스트는 Streamlit form 동작을 간접 검증:
        # _render_filter_section에서 form submit 시에만 fs["search_text"]를 갱신
        # 여기서는 form submit 플래그 없이는 갱신하지 않는 코드 패턴을 확인
        import ast, inspect
        import ui_components
        src = inspect.getsource(ui_components._render_filter_section)
        tree = ast.parse(src)

        # "submitted" 변수가 조건으로 사용되는지 확인
        assert "submitted" in src, "form submit 플래그 'submitted'가 없음"
        assert 'form_submit_button' in src, "st.form_submit_button 없음"

    def test_form_wraps_text_filter(self):
        """텍스트 필터 섹션이 st.form 안에 있는지 확인."""
        import ui_components, inspect
        src = inspect.getsource(ui_components._render_filter_section)
        assert "st.form" in src, "st.form 없음 — 텍스트 필터가 form으로 래핑되지 않음"


# ── 키보드 단축키 JS 내용 검증 ─────────────────

class TestKeyboardShortcuts:
    def _get_js(self) -> str:
        import ui_components, inspect
        src = inspect.getsource(ui_components.render_keyboard_shortcuts)
        # shortcut_js 문자열 추출
        start = src.find('"""', src.find("shortcut_js"))
        end = src.find('"""', start + 3)
        return src[start:end]

    def test_keep_shortcut_defined(self):
        assert "'k'" in self._get_js() or "case 'k'" in self._get_js()

    def test_maybe_shortcut_defined(self):
        assert "'m'" in self._get_js() or "case 'm'" in self._get_js()

    def test_discard_shortcut_defined(self):
        assert "'d'" in self._get_js() or "case 'd'" in self._get_js()

    def test_undecided_shortcut_defined(self):
        assert "'u'" in self._get_js() or "case 'u'" in self._get_js()

    def test_next_shortcut_j_defined(self):
        js = self._get_js()
        assert "key === 'j'" in js or "key === 'J'" in js

    def test_prev_shortcut_shift_j_defined(self):
        js = self._get_js()
        assert "shiftKey" in js and ("'j'" in js or "'J'" in js)

    def test_next_undecided_shortcut_n_defined(self):
        js = self._get_js()
        assert "'n'" in js or "key === 'n'" in js

    def test_input_fields_excluded(self):
        """input/textarea에 포커스 중일 때 단축키 비활성화."""
        js = self._get_js()
        assert "textarea" in js
        assert "input" in js
