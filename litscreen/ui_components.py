"""
ui_components.py — 사이드바, 테이블, 상세 패널, 상태 바 컴포넌트

Public API:
    render_sidebar(df)              사이드바 필터 UI 렌더링
    render_status_bar(df, filtered_df)  상단 상태 배지/진행률 바
    render_paper_table(filtered_df) 논문 테이블 렌더링, 선택 인덱스 반환
    render_detail_panel(row)        선택 논문 상세 패널
    render_keyboard_shortcuts()     JS 키보드 단축키 주입
"""

from __future__ import annotations

import time
from typing import Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from filters import get_unique_keywords, get_year_range
from highlighting import (
    extract_keyword_terms,
    highlight_text,
    parse_user_search_terms,
)
from state import (
    DECISION_VALUES,
    build_export_df,
    get_decisions,
    mark_saved,
    reset_filter_state,
    save_to_excel,
    set_decision,
)


# ──────────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────────

def render_sidebar(df: pd.DataFrame) -> None:
    """사이드바 전체 렌더링 (필터 + 저장 + 자동저장)."""
    st.sidebar.title("LitScreen")

    _render_save_section()
    st.sidebar.divider()
    _render_filter_section(df)
    st.sidebar.divider()
    _render_preset_section()


def _render_save_section() -> None:
    """저장 / Autosave 섹션."""
    fs = st.session_state

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("💾 Save", use_container_width=True, key="btn_save_sidebar"):
            _do_save()
    with col2:
        autosave = st.toggle("Autosave", value=fs.get("autosave_enabled", False), key="toggle_autosave")
        st.session_state["autosave_enabled"] = autosave

    if autosave:
        threshold = st.sidebar.number_input(
            "N개 태깅마다 자동 저장", min_value=1, max_value=100,
            value=fs.get("autosave_threshold", 10), key="autosave_threshold_input"
        )
        st.session_state["autosave_threshold"] = threshold
        # 자동저장 트리거
        if fs.get("autosave_count", 0) >= threshold:
            _do_save()
            st.sidebar.success("자동 저장 완료")

    last_saved = fs.get("last_saved_at")
    if last_saved:
        elapsed = int(time.time() - last_saved)
        st.sidebar.caption(f"마지막 저장: {elapsed}초 전")

    if fs.get("unsaved_changes", False):
        st.sidebar.warning("⚠️ 저장되지 않은 변경사항 있음")


def _do_save() -> None:
    """현재 상태를 xlsx bytes로 저장, download 가능하게 준비."""
    df = st.session_state.get("df")
    file_bytes = st.session_state.get("file_bytes")
    file_name = st.session_state.get("file_name", "output.xlsx")
    if df is None:
        st.sidebar.error("저장할 데이터 없음")
        return
    saved_bytes, err = save_to_excel(df, file_bytes, file_name)
    if err:
        st.sidebar.error(err)
    else:
        st.session_state["saved_bytes"] = saved_bytes
        mark_saved()


def _render_filter_section(df: pd.DataFrame) -> None:
    """필터 UI 렌더링."""
    fs = st.session_state.get("filter_state", {})

    st.sidebar.subheader("필터")

    # ── 텍스트 필터
    with st.sidebar.expander("텍스트 검색", expanded=True):
        search_text = st.text_area(
            "키워드 (쉼표 또는 줄바꿈 구분)",
            value=fs.get("search_text", ""),
            height=80,
            key="filter_search_text",
        )
        fs["search_text"] = search_text

        all_cols = ["Title", "Abstract", "Authors", "Venue", "Keyword"]
        search_cols = st.multiselect(
            "검색 대상 컬럼",
            options=all_cols,
            default=fs.get("search_columns", ["Title", "Abstract"]),
            key="filter_search_cols",
        )
        fs["search_columns"] = search_cols or ["Title", "Abstract"]

        match_mode = st.radio(
            "매칭 모드",
            options=["포함 (OR)", "포함 (AND)", "제외 (NONE)"],
            index=["포함 (OR)", "포함 (AND)", "제외 (NONE)"].index(
                fs.get("match_mode", "포함 (OR)")
            ),
            key="filter_match_mode",
        )
        fs["match_mode"] = match_mode

        col1, col2 = st.columns(2)
        with col1:
            case_sensitive = st.toggle(
                "대소문자 구분", value=fs.get("case_sensitive", False), key="filter_case"
            )
            fs["case_sensitive"] = case_sensitive
        with col2:
            word_boundary = st.toggle(
                "단어 경계", value=fs.get("word_boundary", False), key="filter_wb"
            )
            fs["word_boundary"] = word_boundary

    # ── 수치 필터
    with st.sidebar.expander("수치 필터"):
        year_min_data, year_max_data = get_year_range(df)
        if year_min_data is not None:
            cur_min = fs.get("year_min") or year_min_data
            cur_max = fs.get("year_max") or year_max_data
            year_range = st.slider(
                "출판 연도",
                min_value=year_min_data,
                max_value=year_max_data,
                value=(int(cur_min), int(cur_max)),
                key="filter_year",
            )
            fs["year_min"] = year_range[0]
            fs["year_max"] = year_range[1]

            include_no_year = st.toggle(
                "연도 미상 포함",
                value=fs.get("include_no_year", True),
                key="filter_no_year",
            )
            fs["include_no_year"] = include_no_year
        else:
            fs["year_min"] = None
            fs["year_max"] = None

        citation_min = st.number_input(
            "최소 인용 횟수",
            min_value=0,
            value=int(fs.get("citation_min", 0)),
            key="filter_cites",
        )
        fs["citation_min"] = citation_min

    # ── 메타 필터
    with st.sidebar.expander("메타 필터"):
        decisions_filter = st.multiselect(
            "Decision 상태",
            options=DECISION_VALUES,
            default=fs.get("decisions_filter", DECISION_VALUES),
            key="filter_decisions",
        )
        fs["decisions_filter"] = decisions_filter or DECISION_VALUES

        unique_kws = get_unique_keywords(df)
        kw_filter = st.multiselect(
            "검색 Keyword 출처",
            options=unique_kws,
            default=[k for k in fs.get("keywords_filter", []) if k in unique_kws],
            key="filter_kw",
        )
        fs["keywords_filter"] = kw_filter

        abstract_only = st.toggle(
            "Abstract 있는 것만",
            value=fs.get("abstract_only", False),
            key="filter_abstract",
        )
        fs["abstract_only"] = abstract_only

        doi_only = st.toggle(
            "DOI 있는 것만",
            value=fs.get("doi_only", False),
            key="filter_doi",
        )
        fs["doi_only"] = doi_only

    st.session_state["filter_state"] = fs

    if st.sidebar.button("🔄 필터 초기화", use_container_width=True):
        reset_filter_state()
        st.rerun()


def _render_preset_section() -> None:
    """필터 프리셋 저장/불러오기."""
    with st.sidebar.expander("필터 프리셋"):
        presets: dict = st.session_state.get("filter_presets", {})

        preset_name = st.text_input("프리셋 이름", key="preset_name_input")
        if st.button("현재 필터 저장", key="btn_save_preset"):
            if preset_name:
                import copy
                presets[preset_name] = copy.deepcopy(st.session_state.get("filter_state", {}))
                st.session_state["filter_presets"] = presets
                st.success(f"'{preset_name}' 저장됨")

        if presets:
            selected = st.selectbox("저장된 프리셋", options=list(presets.keys()), key="preset_select")
            if st.button("불러오기", key="btn_load_preset"):
                import copy
                st.session_state["filter_state"] = copy.deepcopy(presets[selected])
                st.rerun()
            if st.button("삭제", key="btn_del_preset"):
                del presets[selected]
                st.session_state["filter_presets"] = presets
                st.rerun()


# ──────────────────────────────────────────────
# 상태 바
# ──────────────────────────────────────────────

def render_status_bar(df: pd.DataFrame, filtered_df: pd.DataFrame) -> None:
    """상단 상태 배지 및 진행률 바 렌더링."""
    export_df = build_export_df(df)

    total = len(export_df)
    keep_n = (export_df["Decision"] == "Keep").sum()
    maybe_n = (export_df["Decision"] == "Maybe").sum()
    discard_n = (export_df["Decision"] == "Discard").sum()
    undecided_n = (export_df["Decision"] == "Undecided").sum()
    decided_n = keep_n + maybe_n + discard_n
    progress = decided_n / total if total > 0 else 0.0

    cols = st.columns([3, 1, 1, 1, 1])
    with cols[0]:
        st.markdown(
            f"**전체 {total}개** 중 **{len(filtered_df)}개** 표시 중"
        )
    with cols[1]:
        st.markdown(f"🟢 Keep **{keep_n}**")
    with cols[2]:
        st.markdown(f"🟡 Maybe **{maybe_n}**")
    with cols[3]:
        st.markdown(f"🔴 Discard **{discard_n}**")
    with cols[4]:
        st.markdown(f"⚪ Undecided **{undecided_n}**")

    st.progress(progress, text=f"진행률 {decided_n}/{total} ({progress:.0%})")

    # 저장 완료 Download 버튼
    saved_bytes = st.session_state.get("saved_bytes")
    if saved_bytes:
        file_name = st.session_state.get("file_name", "output.xlsx")
        st.download_button(
            label="📥 저장된 파일 다운로드",
            data=saved_bytes,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_saved_top",
        )


# ──────────────────────────────────────────────
# 논문 테이블
# ──────────────────────────────────────────────

def render_paper_table(filtered_df: pd.DataFrame) -> Optional[int]:
    """
    논문 테이블 렌더링.

    Returns:
        선택된 행의 원본 DataFrame 인덱스 (없으면 None)
    """
    decisions = get_decisions()
    display_df = filtered_df.copy()

    # Decision 반영
    for i, row in display_df.iterrows():
        pid = str(row["Paper ID"])
        if pid in decisions:
            display_df.at[i, "Decision"] = decisions[pid]["decision"]

    # 표시용 컬럼 준비
    def _short_authors(authors: str) -> str:
        if not authors:
            return ""
        parts = [a.strip() for a in authors.split(",") if a.strip()]
        return parts[0] + " et al." if len(parts) > 1 else parts[0] if parts else ""

    display_df["Authors_short"] = display_df["Authors"].apply(_short_authors)
    display_df["Year_str"] = display_df["Year"].apply(
        lambda y: str(int(y)) if pd.notna(y) else "N/A"
    )

    show_cols = ["Decision", "Title", "Authors_short", "Year_str", "Citation Count", "Venue", "Keyword"]
    rename_map = {"Authors_short": "Authors", "Year_str": "Year"}

    table_df = display_df[show_cols].rename(columns=rename_map)

    event = st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=False,
        selection_mode="single-row",
        on_select="rerun",
        key="paper_table",
        column_config={
            "Decision": st.column_config.TextColumn("Decision", width="small"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Authors": st.column_config.TextColumn("Authors", width="medium"),
            "Year": st.column_config.TextColumn("Year", width="small"),
            "Citation Count": st.column_config.NumberColumn("Cites", width="small"),
            "Venue": st.column_config.TextColumn("Venue", width="medium"),
            "Keyword": st.column_config.TextColumn("Keyword", width="medium"),
        },
    )

    # 선택된 행 인덱스 추출
    selected_rows = event.selection.rows if hasattr(event, "selection") else []
    if selected_rows:
        table_pos = selected_rows[0]
        if table_pos < len(filtered_df):
            return filtered_df.index[table_pos]
    return None


# ──────────────────────────────────────────────
# 상세 패널
# ──────────────────────────────────────────────

def render_detail_panel(row: pd.Series) -> None:
    """선택된 논문 상세 패널 렌더링."""
    paper_id = str(row["Paper ID"])
    decisions = get_decisions()
    current = decisions.get(paper_id, {"decision": row.get("Decision", "Undecided"), "reason": ""})
    current_decision = current["decision"]
    current_reason = current.get("reason", "")

    # 하이라이트 설정
    fs = st.session_state.get("filter_state", {})
    kw_terms = extract_keyword_terms(str(row.get("Keyword", "")))
    user_terms = parse_user_search_terms(fs.get("search_text", ""))
    case_sensitive = fs.get("case_sensitive", False)
    word_boundary = fs.get("word_boundary", False)

    # Title
    title_html = highlight_text(
        str(row.get("Title", "")), kw_terms, user_terms, case_sensitive, word_boundary
    )
    st.markdown(
        f"<h3 style='margin-bottom:4px'>{title_html}</h3>",
        unsafe_allow_html=True,
    )

    # 메타 정보
    year = str(int(row["Year"])) if pd.notna(row.get("Year")) else "N/A"
    venue = str(row.get("Venue", "") or "N/A")
    cites = int(row.get("Citation Count", 0))
    doi = str(row.get("DOI", "N/A"))
    url = str(row.get("URL", ""))

    meta_parts = [f"**Year**: {year}", f"**Venue**: {venue}", f"**Citations**: {cites}"]
    if doi not in ("N/A", "", "nan"):
        meta_parts.append(f"**DOI**: [{doi}](https://doi.org/{doi})")
    if url:
        meta_parts.append(f"[Semantic Scholar]({url})")
    st.markdown(" | ".join(meta_parts))

    # 저자
    st.markdown(f"**Authors**: {row.get('Authors', '')}")
    st.divider()

    # Decision 버튼
    st.markdown("**Decision**")
    btn_cols = st.columns(4)
    decision_buttons = [
        ("✅ Keep", "Keep", "primary"),
        ("💛 Maybe", "Maybe", "secondary"),
        ("❌ Discard", "Discard", "secondary"),
        ("⚪ Undecided", "Undecided", "secondary"),
    ]

    for i, (label, value, _type) in enumerate(decision_buttons):
        with btn_cols[i]:
            is_current = current_decision == value
            button_label = f"**{label}**" if is_current else label
            if st.button(
                button_label,
                key=f"btn_{value}_{paper_id}",
                use_container_width=True,
                type="primary" if is_current else "secondary",
            ):
                set_decision(paper_id, value, current_reason)
                st.rerun()

    # Reason 입력
    new_reason = st.text_input(
        "Reason (선택)",
        value=current_reason,
        key=f"reason_{paper_id}",
        placeholder="이 논문을 선택/제외한 이유를 기록하세요",
    )
    if new_reason != current_reason:
        set_decision(paper_id, current_decision, new_reason)

    st.divider()

    # Abstract
    abstract = str(row.get("Abstract", "No abstract available"))
    abstract_html = highlight_text(abstract, kw_terms, user_terms, case_sensitive, word_boundary)
    st.markdown("**Abstract**")
    st.markdown(
        f"<div style='line-height:1.7;font-size:0.95em'>{abstract_html}</div>",
        unsafe_allow_html=True,
    )

    # Chicago Citation
    chicago = str(row.get("Chicago Citation", ""))
    if chicago:
        st.divider()
        st.markdown("**Chicago Citation**")
        st.code(chicago, language=None)


# ──────────────────────────────────────────────
# 키보드 단축키 (JS 주입)
# ──────────────────────────────────────────────

def render_keyboard_shortcuts() -> None:
    """JS keydown 이벤트 기반 키보드 단축키 주입."""
    shortcut_js = """
    <script>
    (function() {
        if (window._litscreenKeysRegistered) return;
        window._litscreenKeysRegistered = true;

        function clickButton(labelContains) {
            const buttons = window.parent.document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.textContent.trim().includes(labelContains)) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }

        window.parent.document.addEventListener('keydown', function(e) {
            const tag = e.target.tagName.toLowerCase();
            if (tag === 'input' || tag === 'textarea') return;

            switch(e.key.toLowerCase()) {
                case 'k':
                    e.preventDefault();
                    clickButton('Keep');
                    break;
                case 'm':
                    e.preventDefault();
                    clickButton('Maybe');
                    break;
                case 'd':
                    e.preventDefault();
                    clickButton('Discard');
                    break;
                case 'u':
                    e.preventDefault();
                    clickButton('Undecided');
                    break;
            }
        });
    })();
    </script>
    """
    components.html(shortcut_js, height=0)


# ──────────────────────────────────────────────
# Export 패널
# ──────────────────────────────────────────────

def render_export_panel(df: pd.DataFrame) -> None:
    """Export 섹션 렌더링."""
    from exporters import export_bibtex, export_markdown, export_xlsx

    st.subheader("Export")
    tab1, tab2, tab3 = st.tabs(["📊 Excel", "📖 BibTeX", "📝 Markdown"])

    with tab1:
        scope = st.radio(
            "Export 범위",
            options=["all", "filtered", "keep", "keep_maybe"],
            format_func=lambda x: {
                "all": "전체",
                "filtered": "현재 필터 view",
                "keep": "Keep만",
                "keep_maybe": "Keep + Maybe",
            }[x],
            horizontal=True,
            key="export_xlsx_scope",
        )
        if st.button("Excel 다운로드", key="btn_export_xlsx"):
            data = export_xlsx(df, get_decisions(), scope)
            st.download_button(
                "📥 xlsx 다운로드",
                data=data,
                file_name="litscreen_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_xlsx",
            )

    with tab2:
        st.caption("Keep으로 분류된 논문만 포함됩니다.")
        if st.button("BibTeX 생성", key="btn_export_bib"):
            bib = export_bibtex(df, get_decisions())
            st.download_button(
                "📥 .bib 다운로드",
                data=bib.encode("utf-8"),
                file_name="litscreen_keep.bib",
                mime="text/plain",
                key="dl_bib",
            )
            with st.expander("미리보기"):
                st.code(bib[:2000] + ("..." if len(bib) > 2000 else ""), language="bibtex")

    with tab3:
        group_by = st.radio(
            "그룹화 기준",
            options=["year", "venue", "citation", "keyword"],
            format_func=lambda x: {
                "year": "Year별",
                "venue": "Venue별",
                "citation": "Citation Count 내림차순",
                "keyword": "Keyword 출처별",
            }[x],
            horizontal=True,
            key="export_md_group",
        )
        if st.button("Markdown 생성", key="btn_export_md"):
            md = export_markdown(df, get_decisions(), group_by)
            st.download_button(
                "📥 .md 다운로드",
                data=md.encode("utf-8"),
                file_name="litscreen_keep.md",
                mime="text/plain",
                key="dl_md",
            )
            with st.expander("미리보기"):
                st.markdown(md[:3000] + ("..." if len(md) > 3000 else ""))
