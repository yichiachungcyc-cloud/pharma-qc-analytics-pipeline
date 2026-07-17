import pandas as pd
import pytest

from src.generate_data import generate_qc_data
from src.qc_pipeline import analyse_results, validate_input


def test_generated_dataset_is_reproducible() -> None:
    pd.testing.assert_frame_equal(generate_qc_data(seed=7), generate_qc_data(seed=7))


def test_validation_rejects_duplicate_sample_id() -> None:
    df = generate_qc_data()
    df.loc[1, "sample_id"] = df.loc[0, "sample_id"]
    with pytest.raises(ValueError, match="unique"):
        validate_input(df)


def test_validation_rejects_missing_column() -> None:
    df = generate_qc_data().drop(columns="batch_id")
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_input(df)


def test_known_out_of_specification_result_is_flagged() -> None:
    analysed, _, _ = analyse_results(generate_qc_data())
    status = analysed.loc[analysed["sample_id"] == "S-2006-3", "qc_status"].item()
    assert status == "OOS"


def test_known_out_of_trend_result_is_flagged() -> None:
    analysed, _, _ = analyse_results(generate_qc_data())
    status = analysed.loc[analysed["sample_id"] == "S-1008-2", "qc_status"].item()
    assert status == "OOT"


def test_batch_summary_preserves_all_batches() -> None:
    df = generate_qc_data(batches_per_product=5)
    analysed, batch_summary, _ = analyse_results(df)
    assert len(analysed) == len(df)
    assert batch_summary["batch_id"].nunique() == 10
