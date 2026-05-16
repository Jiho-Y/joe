"""
app.py — Streamlit 메인 엔트리, 라우팅 및 전체 레이아웃

실행: streamlit run app.py
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from filters import apply_all_filters
from state import (
    apply_loaded_decisions,
    has_unsaved_changes,
    init_session_state,
    load_excel,
)
from ui_components import (
    render_active_filters,
    render_bulk_decision,
    render_detail_panel,
    render_export_panel,
    render_keyboard_shortcuts,
    render_paper_table,
    render_sidebar,
    render_status_bar,
)


def main() -> None:
    """앱 메인 진입점."""
    st.set_page_config(
        page_title="LitScreen",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session_state()
    render_keyboard_shortcuts()

    df = st.session_state.get("df")

    if df is None:
        _render_upload_page()
        return

    render_sidebar(df)

    filter_state = st.session_state.get("filter_state", {})
    decisions = st.session_state.get("decisions", {})
    filtered_df = apply_all_filters(df, filter_state, decisions)

    render_status_bar(df, filtered_df)

    # 활성 필터 인디케이터
    render_active_filters(filter_state)
    st.divider()

    if filtered_df.empty:
        st.info("조건에 맞는 논문이 없습니다. 필터를 조정해보세요.")
    else:
        # 일괄 분류 패널
        render_bulk_decision(filtered_df)

        selected_orig_idx = render_paper_table(filtered_df)

        if selected_orig_idx is not None:
            st.session_state["selected_idx"] = selected_orig_idx
        else:
            saved = st.session_state.get("selected_idx", 0)
            if saved not in filtered_df.index:
                st.session_state["selected_idx"] = filtered_df.index[0]

        selected_idx = st.session_state["selected_idx"]
        row = df.loc[selected_idx]

        _render_navigation(filtered_df)

        st.divider()
        render_detail_panel(row)

    st.divider()
    render_export_panel(df)


def _render_upload_page() -> None:
    """파일 업로드 초기 화면."""
    st.title("📚 LitScreen — 학술 문헌 스크리닝 도구")
    st.markdown(
        """
        Semantic Scholar API로 수집한 논문 메타데이터를 효율적으로 스크리닝할 수 있습니다.

        **사용 방법:**
        1. 아래에서 Excel 파일을 업로드하세요 (`.xlsx`, `Papers` 시트 필요)
        2. 필터로 1차 분류 후 Keep / Maybe / Discard 태깅
        3. Abstract 정독 후 최종 결정
        4. Keep 논문을 Excel / BibTeX / Markdown으로 export

        **키보드 단축키:**
        `K` Keep · `M` Maybe · `D` Discard · `U` Undecided · `J` 다음 · `Shift+J` 이전 · `N` 다음 Undecided
        """
    )
    st.divider()

    uploaded = st.file_uploader(
        "Excel 파일 업로드 (.xlsx)",
        type=["xlsx"],
        help="Papers 시트에 12개 필수 컬럼이 있어야 합니다.",
    )

    if uploaded is not None:
        file_bytes = uploaded.read()
        df, error = load_excel(io.BytesIO(file_bytes))
        if error:
            st.error(f"파일 로드 실패: {error}")
            return

        st.session_state["df"] = df
        st.session_state["file_bytes"] = file_bytes
        st.session_state["file_name"] = uploaded.name
        st.session_state["decisions"] = apply_loaded_decisions(df)
        st.session_state["unsaved_changes"] = False
        st.session_state["saved_bytes"] = None
        st.session_state["selected_idx"] = df.index[0] if not df.empty else 0

        st.success(f"✅ {uploaded.name} 로드 완료 — {len(df)}개 논문")
        st.rerun()


def _render_navigation(filtered_df: pd.DataFrame) -> None:
    """이전/다음 논문 네비게이션 버튼. 단축키: J / Shift+J / N."""
    selected_idx = st.session_state.get("selected_idx")
    indices = list(filtered_df.index)

    if selected_idx not in indices:
        return

    pos = indices.index(selected_idx)
    total = len(indices)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    with col1:
        if st.button("◀ 이전", disabled=(pos == 0), key="btn_prev",
                     help="단축키: Shift+J"):
            st.session_state["selected_idx"] = indices[pos - 1]
            st.rerun()
    with col2:
        if st.button("다음 ▶", disabled=(pos >= total - 1), key="btn_next",
                     help="단축키: J"):
            st.session_state["selected_idx"] = indices[pos + 1]
            st.rerun()
    with col3:
        if st.button("⏭ 다음 Undecided", key="btn_next_undecided",
                     help="단축키: N"):
            decisions = st.session_state.get("decisions", {})
            for i in indices[pos + 1:]:
                pid = str(filtered_df.loc[i, "Paper ID"])
                d = decisions.get(pid, {}).get("decision", "Undecided")
                if d == "Undecided":
                    st.session_state["selected_idx"] = i
                    st.rerun()
                    break
            else:
                st.toast("남은 Undecided 논문이 없습니다.")
    with col4:
        st.caption(f"논문 {pos + 1} / {total} &nbsp;|&nbsp; 단축키: **J** 다음 · **Shift+J** 이전 · **N** 다음 Undecided")

    with st.expander("다른 파일 업로드"):
        if has_unsaved_changes():
            st.warning("⚠️ 저장되지 않은 변경사항이 있습니다. 새 파일을 업로드하면 현재 작업이 사라집니다.")
            confirmed = st.checkbox("변경사항을 버리고 새 파일을 업로드합니다.", key="confirm_new_upload")
        else:
            confirmed = True

        new_file = st.file_uploader("새 파일 업로드", type=["xlsx"], key="new_file_uploader")
        if new_file and confirmed:
            file_bytes = new_file.read()
            df, error = load_excel(io.BytesIO(file_bytes))
            if error:
                st.error(error)
            else:
                st.session_state["df"] = df
                st.session_state["file_bytes"] = file_bytes
                st.session_state["file_name"] = new_file.name
                st.session_state["decisions"] = apply_loaded_decisions(df)
                st.session_state["unsaved_changes"] = False
                st.session_state["saved_bytes"] = None
                st.session_state["selected_idx"] = df.index[0] if not df.empty else 0
                st.rerun()


if __name__ == "__main__":
    main()
