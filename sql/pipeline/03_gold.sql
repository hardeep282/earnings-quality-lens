

-- Gold: Kimball star schema + governed North Star views.
-- Fact grain: one row per company x fiscal quarter (= one calendar quarter per company; 0 collisions, Phase 2).
-- Parameters come from ref.kpi_parameter (a table), never session variables: views run in later sessions.

CREATE SCHEMA IF NOT EXISTS gold;

-- Dimension: company (surrogate key + attributes from the ref seed)
CREATE OR REPLACE TABLE gold.dim_company AS
SELECT row_number() OVER (ORDER BY r.symbol)  AS company_key,
       r.symbol, r.business_group, r.is_financial, r.is_non_us,
       s.reported_currency, r.kpi_caution,
       s.first_quarter, s.last_quarter
FROM ref.company AS r
JOIN (SELECT symbol, any_value(reported_currency) AS reported_currency,
             arg_min(calendar_quarter, q_idx) AS first_quarter,
             arg_max(calendar_quarter, q_idx) AS last_quarter
      FROM silver.income_statement GROUP BY symbol) AS s USING (symbol);

-- Dimension: calendar quarter (complete range, so gaps in the fact table stay visible)
CREATE OR REPLACE TABLE gold.dim_quarter AS
WITH bounds AS (SELECT min(q_idx) AS lo, max(q_idx) AS hi FROM silver.income_statement),
keys AS (SELECT unnest(range(lo, hi + 1)) AS quarter_key FROM bounds)
SELECT quarter_key,
       (quarter_key - 1) // 4                                                   AS calendar_year,
       (quarter_key - 1) % 4 + 1                                                AS quarter_of_year,
       ((quarter_key - 1) // 4)::VARCHAR || 'Q' || ((quarter_key - 1) % 4 + 1)::VARCHAR AS calendar_quarter,
       make_date(((quarter_key - 1) // 4)::BIGINT, ((quarter_key - 1) % 4 * 3 + 1)::BIGINT, 1) AS quarter_start
FROM keys;

-- Fact: income-statement measures at the declared grain (interest columns stay in Silver: Phase 2 rule)
CREATE OR REPLACE TABLE gold.fact_quarter AS
SELECT c.company_key, s.q_idx AS quarter_key, s.fiscal_date,
       s.total_revenue, s.cost_of_revenue, s.gross_profit, s.research_and_development, s.sga,
       s.operating_expenses, s.operating_income, s.depreciation_and_amortization,
       s.income_before_tax, s.income_tax_expense, s.ebit, s.ebitda, s.net_income,
       s.input_valid, s.exclude_from_modelling, s.currency_imputed
FROM silver.income_statement AS s
JOIN gold.dim_company AS c USING (symbol);

-- View: North Star per company-quarter (D1-D7), same logic as src/kpis.py
CREATE OR REPLACE VIEW gold.north_star AS
WITH ttm AS (
    SELECT company_key, quarter_key,
           SUM(CASE WHEN input_valid THEN operating_income END) OVER w AS oi_sum,
           SUM(CASE WHEN input_valid THEN total_revenue END)    OVER w AS rev_sum,
           COUNT(CASE WHEN input_valid THEN 1 END)              OVER w AS valid_quarters
    FROM gold.fact_quarter
    WINDOW w AS (PARTITION BY company_key ORDER BY quarter_key RANGE BETWEEN 3 PRECEDING AND CURRENT ROW)
),
grid AS (   -- every calendar quarter in each company's span, so gap quarters appear as rows (D2)
    SELECT c.company_key, q.quarter_key
    FROM gold.dim_company AS c
    JOIN (SELECT company_key, min(quarter_key) AS lo, max(quarter_key) AS hi
          FROM gold.fact_quarter GROUP BY company_key) AS b USING (company_key)
    JOIN gold.dim_quarter AS q ON q.quarter_key BETWEEN b.lo AND b.hi
),
ttm_ok AS (
    SELECT g.company_key, g.quarter_key,
           CASE WHEN t.valid_quarters = 4 THEN t.oi_sum END  AS ttm_oi,
           CASE WHEN t.valid_quarters = 4 THEN t.rev_sum END AS ttm_revenue
    FROM grid AS g
    LEFT JOIN ttm AS t USING (company_key, quarter_key)
),
paired AS (
    SELECT c.company_key, c.quarter_key, c.ttm_oi, c.ttm_revenue,
           b.ttm_oi AS base_ttm_oi, b.ttm_revenue AS base_ttm_revenue,
           c.ttm_oi / c.ttm_revenue AS ttm_margin,
           b.ttm_oi / b.ttm_revenue AS base_margin
    FROM ttm_ok AS c
    LEFT JOIN ttm_ok AS b ON b.company_key = c.company_key AND b.quarter_key = c.quarter_key - 4
),
labelled AS (
    SELECT *,
           100 * (ttm_margin - base_margin) AS margin_change_pp,
           CASE WHEN ttm_oi IS NULL OR base_ttm_oi IS NULL           THEN 'no TTM pair'
                WHEN base_ttm_oi <= 0 AND ttm_oi > 0                 THEN 'turned profitable'
                WHEN base_ttm_oi <= 0 AND ttm_oi > base_ttm_oi       THEN 'loss narrowed'
                WHEN base_ttm_oi <= 0                                THEN 'loss widened or flat'
                WHEN base_margin < (SELECT value FROM ref.kpi_parameter
                                    WHERE name = 'min_base_margin') THEN 'base margin below 2%'
                ELSE 'defined' END AS ns_status
    FROM paired
)
SELECT d.symbol, q.calendar_quarter, l.company_key, l.quarter_key,
       l.ttm_revenue, l.ttm_oi, l.base_ttm_revenue, l.base_ttm_oi,
       l.ttm_margin, l.base_margin, l.margin_change_pp, l.ns_status,
       CASE WHEN l.ns_status = 'defined' THEN l.ttm_oi / l.base_ttm_oi - 1 END AS ns_growth,
       CASE WHEN l.ns_status <> 'defined'                              THEN ''
            WHEN l.ttm_oi > l.base_ttm_oi AND l.margin_change_pp >= 0  THEN 'growth with margin up'
            WHEN l.ttm_oi > l.base_ttm_oi                              THEN 'growth with margin down'
            WHEN l.margin_change_pp >= 0                               THEN 'decline with margin up'
            ELSE 'decline with margin down' END AS quality_quadrant,
       COALESCE(d.kpi_caution, '') AS caution
FROM labelled AS l
JOIN gold.dim_company AS d USING (company_key)
JOIN gold.dim_quarter AS q USING (quarter_key);

-- View: like-for-like USD aggregate (D6): ratio of sums over companies with a TTM in both years
CREATE OR REPLACE VIEW gold.north_star_lfl AS
SELECT n.calendar_quarter,
       count(*)                               AS companies,
       sum(n.ttm_oi)                          AS ttm_oi,
       sum(n.base_ttm_oi)                     AS base_ttm_oi,
       CASE WHEN sum(n.base_ttm_oi) > 0 THEN sum(n.ttm_oi) / sum(n.base_ttm_oi) - 1 END AS ns_growth,
       sum(n.ttm_oi) / sum(n.ttm_revenue)     AS ttm_margin,
       100 * (sum(n.ttm_oi) / sum(n.ttm_revenue)
              - sum(n.base_ttm_oi) / sum(n.base_ttm_revenue)) AS margin_change_pp
FROM gold.north_star AS n
JOIN gold.dim_company AS d USING (company_key)
WHERE NOT d.is_non_us AND n.ttm_oi IS NOT NULL AND n.base_ttm_oi IS NOT NULL
GROUP BY n.calendar_quarter
ORDER BY n.calendar_quarter;