"""
exporters.py — xlsx, BibTeX, Markdown export

Public API:
    export_xlsx(df, decisions, scope) -> bytes
    export_bibtex(df, decisions) -> str
    export_markdown(df, decisions, group_by) -> str
"""

from __future__ import annotations

import io
import re
from datetime import date
from typing import Literal

import pandas as pd

from state import build_export_df

SHEET_NAME = "Papers"

Scope = Literal["all", "filtered", "keep", "keep_maybe"]
GroupBy = Literal["year", "venue", "citation", "keyword"]


def export_xlsx(df: pd.DataFrame, decisions: dict, scope: Scope = "all") -> bytes:
    """지정 scope의 DataFrame을 xlsx bytes로 반환."""
    result = build_export_df(df)
    result = _filter_by_scope(result, scope)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        result.to_excel(writer, sheet_name=SHEET_NAME, index=False)
    buf.seek(0)
    return buf.read()


def _filter_by_scope(df: pd.DataFrame, scope: Scope) -> pd.DataFrame:
    """scope에 따라 DataFrame 필터링."""
    if scope == "keep":
        return df[df["Decision"] == "Keep"]
    elif scope == "keep_maybe":
        return df[df["Decision"].isin(["Keep", "Maybe"])]
    return df


def export_bibtex(df: pd.DataFrame, decisions: dict) -> str:
    """Keep된 논문(또는 전체)을 BibTeX 문자열로 반환."""
    result = build_export_df(df)
    keep_df = result[result["Decision"] == "Keep"]

    entries = []
    for _, row in keep_df.iterrows():
        key = _make_citation_key(row)
        authors = str(row.get("Authors", "Unknown"))
        title = str(row.get("Title", ""))
        year = str(int(row["Year"])) if pd.notna(row.get("Year")) else "n.d."
        venue = str(row.get("Venue", "") or "")
        doi = str(row.get("DOI", "N/A"))
        url = str(row.get("URL", ""))
        paper_id = str(row.get("Paper ID", ""))

        lines = [f"@article{{{key},"]
        lines.append(f"  title     = {{{title}}},")
        lines.append(f"  author    = {{{authors}}},")
        lines.append(f"  year      = {{{year}}},")
        if venue:
            lines.append(f"  journal   = {{{venue}}},")
        if doi != "N/A" and doi.strip():
            lines.append(f"  doi       = {{{doi}}},")
        if url:
            lines.append(f"  url       = {{{url}}},")
        if doi == "N/A" or not doi.strip():
            lines.append(f"  note      = {{Semantic Scholar paper ID: {paper_id}}},")
        lines.append("}")
        entries.append("\n".join(lines))

    return "\n\n".join(entries)


def _make_citation_key(row: pd.Series) -> str:
    """BibTeX citation key 생성: {1저자성}{Year}{Title첫단어}."""
    authors = str(row.get("Authors", ""))
    first_author = authors.split(",")[0].strip().split()[-1] if authors else "unknown"
    year = str(int(row["Year"])) if pd.notna(row.get("Year")) else "nd"
    title = str(row.get("Title", ""))
    first_word = title.split()[0] if title else "untitled"

    key = f"{first_author}{year}{first_word}"
    # 특수문자 제거, 소문자
    key = re.sub(r"[^a-zA-Z0-9_]", "", key).lower()
    return key or "unknown"


def export_markdown(
    df: pd.DataFrame,
    decisions: dict,
    group_by: GroupBy = "year",
    filter_desc: str = "",
) -> str:
    """Keep된 논문을 Markdown 문자열로 반환."""
    result = build_export_df(df)
    keep_df = result[result["Decision"] == "Keep"].copy()

    today = date.today().isoformat()
    total = len(keep_df)

    header_lines = [
        f"# Literature Screening Results",
        f"",
        f"- **Export date**: {today}",
        f"- **Total kept**: {total}",
    ]
    if filter_desc:
        header_lines.append(f"- **Filters applied**: {filter_desc}")
    header_lines.append("")

    if keep_df.empty:
        return "\n".join(header_lines) + "\n\n_No papers marked as Keep._\n"

    grouped = _group_df(keep_df, group_by)
    body_lines = []

    for group_label, group_df in grouped:
        body_lines.append(f"## {group_label}")
        body_lines.append("")
        for _, row in group_df.iterrows():
            body_lines.append(_format_paper_bullet(row))
            body_lines.append("")

    return "\n".join(header_lines + body_lines)


def _group_df(df: pd.DataFrame, group_by: GroupBy) -> list[tuple[str, pd.DataFrame]]:
    """group_by 기준으로 DataFrame을 그룹화하여 (label, sub_df) 리스트 반환."""
    if group_by == "year":
        df = df.copy()
        df["_year_key"] = df["Year"].apply(lambda y: int(y) if pd.notna(y) else 0)
        groups = []
        for yr in sorted(df["_year_key"].unique(), reverse=True):
            label = str(yr) if yr != 0 else "Unknown Year"
            groups.append((label, df[df["_year_key"] == yr].drop(columns=["_year_key"])))
        return groups

    elif group_by == "venue":
        df = df.copy()
        df["_venue_key"] = df["Venue"].fillna("Unknown Venue").replace("", "Unknown Venue")
        groups = []
        for venue in sorted(df["_venue_key"].unique()):
            groups.append((venue, df[df["_venue_key"] == venue].drop(columns=["_venue_key"])))
        return groups

    elif group_by == "citation":
        df_sorted = df.sort_values("Citation Count", ascending=False)
        return [("By Citation Count (descending)", df_sorted)]

    elif group_by == "keyword":
        df = df.copy()
        df["_kw_key"] = df["Keyword"].fillna("Unknown Keyword")
        groups = []
        for kw in sorted(df["_kw_key"].unique()):
            groups.append((kw, df[df["_kw_key"] == kw].drop(columns=["_kw_key"])))
        return groups

    return [("All Papers", df)]


def _format_paper_bullet(row: pd.Series) -> str:
    """논문 1~2줄 bullet 포맷 생성."""
    title = str(row.get("Title", "Untitled"))
    year = str(int(row["Year"])) if pd.notna(row.get("Year")) else "n.d."
    authors_raw = str(row.get("Authors", ""))
    authors = _et_al(authors_raw)
    venue = str(row.get("Venue", "") or "")
    cites = int(row.get("Citation Count", 0))
    doi = str(row.get("DOI", "N/A"))
    reason = str(row.get("Reason", "") or "")

    doi_part = f"[DOI](https://doi.org/{doi})" if doi not in ("N/A", "", "nan") else "No DOI"
    venue_part = f"*{venue}*. " if venue else ""
    line1 = f"- **{title}** ({year})  "
    line2 = f"  {authors}. {venue_part}Cited by {cites}. {doi_part}  "

    if reason:
        line2 += f"\n  *{reason}*  "

    return line1 + "\n" + line2


def _et_al(authors: str, max_authors: int = 3) -> str:
    """저자 목록을 et al. 처리."""
    if not authors:
        return "Unknown"
    parts = [a.strip() for a in authors.split(",") if a.strip()]
    if len(parts) <= max_authors:
        return ", ".join(parts)
    return ", ".join(parts[:max_authors]) + " et al."
