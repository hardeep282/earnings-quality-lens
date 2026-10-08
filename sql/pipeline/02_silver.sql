

-- Silver: typed, cleaned and conformed income statement + quality flags.
-- Reads bronze.income_statement and the ref.* seed tables written by src/pipeline.py.
-- Rules come from the Phase 2 cleaning plan and Phase 3 decision D3. Variable: tol (identity tolerance).

CREATE SCHEMA IF NOT EXISTS silver;

-- 'None' -> NULL, then CAST (not TRY_CAST): a malformed number must fail loudly, never become NULL silently
CREATE OR REPLACE MACRO silver.num(x) AS CAST(NULLIF(x, 'None') AS DOUBLE);

CREATE OR REPLACE TABLE silver.income_statement AS
WITH typed AS (
    SELECT
        symbol,
        CAST(fiscalDateEnding AS DATE)                              AS fiscal_date,
        COALESCE(NULLIF(reportedCurrency, 'None'), 'USD')          AS reported_currency,
        NULLIF(reportedCurrency, 'None') IS NULL                   AS currency_imputed,   -- PLTR 2019 (2 rows)
        silver.num(totalRevenue)                     AS total_revenue,
        silver.num(costOfRevenue)                    AS cost_of_revenue,       -- duplicate column dropped
        silver.num(grossProfit)                      AS gross_profit,
        silver.num(researchAndDevelopment)           AS research_and_development,
        silver.num(sellingGeneralAndAdministrative)  AS sga,
        silver.num(operatingExpenses)                AS operating_expenses,
        silver.num(operatingIncome)                  AS operating_income,
        silver.num(netInterestIncome)                AS net_interest_income,
        silver.num(interestIncome)                   AS interest_income,
        silver.num(interestExpense)                  AS interest_expense,
        silver.num(otherNonOperatingIncome)          AS other_non_operating_income,
        silver.num(depreciationAndAmortization)      AS depreciation_and_amortization,
        silver.num(incomeBeforeTax)                  AS income_before_tax,
        silver.num(incomeTaxExpense)                 AS income_tax_expense,
        silver.num(netIncomeFromContinuingOperations) AS net_income_continuing,
        silver.num(ebit)                             AS ebit,
        silver.num(ebitda)                           AS ebitda,
        silver.num(netIncome)                        AS net_income
    FROM bronze.income_statement
    -- 5 fully empty columns are simply not selected (Phase 2 cleaning plan)
),
calendar AS (
    SELECT *,
           fiscal_date - INTERVAL 45 DAY AS midpoint            -- midpoint rule (Phase 2)
    FROM typed
),
lagged AS (
    SELECT c.*,
           strftime(midpoint, '%Y') || 'Q' || quarter(midpoint)  AS calendar_quarter,
           year(midpoint) * 4 + quarter(midpoint)                AS q_idx,
           LAG(total_revenue)    OVER w AS prev_revenue,
           LAG(gross_profit)     OVER w AS prev_gross_profit,
           LAG(operating_income) OVER w AS prev_operating_income,
           LAG(net_income)       OVER w AS prev_net_income
    FROM calendar AS c
    WINDOW w AS (PARTITION BY symbol ORDER BY fiscal_date)
),
flagged AS (
    SELECT l.*,
           r.is_financial,
           -- Phase 2 row flags: any measure not in whole thousands / all four key measures copied
           COALESCE(list_bool_or([x % 1000 <> 0 FOR x IN [
               total_revenue, cost_of_revenue, gross_profit, research_and_development, sga,
               operating_expenses, operating_income, net_interest_income, interest_income,
               interest_expense, other_non_operating_income, depreciation_and_amortization,
               income_before_tax, income_tax_expense, net_income_continuing, ebit, ebitda, net_income]
               IF x IS NOT NULL]), false)                                         AS is_derived_row,
           COALESCE(total_revenue = prev_revenue AND gross_profit = prev_gross_profit
                    AND operating_income = prev_operating_income
                    AND net_income = prev_net_income, false)                      AS is_repeated,
           -- Phase 3 D3 field-level flags for the North Star inputs
           COALESCE(total_revenue % 1000 <> 0, false)
               OR COALESCE(operating_income % 1000 <> 0, false)                    AS is_derived_input,
           COALESCE(total_revenue = prev_revenue AND total_revenue <> 0, false)
               AND NOT COALESCE(abs(gross_profit - (total_revenue - cost_of_revenue))
                                / abs(total_revenue) <= getvariable('tol'), false) AS stale_revenue,
           COALESCE(operating_income = prev_operating_income AND operating_income <> 0, false)
               AND NOT COALESCE(abs(operating_income - (gross_profit - operating_expenses))
                                / abs(total_revenue) <= getvariable('tol'), false) AS stale_oi,
           total_revenue IS NULL OR operating_income IS NULL                      AS is_missing_input,
           EXISTS (SELECT 1 FROM ref.manual_exclusion AS m
                   WHERE m.symbol = l.symbol
                     AND l.fiscal_date BETWEEN m.first_date AND m.last_date)        AS is_manual
    FROM lagged AS l
    LEFT JOIN ref.company AS r USING (symbol)
)
SELECT * EXCLUDE (midpoint, prev_revenue, prev_gross_profit, prev_operating_income, prev_net_income),
       is_derived_row OR is_repeated                                              AS exclude_from_modelling,
       NOT (is_repeated OR is_derived_input OR stale_revenue OR stale_oi
            OR is_missing_input OR is_manual)                                     AS input_valid
FROM flagged
ORDER BY symbol, fiscal_date;