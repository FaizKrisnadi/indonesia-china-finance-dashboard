from __future__ import annotations

import pandas as pd

RISK_WEIGHTS = {
    "cancelled": 1.0,
    "stalled": 0.8,
    "delayed": 0.5,
}


def _series_or_na(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([pd.NA] * len(frame), index=frame.index)


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def add_realization_rate(projects: pd.DataFrame) -> pd.DataFrame:
    enriched = projects.copy()
    committed = _to_numeric(_series_or_na(enriched, "committed_usd")).replace(0, pd.NA)
    disbursed = _to_numeric(_series_or_na(enriched, "disbursed_usd"))
    enriched["realization_rate"] = disbursed / committed
    return enriched


def overall_realization_rate(projects: pd.DataFrame) -> float | None:
    committed_total = _to_numeric(_series_or_na(projects, "committed_usd")).sum(min_count=1)
    disbursed_total = _to_numeric(_series_or_na(projects, "disbursed_usd")).sum(min_count=1)

    if pd.isna(committed_total) or committed_total == 0:
        return None
    if pd.isna(disbursed_total):
        return None

    return float(disbursed_total / committed_total)


def add_time_to_implementation_days(projects: pd.DataFrame) -> pd.DataFrame:
    enriched = projects.copy()
    approval = pd.to_datetime(_series_or_na(enriched, "approval_date"), errors="coerce")
    operation = pd.to_datetime(_series_or_na(enriched, "operation_date"), errors="coerce")
    enriched["time_to_implementation_days"] = (operation - approval).dt.days.astype("Int64")
    return enriched


def province_year_exposure(projects: pd.DataFrame) -> pd.DataFrame:
    province = _series_or_na(projects, "province").astype("string")
    disbursed = _to_numeric(_series_or_na(projects, "disbursed_usd")).fillna(0.0)
    status = _series_or_na(projects, "status").astype("string").str.lower()

    source_year = _to_numeric(_series_or_na(projects, "year"))
    approval_year = pd.to_datetime(_series_or_na(projects, "approval_date"), errors="coerce").dt.year
    year = source_year.fillna(approval_year).astype("Int64")

    active_mask = ~status.isin(["cancelled", "stalled"])

    exposure = pd.DataFrame(
        {
            "province": province,
            "year": year,
            "province_year_exposure": disbursed.where(active_mask, 0.0),
        }
    )
    exposure = exposure.dropna(subset=["province", "year"])

    if exposure.empty:
        return exposure

    grouped = (
        exposure.groupby(["province", "year"], as_index=False)["province_year_exposure"].sum()
        .sort_values(["province", "year"])
        .reset_index(drop=True)
    )
    return grouped


def sector_concentration_shares(
    projects: pd.DataFrame,
    value_column: str = "committed_usd",
) -> pd.DataFrame:
    sector = _series_or_na(projects, "sector").astype("string")
    values = _to_numeric(_series_or_na(projects, value_column))

    frame = pd.DataFrame({"sector": sector, "value": values}).dropna(subset=["sector"])
    if frame.empty:
        return pd.DataFrame(columns=["sector", "value", "share"])

    grouped = frame.groupby("sector", as_index=False)["value"].sum(min_count=1)
    total_value = grouped["value"].sum(min_count=1)

    if pd.isna(total_value) or total_value == 0:
        grouped["share"] = pd.NA
    else:
        grouped["share"] = grouped["value"] / total_value

    return grouped.sort_values("share", ascending=False, na_position="last").reset_index(drop=True)


def compute_status_risk_index(
    projects: pd.DataFrame,
    group_col: str | None = None,
    weights: dict[str, float] | None = None,
) -> float | None | pd.DataFrame:
    risk_weights = weights or RISK_WEIGHTS

    status = _series_or_na(projects, "status").astype("string").str.lower()
    weight = status.map(risk_weights).fillna(0.0)

    exposure = _to_numeric(_series_or_na(projects, "committed_usd"))
    exposure = exposure.where(exposure > 0, 1.0).fillna(1.0)

    risk_component = weight * exposure

    if group_col is None:
        denominator = exposure.sum(min_count=1)
        numerator = risk_component.sum(min_count=1)
        if pd.isna(denominator) or denominator == 0:
            return None
        return float((numerator / denominator) * 100)

    groups = _series_or_na(projects, group_col).astype("string")
    frame = pd.DataFrame(
        {
            group_col: groups,
            "risk_component": risk_component,
            "exposure": exposure,
        }
    ).dropna(subset=[group_col])

    if frame.empty:
        return pd.DataFrame(columns=[group_col, "status_risk_index"])

    grouped = frame.groupby(group_col, as_index=False).sum(numeric_only=True)
    grouped["status_risk_index"] = (
        (grouped["risk_component"] / grouped["exposure"]) * 100
    ).where(grouped["exposure"] > 0)

    return grouped[[group_col, "status_risk_index"]].sort_values(group_col).reset_index(drop=True)


def lifecycle_funnel(projects: pd.DataFrame) -> pd.DataFrame:
    stages = {
        "Approved": "approval_date",
        "Financial Close": "financial_close_date",
        "Construction Start": "construction_start_date",
        "Operation": "operation_date",
    }

    counts = []
    for stage, date_column in stages.items():
        values = pd.to_datetime(_series_or_na(projects, date_column), errors="coerce")
        counts.append({"stage": stage, "projects": int(values.notna().sum())})

    return pd.DataFrame(counts)


def approval_cohorts(projects: pd.DataFrame) -> pd.DataFrame:
    enriched = add_time_to_implementation_days(add_realization_rate(projects))

    approval_year = pd.to_datetime(_series_or_na(enriched, "approval_date"), errors="coerce").dt.year
    committed = _to_numeric(_series_or_na(enriched, "committed_usd"))
    disbursed = _to_numeric(_series_or_na(enriched, "disbursed_usd"))

    cohort = pd.DataFrame(
        {
            "approval_year": approval_year.astype("Int64"),
            "committed_usd": committed,
            "disbursed_usd": disbursed,
            "realization_rate": enriched["realization_rate"],
            "time_to_implementation_days": enriched["time_to_implementation_days"],
        }
    ).dropna(subset=["approval_year"])

    if cohort.empty:
        return pd.DataFrame(
            columns=[
                "approval_year",
                "projects",
                "committed_usd",
                "disbursed_usd",
                "avg_realization_rate",
                "median_time_to_implementation_days",
            ]
        )

    grouped = cohort.groupby("approval_year", as_index=False).agg(
        projects=("approval_year", "size"),
        committed_usd=("committed_usd", "sum"),
        disbursed_usd=("disbursed_usd", "sum"),
        avg_realization_rate=("realization_rate", "mean"),
        median_time_to_implementation_days=("time_to_implementation_days", "median"),
    )

    return grouped.sort_values("approval_year").reset_index(drop=True)


def delay_distribution(projects: pd.DataFrame) -> pd.Series:
    enriched = add_time_to_implementation_days(projects)
    delay_series = pd.to_numeric(
        enriched["time_to_implementation_days"],
        errors="coerce",
    ).dropna()
    return delay_series


def status_mix(projects: pd.DataFrame) -> pd.DataFrame:
    status = _series_or_na(projects, "status").astype("string")
    frame = status.value_counts(dropna=True).rename_axis("status").reset_index(name="projects")
    return frame.sort_values("projects", ascending=False).reset_index(drop=True)


def summarize_exposure_vs_friction(projects: pd.DataFrame) -> pd.DataFrame:
    exposure = province_year_exposure(projects)
    if exposure.empty:
        return pd.DataFrame(
            columns=[
                "province",
                "total_exposure",
                "avg_realization_rate",
                "status_risk_index",
                "exposure_band",
            ]
        )

    total_exposure = (
        exposure.groupby("province", as_index=False)["province_year_exposure"]
        .sum()
        .rename(columns={"province_year_exposure": "total_exposure"})
    )

    realized = add_realization_rate(projects)
    province_realization = (
        realized.groupby("province", as_index=False)["realization_rate"].mean().rename(
            columns={"realization_rate": "avg_realization_rate"}
        )
    )

    risk = compute_status_risk_index(projects, group_col="province")
    if isinstance(risk, float) or risk is None:
        risk = pd.DataFrame(columns=["province", "status_risk_index"])

    comparison = total_exposure.merge(province_realization, on="province", how="left")
    comparison = comparison.merge(risk, on="province", how="left")

    threshold = comparison["total_exposure"].median()
    comparison["exposure_band"] = comparison["total_exposure"].apply(
        lambda value: "High Exposure" if value >= threshold else "Low Exposure"
    )
    return comparison.sort_values("total_exposure", ascending=False).reset_index(drop=True)
