from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.generate_data import generate_qc_data
from src.qc_pipeline import analyse_results


st.set_page_config(page_title="Pharmaceutical QC Analytics", layout="wide")
st.title("Pharmaceutical QC Analytics Dashboard")
st.caption("Synthetic portfolio data - not validated for operational GMP use")

analysed, batch_summary, limits = analyse_results(generate_qc_data())

selected_products = st.sidebar.multiselect(
    "Product", sorted(analysed["product"].unique()), default=sorted(analysed["product"].unique())
)
selected_statuses = st.sidebar.multiselect(
    "QC status", ["PASS", "OOT", "OOS"], default=["PASS", "OOT", "OOS"]
)

filtered = analysed[
    analysed["product"].isin(selected_products) & analysed["qc_status"].isin(selected_statuses)
].copy()
filtered_batches = batch_summary[batch_summary["product"].isin(selected_products)].copy()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Results", f"{len(filtered):,}")
col2.metric("Batches", f"{filtered_batches['batch_id'].nunique():,}")
col3.metric("OOS results", int((filtered["qc_status"] == "OOS").sum()))
col4.metric("OOT results", int((filtered["qc_status"] == "OOT").sum()))

st.subheader("Assay results and limits")
if filtered.empty:
    st.warning("No records match the selected filters.")
else:
    products = list(filtered["product"].unique())
    fig, axes = plt.subplots(len(products), 1, figsize=(12, 4 * len(products)), squeeze=False)
    colours = {"PASS": "#2a9d8f", "OOT": "#f4a261", "OOS": "#e63946"}
    for axis, product in zip(axes.flat, products):
        subset = filtered[filtered["product"] == product].reset_index(drop=True)
        for status, group in subset.groupby("qc_status"):
            axis.scatter(group.index, group["assay_result_pct"], label=status, color=colours[status])
        limit = limits[limits["product"] == product].iloc[0]
        specification = analysed[analysed["product"] == product].iloc[0]
        axis.axhline(limit["reference_mean"], color="#264653", linestyle="--", label="Mean")
        axis.axhline(limit["control_upper_3sd"], color="#f4a261", linestyle=":", label="3-sigma")
        axis.axhline(limit["control_lower_3sd"], color="#f4a261", linestyle=":")
        axis.axhline(specification["spec_upper_pct"], color="#e63946", linestyle="-.", label="Specification")
        axis.axhline(specification["spec_lower_pct"], color="#e63946", linestyle="-.")
        axis.set_title(product)
        axis.set_ylabel("Assay (%)")
        axis.grid(alpha=0.25)
        axis.legend(ncol=4)
    fig.tight_layout()
    st.pyplot(fig)

left, right = st.columns(2)
with left:
    st.subheader("Flagged results")
    st.dataframe(
        filtered.loc[filtered["qc_status"] != "PASS", [
            "sample_id", "batch_id", "product", "test_date", "assay_result_pct", "qc_status"
        ]],
        use_container_width=True,
        hide_index=True,
    )
with right:
    st.subheader("Batches requiring review")
    st.dataframe(
        filtered_batches.loc[filtered_batches["batch_status"] != "PASS"],
        use_container_width=True,
        hide_index=True,
    )

st.download_button(
    "Download filtered results",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_qc_results.csv",
    mime="text/csv",
)

