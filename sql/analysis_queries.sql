-- 1. Product-level OOS and OOT rates
SELECT
    product,
    COUNT(*) AS total_results,
    SUM(CASE WHEN qc_status = 'OOS' THEN 1 ELSE 0 END) AS oos_results,
    ROUND(100.0 * SUM(CASE WHEN qc_status = 'OOS' THEN 1 ELSE 0 END) / COUNT(*), 2) AS oos_rate_pct,
    SUM(CASE WHEN qc_status = 'OOT' THEN 1 ELSE 0 END) AS oot_results
FROM analysed_results
GROUP BY product;

-- 2. Batches requiring investigation
SELECT product, batch_id, test_date, mean_assay_pct, oos_count, oot_count, batch_status
FROM batch_summary
WHERE batch_status <> 'PASS'
ORDER BY test_date;

-- 3. Compare each batch with the previous batch using a window function
WITH ordered_batches AS (
    SELECT
        product,
        batch_id,
        test_date,
        mean_assay_pct,
        LAG(mean_assay_pct) OVER (PARTITION BY product ORDER BY test_date) AS previous_batch_mean
    FROM batch_summary
)
SELECT
    *,
    ROUND(mean_assay_pct - previous_batch_mean, 3) AS change_from_previous
FROM ordered_batches
ORDER BY product, test_date;

-- 4. Instrument-level data quality signal
SELECT
    instrument_id,
    COUNT(*) AS result_count,
    ROUND(AVG(assay_result_pct), 3) AS mean_assay_pct,
    SUM(CASE WHEN qc_status IN ('OOS', 'OOT') THEN 1 ELSE 0 END) AS flagged_results
FROM analysed_results
GROUP BY instrument_id
ORDER BY flagged_results DESC;

