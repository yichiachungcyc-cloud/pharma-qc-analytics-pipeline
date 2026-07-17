from __future__ import annotations

import os
import sqlite3
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".matplotlib").resolve()))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "sample_id",
    "batch_id",
    "product",
    "test_date",
    "replicate",
    "assay_result_pct",
    "spec_lower_pct",
    "spec_upper_pct",
    "analyst_id",
    "instrument_id",
}


def validate_input(df: pd.DataFrame) -> pd.DataFrame:
    """Validate schema and values without silently discarding regulated records."""
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Input dataset is empty")
    if df["sample_id"].isna().any() or df["sample_id"].duplicated().any():
        raise ValueError("sample_id must be present and unique")

    clean = df.copy()
    clean["test_date"] = pd.to_datetime(clean["test_date"], errors="coerce")
    numeric_columns = ["replicate", "assay_result_pct", "spec_lower_pct", "spec_upper_pct"]
    for column in numeric_columns:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    if clean[["test_date", *numeric_columns]].isna().any().any():
        raise ValueError("Invalid date or numeric values detected")
    if (clean["spec_lower_pct"] >= clean["spec_upper_pct"]).any():
        raise ValueError("Specification lower limit must be below upper limit")
    if (~clean["replicate"].between(1, 20)).any():
        raise ValueError("replicate is outside the expected range 1-20")
    return clean.sort_values(["product", "test_date", "batch_id", "replicate"]).reset_index(drop=True)


def calculate_reference_limits(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate product-level 3-sigma limits from in-spec observations."""
    in_spec = df[df["assay_result_pct"].between(df["spec_lower_pct"], df["spec_upper_pct"])]
    stats = (
        in_spec.groupby("product")["assay_result_pct"]
        .agg(reference_mean="mean", reference_sd="std", reference_n="count")
        .reset_index()
    )
    if (stats["reference_n"] < 2).any() or stats["reference_sd"].isna().any():
        raise ValueError("At least two in-spec observations per product are required")
    stats["control_lower_3sd"] = stats["reference_mean"] - 3 * stats["reference_sd"]
    stats["control_upper_3sd"] = stats["reference_mean"] + 3 * stats["reference_sd"]
    return stats


def analyse_results(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    validated = validate_input(df)
    limits = calculate_reference_limits(validated)
    analysed = validated.merge(limits, on="product", validate="many_to_one")

    analysed["is_oos"] = ~analysed["assay_result_pct"].between(
        analysed["spec_lower_pct"], analysed["spec_upper_pct"], inclusive="both"
    )
    outside_control = ~analysed["assay_result_pct"].between(
        analysed["control_lower_3sd"], analysed["control_upper_3sd"], inclusive="both"
    )
    analysed["is_oot"] = outside_control & ~analysed["is_oos"]
    analysed["qc_status"] = np.select(
        [analysed["is_oos"], analysed["is_oot"]], ["OOS", "OOT"], default="PASS"
    )

    batch_summary = (
        analysed.groupby(["product", "batch_id", "test_date"], as_index=False)
        .agg(
            mean_assay_pct=("assay_result_pct", "mean"),
            min_assay_pct=("assay_result_pct", "min"),
            max_assay_pct=("assay_result_pct", "max"),
            result_count=("sample_id", "count"),
            oos_count=("is_oos", "sum"),
            oot_count=("is_oot", "sum"),
        )
        .sort_values(["product", "test_date"])
    )
    batch_summary["batch_status"] = np.select(
        [batch_summary["oos_count"] > 0, batch_summary["oot_count"] > 0],
        ["OOS", "OOT"],
        default="PASS",
    )
    return analysed, batch_summary, limits


def write_sqlite(
    raw: pd.DataFrame,
    analysed: pd.DataFrame,
    batch_summary: pd.DataFrame,
    limits: pd.DataFrame,
    database_path: Path,
) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        raw.to_sql("raw_results", connection, if_exists="replace", index=False)
        analysed.to_sql("analysed_results", connection, if_exists="replace", index=False)
        batch_summary.to_sql("batch_summary", connection, if_exists="replace", index=False)
        limits.to_sql("product_control_limits", connection, if_exists="replace", index=False)
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sample_id ON raw_results(sample_id)")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_batch ON analysed_results(product, batch_id)"
        )


def plot_control_charts(analysed: pd.DataFrame, output_path: Path) -> None:
    products = list(analysed["product"].unique())
    fig, axes = plt.subplots(len(products), 1, figsize=(12, 4 * len(products)), squeeze=False)
    colours = {"PASS": "#2a9d8f", "OOT": "#f4a261", "OOS": "#e63946"}

    for axis, product in zip(axes.flat, products):
        subset = analysed[analysed["product"] == product].reset_index(drop=True)
        for status, group in subset.groupby("qc_status"):
            axis.scatter(group.index, group["assay_result_pct"], label=status, color=colours[status])
        first = subset.iloc[0]
        axis.axhline(first["reference_mean"], color="#264653", linestyle="--", label="Reference mean")
        axis.axhline(first["control_upper_3sd"], color="#f4a261", linestyle=":", label="3-sigma limits")
        axis.axhline(first["control_lower_3sd"], color="#f4a261", linestyle=":")
        axis.axhline(first["spec_upper_pct"], color="#e63946", linestyle="-.", label="Specification limits")
        axis.axhline(first["spec_lower_pct"], color="#e63946", linestyle="-.")
        axis.set(title=f"{product} assay monitoring", xlabel="Sequential observation", ylabel="Assay (%)")
        axis.grid(alpha=0.25)
        axis.legend(ncol=3)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
