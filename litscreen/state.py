"""
state.py — session_state 초기화/관리, xlsx 로드/저장

Public API:
    init_session_state()        세션 상태 초기화 (앱 시작 시 1회 호출)
    load_excel(file)            업로드된 파일을 DataFrame으로 로드, 검증
    save_to_excel(df, path)     DataFrame을 xlsx에 Decision/Reason 포함하여 저장
    get_decisions()             {paper_id: {decision, reason}} dict 반환
    set_decision(paper_id, decision, reason)  단건 결정 저장
    has_unsaved_changes()       저장되지 않은 변경 여부
    mark_saved()                저장 완료 표시
"""

from __future__ import annotations

import io
import shutil
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

REQUIRED_COLUMNS = [
    "Keyword", "Paper ID", "DOI", "Title", "Authors",
    "Year", "Publication Date", "Venue", "Citation Count",
    "Abstract", "URL", "Chicago Citation",
]
DECISION_VALUES = ["Undecided", "Keep", "Maybe", "Discard"]
SHEET_NAME = "Papers"


def init_session_state() -> None:
    """필요한 모든 session_state 키를 기본값으로 초기화."""
    defaults = {
        "df": None,
        "file_name": None,
        "file_bytes": None,
        "decisions": {},        # {paper_id: {"decision": str, "reason": str}}
        "selected_idx": 0,
        "unsaved_changes": False,
        "last_saved_at": None,
        "autosave_enabled": False,
        "autosave_count": 0,
        "autosave_threshold": 10,
        "filter_state": _default_filter_state(),
        "filter_presets": {},
        "current_preset_name": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _default_filter_state() -> dict:
    return {
        "search_text": "",
        "search_columns": ["Title", "Abstract"],
        "match_mode": "포함 (OR)",
        "case_sensitive": False,
        "word_boundary": False,
        "year_min": None,
        "year_max": None,
        "include_no_year": True,
        "citation_min": 0,
        "decisions_filter": DECISION_VALUES.copy(),
        "keywords_filter": [],
        "abstract_only": False,
        "doi_only": False,
    }


def load_excel(file: io.BytesIO) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    업로드 파일을 DataFrame으로 로드하고 컬럼 검증.

    Returns:
        (DataFrame, None) on success
        (None, error_message) on failure
    """
    try:
        df = pd.read_excel(file, sheet_name=SHEET_NAME, engine="openpyxl")
    except Exception as e:
        return None, f"파일 읽기 실패: {e}"

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return None, f"필수 컬럼 누락: {', '.join(missing)}"

    # Decision/Reason 컬럼 복원 또는 초기화
    if "Decision" not in df.columns:
        df["Decision"] = "Undecided"
    else:
        df["Decision"] = df["Decision"].fillna("Undecided")
        df["Decision"] = df["Decision"].where(
            df["Decision"].isin(DECISION_VALUES), "Undecided"
        )

    if "Reason" not in df.columns:
        df["Reason"] = ""
    else:
        df["Reason"] = df["Reason"].fillna("")

    # 타입 정규화
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Citation Count"] = pd.to_numeric(df["Citation Count"], errors="coerce").fillna(0).astype(int)
    df["Paper ID"] = df["Paper ID"].astype(str)
    df["Abstract"] = df["Abstract"].fillna("No abstract available")
    df["DOI"] = df["DOI"].fillna("N/A")
    df["Venue"] = df["Venue"].fillna("")

    df = df.reset_index(drop=True)
    return df, None


def apply_loaded_decisions(df: pd.DataFrame) -> dict:
    """DataFrame의 Decision/Reason 컬럼으로 decisions dict 생성."""
    decisions = {}
    for _, row in df.iterrows():
        pid = str(row["Paper ID"])
        decisions[pid] = {
            "decision": row.get("Decision", "Undecided"),
            "reason": str(row.get("Reason", "") or ""),
        }
    return decisions


def get_decisions() -> dict:
    """현재 session decisions dict 반환."""
    return st.session_state.get("decisions", {})


def set_decision(paper_id: str, decision: str, reason: str = "") -> None:
    """단건 논문 결정 저장, unsaved 플래그 설정."""
    if "decisions" not in st.session_state:
        st.session_state["decisions"] = {}
    st.session_state["decisions"][paper_id] = {
        "decision": decision,
        "reason": reason,
    }
    st.session_state["unsaved_changes"] = True
    st.session_state["autosave_count"] = st.session_state.get("autosave_count", 0) + 1


def has_unsaved_changes() -> bool:
    """저장되지 않은 변경 여부 반환."""
    return st.session_state.get("unsaved_changes", False)


def mark_saved() -> None:
    """저장 완료 표시."""
    st.session_state["unsaved_changes"] = False
    st.session_state["last_saved_at"] = time.time()
    st.session_state["autosave_count"] = 0


def build_export_df(df: pd.DataFrame) -> pd.DataFrame:
    """decisions dict를 DataFrame Decision/Reason 컬럼에 반영한 복사본 반환."""
    result = df.copy()
    decisions = get_decisions()
    for i, row in result.iterrows():
        pid = str(row["Paper ID"])
        if pid in decisions:
            result.at[i, "Decision"] = decisions[pid]["decision"]
            result.at[i, "Reason"] = decisions[pid]["reason"]
    return result


def save_to_excel(df: pd.DataFrame, file_bytes: bytes, file_name: str) -> tuple[Optional[bytes], Optional[str]]:
    """
    DataFrame을 xlsx bytes로 저장.

    Returns:
        (bytes, None) on success
        (None, error_message) on failure
    """
    try:
        export_df = build_export_df(df)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            export_df.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        buf.seek(0)
        return buf.read(), None
    except Exception as e:
        return None, f"저장 실패: {e}"


def reset_filter_state() -> None:
    """필터 상태를 기본값으로 리셋."""
    st.session_state["filter_state"] = _default_filter_state()
