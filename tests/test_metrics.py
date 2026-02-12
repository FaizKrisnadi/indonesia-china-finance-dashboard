from __future__ import annotations

import pandas as pd

from src.metrics import (
    add_realization_rate,
    add_time_to_implementation_days,
    compute_status_risk_index,
    province_year_exposure,
    sector_concentration_shares,
)


def test_realization_rate_handles_zero_and_missing_values() -> None:
    frame = pd.DataFrame(
        {
            "committed_usd": [100.0, 0.0, None],
            "disbursed_usd": [50.0, 10.0, 20.0],
        }
    )

    result = add_realization_rate(frame)

    assert result.loc[0, "realization_rate"] == 0.5
    assert pd.isna(result.loc[1, "realization_rate"])
    assert pd.isna(result.loc[2, "realization_rate"])


def test_time_to_implementation_days_handles_missing_dates() -> None:
    frame = pd.DataFrame(
        {
            "approval_date": ["2020-01-01", None, "2021-01-01"],
            "operation_date": ["2020-01-11", "2020-02-01", None],
        }
    )

    result = add_time_to_implementation_days(frame)

    assert result.loc[0, "time_to_implementation_days"] == 10
    assert pd.isna(result.loc[1, "time_to_implementation_days"])
    assert pd.isna(result.loc[2, "time_to_implementation_days"])


def test_province_year_exposure_excludes_cancelled_and_stalled() -> None:
    frame = pd.DataFrame(
        {
            "province": ["A", "A", "A", "B"],
            "year": [2021, 2021, 2021, 2021],
            "disbursed_usd": [100.0, 50.0, 20.0, 40.0],
            "status": ["operational", "cancelled", "stalled", "delayed"],
        }
    )

    exposure = province_year_exposure(frame)

    row_a = exposure[(exposure["province"] == "A") & (exposure["year"] == 2021)].iloc[0]
    row_b = exposure[(exposure["province"] == "B") & (exposure["year"] == 2021)].iloc[0]

    assert row_a["province_year_exposure"] == 100.0
    assert row_b["province_year_exposure"] == 40.0


def test_status_risk_index_uses_default_weights() -> None:
    frame = pd.DataFrame(
        {
            "status": ["cancelled", "stalled", "delayed", "operational"],
            "committed_usd": [100.0, 100.0, 100.0, 100.0],
        }
    )

    risk_index = compute_status_risk_index(frame)

    assert risk_index is not None
    assert round(risk_index, 2) == 57.5


def test_sector_concentration_handles_zero_total_value() -> None:
    frame = pd.DataFrame(
        {
            "sector": ["Energy", "Transport"],
            "committed_usd": [0.0, 0.0],
        }
    )

    concentration = sector_concentration_shares(frame)

    assert len(concentration) == 2
    assert concentration["share"].isna().all()
