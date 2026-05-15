"""state.py 테스트 — 파일 로드/저장/컬럼 검증."""

import io
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from state import REQUIRED_COLUMNS, load_excel, save_to_excel

SAMPLE_PATH = Path("/root/.claude/uploads/81ff8d91-5a3d-4197-bece-363cc2d2eb9d/9cc2082b-IN625_corrosion_Tier1.xlsx")


def _sample_bytes() -> bytes:
    return SAMPLE_PATH.read_bytes()


def _make_df(**overrides) -> pd.DataFrame:
    """테스트용 최소 DataFrame."""
    base = {c: ["val"] for c in REQUIRED_COLUMNS}
    base["Year"] = [2023]
    base["Citation Count"] = [10]
    base.update(overrides)
    return pd.DataFrame(base)


# ── 정상 로드 ──────────────────────────────────

class TestLoadExcel:
    def test_loads_sample_file(self):
        df, err = load_excel(io.BytesIO(_sample_bytes()))
        assert err is None
        assert len(df) == 16

    def test_all_required_columns_present(self):
        df, err = load_excel(io.BytesIO(_sample_bytes()))
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"missing column: {col}"

    def test_decision_reason_columns_added(self):
        df, err = load_excel(io.BytesIO(_sample_bytes()))
        assert "Decision" in df.columns
        assert "Reason" in df.columns

    def test_all_decisions_default_undecided(self):
        df, _ = load_excel(io.BytesIO(_sample_bytes()))
        assert (df["Decision"] == "Undecided").all()

    def test_year_is_numeric(self):
        df, _ = load_excel(io.BytesIO(_sample_bytes()))
        assert pd.api.types.is_numeric_dtype(df["Year"])

    def test_citation_count_is_int(self):
        df, _ = load_excel(io.BytesIO(_sample_bytes()))
        assert df["Citation Count"].dtype in (int, "int64", "Int64")

    def test_paper_id_is_str(self):
        df, _ = load_excel(io.BytesIO(_sample_bytes()))
        # pandas 버전에 따라 object 또는 StringDtype 반환
        assert pd.api.types.is_string_dtype(df["Paper ID"]) or df["Paper ID"].dtype == object


# ── 컬럼 누락 에러 처리 ────────────────────────

class TestLoadExcelValidation:
    def test_missing_one_column_returns_error(self):
        df = _make_df()
        df = df.drop(columns=["Title"])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="Papers", index=False)
        buf.seek(0)
        _, err = load_excel(buf)
        assert err is not None
        assert "Title" in err

    def test_missing_multiple_columns_lists_all(self):
        df = _make_df()
        df = df.drop(columns=["Title", "Abstract", "DOI"])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="Papers", index=False)
        buf.seek(0)
        _, err = load_excel(buf)
        assert "Title" in err
        assert "Abstract" in err
        assert "DOI" in err

    def test_wrong_sheet_name_returns_error(self):
        df = _make_df()
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="WrongSheet", index=False)
        buf.seek(0)
        _, err = load_excel(buf)
        assert err is not None

    def test_non_excel_bytes_returns_error(self):
        _, err = load_excel(io.BytesIO(b"this is not an excel file"))
        assert err is not None

    def test_empty_bytes_returns_error(self):
        _, err = load_excel(io.BytesIO(b""))
        assert err is not None


# ── 이전 Decision 복원 ─────────────────────────

class TestDecisionRestoration:
    def test_existing_decision_column_preserved(self):
        df = _make_df()
        df["Decision"] = ["Keep"]
        df["Reason"] = ["good paper"]
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="Papers", index=False)
        buf.seek(0)
        loaded, _ = load_excel(buf)
        assert loaded.iloc[0]["Decision"] == "Keep"
        assert loaded.iloc[0]["Reason"] == "good paper"

    def test_invalid_decision_value_becomes_undecided(self):
        df = _make_df()
        df["Decision"] = ["InvalidStatus"]
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="Papers", index=False)
        buf.seek(0)
        loaded, _ = load_excel(buf)
        assert loaded.iloc[0]["Decision"] == "Undecided"

    def test_nan_decision_becomes_undecided(self):
        df = _make_df()
        df["Decision"] = [None]
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="Papers", index=False)
        buf.seek(0)
        loaded, _ = load_excel(buf)
        assert loaded.iloc[0]["Decision"] == "Undecided"


# ── 저장 라운드트립 ────────────────────────────

class TestSaveToExcel:
    def test_save_returns_bytes(self):
        df, _ = load_excel(io.BytesIO(_sample_bytes()))
        saved, err = save_to_excel(df, _sample_bytes(), "test.xlsx")
        assert err is None
        assert isinstance(saved, bytes)
        assert len(saved) > 0

    def test_saved_file_is_valid_excel(self):
        df, _ = load_excel(io.BytesIO(_sample_bytes()))
        saved, _ = save_to_excel(df, _sample_bytes(), "test.xlsx")
        reloaded, err = load_excel(io.BytesIO(saved))
        assert err is None
        assert len(reloaded) == len(df)

    def test_decision_persisted_on_reload(self):
        df, _ = load_excel(io.BytesIO(_sample_bytes()))
        df.loc[0, "Decision"] = "Keep"
        df.loc[0, "Reason"] = "important"
        saved, _ = save_to_excel(df, _sample_bytes(), "test.xlsx")
        reloaded, _ = load_excel(io.BytesIO(saved))
        assert reloaded.loc[0, "Decision"] == "Keep"
        assert reloaded.loc[0, "Reason"] == "important"
