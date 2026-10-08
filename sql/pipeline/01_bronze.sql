

-- Bronze: the raw CSV exactly as delivered (every column kept as text), plus a load log.
-- Variables set by src/pipeline.py: raw_path, raw_sha256.

CREATE SCHEMA IF NOT EXISTS bronze;

CREATE OR REPLACE TABLE bronze.income_statement AS
SELECT *
FROM read_csv(getvariable('raw_path'), header = true, all_varchar = true);

CREATE TABLE IF NOT EXISTS bronze.load_log (
    loaded_at   TIMESTAMP,
    source_file VARCHAR,
    sha256      VARCHAR,
    row_count   BIGINT
);

INSERT INTO bronze.load_log
SELECT current_timestamp, getvariable('raw_path'), getvariable('raw_sha256'),
       (SELECT count(*) FROM bronze.income_statement);