from pathlib import Path

import numpy as np
import pandas as pd


PRODUCTS = {
    "API-A": {"target": 99.5, "sigma": 0.55, "lsl": 98.0, "usl": 102.0},
    "API-B": {"target": 100.0, "sigma": 0.70, "lsl": 97.5, "usl": 102.5},
}


def generate_qc_data(seed: int = 42, batches_per_product: int = 18) -> pd.DataFrame:
    """Create a reproducible synthetic assay dataset inspired by pharma QC workflows."""
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    start_date = pd.Timestamp("2025-01-06")

    for product_index, (product, cfg) in enumerate(PRODUCTS.items()):
        for batch_index in range(1, batches_per_product + 1):
            batch_id = f"{product}-{batch_index:03d}"
            batch_shift = rng.normal(0, cfg["sigma"] * 0.35)

            for replicate in range(1, 4):
                result = rng.normal(cfg["target"] + batch_shift, cfg["sigma"])
                rows.append(
                    {
                        "sample_id": f"S-{product_index + 1}{batch_index:03d}-{replicate}",
                        "batch_id": batch_id,
                        "product": product,
                        "test_date": start_date
                        + pd.Timedelta(days=(product_index * batches_per_product + batch_index) * 3),
                        "replicate": replicate,
                        "assay_result_pct": round(float(result), 3),
                        "spec_lower_pct": cfg["lsl"],
                        "spec_upper_pct": cfg["usl"],
                        "analyst_id": f"AN-{rng.integers(1, 5):02d}",
                        "instrument_id": f"HPLC-{rng.integers(1, 4):02d}",
                    }
                )

    df = pd.DataFrame(rows)

    # Deliberate signals make the portfolio analysis testable and explainable.
    df.loc[df["sample_id"] == "S-1008-2", "assay_result_pct"] = 101.95
    df.loc[df["sample_id"] == "S-1015-1", "assay_result_pct"] = 98.05
    df.loc[df["sample_id"] == "S-2006-3", "assay_result_pct"] = 103.10
    return df


def save_synthetic_data(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate_qc_data().to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    path = save_synthetic_data(Path("data/synthetic_qc_results.csv"))
    print(f"Synthetic dataset written to {path}")
