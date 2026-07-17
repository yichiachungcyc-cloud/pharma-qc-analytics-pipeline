from pathlib import Path

import pandas as pd

from src.generate_data import save_synthetic_data
from src.qc_pipeline import analyse_results, plot_control_charts, validate_input, write_sqlite


DATA_PATH = Path("data/synthetic_qc_results.csv")
OUTPUT_DIR = Path("outputs")


def main() -> None:
    # Recreate the synthetic input on every run so the workflow is reproducible.
    save_synthetic_data(DATA_PATH)

    raw = pd.read_csv(DATA_PATH)
    validated = validate_input(raw)
    analysed, batch_summary, limits = analyse_results(validated)

    OUTPUT_DIR.mkdir(exist_ok=True)
    analysed.to_csv(OUTPUT_DIR / "analysed_results.csv", index=False)
    batch_summary.to_csv(OUTPUT_DIR / "batch_summary.csv", index=False)
    write_sqlite(validated, analysed, batch_summary, limits, OUTPUT_DIR / "pharma_qc.db")
    plot_control_charts(analysed, OUTPUT_DIR / "control_charts.png")

    print(f"Analysed {len(analysed)} results across {batch_summary['batch_id'].nunique()} batches")
    print(analysed["qc_status"].value_counts().to_string())
    print(f"Outputs written to {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
