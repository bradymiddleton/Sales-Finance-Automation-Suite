-- ============================================================
-- Middleton Finance Suite — SQL Analysis Queries
-- ============================================================
-- Databases:
--   pricing_rebates.db  → transactions, rebate_tiers, discount_plan
--   deal_pipeline.db    → deals, deal_scores, approvals
--   channel_sales.db    → rep_performance, quota_plan, monthly_actuals
--
-- Run via:  python 04_run_queries.py
-- ============================================================


-- ────────────────────────────────────────────
-- SECTION 1: PRICING & REBATE ANALYSIS
-- Database: pricing_rebates.db
-- ────────────────────────────────────────────

-- 1A. Discount rate actual vs. plan by product category
--     Identifies which categories are over- or under-discounting vs. budget
SELECT
    product_category,
    COUNT(*)                                        AS total_orders,
    ROUND(SUM(net_revenue) / 1e6, 2)               AS net_revenue_mm,
    ROUND(AVG(discount_rate) * 100, 2)             AS actual_disc_pct,
    ROUND(AVG(plan_discount_rate) * 100, 2)        AS plan_disc_pct,
    ROUND((AVG(discount_rate) - AVG(plan_discount_rate)) * 100, 2)
                                                    AS variance_pp,
    ROUND(AVG(gross_margin_pct) * 100, 2)          AS actual_gm_pct
FROM transactions
GROUP BY product_category
ORDER BY variance_pp DESC;


-- 1B. Quarterly discount trend — FY2024
--     Used for QBR variance commentary and finance deck
SELECT
    quarter,
    COUNT(*)                                        AS orders,
    ROUND(SUM(net_revenue) / 1e6, 2)               AS net_revenue_mm,
    ROUND(AVG(discount_rate) * 100, 2)             AS actual_disc_pct,
    ROUND(AVG(plan_discount_rate) * 100, 2)        AS plan_disc_pct,
    ROUND((AVG(discount_rate) - AVG(plan_discount_rate)) * 100, 2)
                                                    AS variance_pp,
    ROUND(AVG(gross_margin_pct) * 100, 2)          AS avg_gm_pct
FROM transactions
WHERE quarter LIKE '%2024%'
GROUP BY quarter
ORDER BY quarter;


-- 1C. Top 5 channel partners by average discount rate
--     Flags partners receiving aggressive pricing concessions
SELECT
    channel_partner,
    COUNT(*)                                        AS orders,
    ROUND(AVG(discount_rate) * 100, 2)             AS avg_disc_pct,
    ROUND(SUM(discount_amount) / 1e6, 2)           AS total_discount_mm,
    ROUND(SUM(net_revenue) / 1e6, 2)               AS net_revenue_mm,
    ROUND(AVG(gross_margin_pct) * 100, 2)          AS avg_gm_pct
FROM transactions
GROUP BY channel_partner
ORDER BY avg_disc_pct DESC
LIMIT 10;


-- 1D. Gross margin miss vs. target by category
--     Targets defined in assumptions: GPUs 35%, CPUs 38%, Embedded 42%,
--     Semi-Custom 28%, Adaptive Computing 40%
SELECT
    product_category,
    ROUND(AVG(gross_margin_pct) * 100, 2)          AS actual_gm_pct,
    CASE product_category
        WHEN 'GPUs'               THEN 35.0
        WHEN 'CPUs'               THEN 38.0
        WHEN 'Embedded'           THEN 42.0
        WHEN 'Semi-Custom'        THEN 28.0
        WHEN 'Adaptive Computing' THEN 40.0
    END                                             AS target_gm_pct,
    ROUND(AVG(gross_margin_pct) * 100, 2) -
    CASE product_category
        WHEN 'GPUs'               THEN 35.0
        WHEN 'CPUs'               THEN 38.0
        WHEN 'Embedded'           THEN 42.0
        WHEN 'Semi-Custom'        THEN 28.0
        WHEN 'Adaptive Computing' THEN 40.0
    END                                             AS gm_gap_pp
FROM transactions
GROUP BY product_category
ORDER BY gm_gap_pp ASC;


-- 1E. Estimated rebate accrual by partner (Gold 5%, Silver 3%, Bronze 1.5%)
--     Joins transactions to rebate_tiers to compute accrued liability
SELECT
    t.channel_partner,
    r.tier,
    ROUND(SUM(t.net_revenue) / 1e6, 2)             AS net_revenue_mm,
    CASE r.tier
        WHEN 'Gold'   THEN 0.050
        WHEN 'Silver' THEN 0.030
        WHEN 'Bronze' THEN 0.015
    END                                             AS rebate_rate,
    ROUND(SUM(t.net_revenue) *
        CASE r.tier
            WHEN 'Gold'   THEN 0.050
            WHEN 'Silver' THEN 0.030
            WHEN 'Bronze' THEN 0.015
        END / 1000, 1)                              AS accrued_rebate_k,
    r.mdf_eligible
FROM transactions t
JOIN rebate_tiers r ON t.channel_partner = r.channel_partner
GROUP BY t.channel_partner, r.tier, r.mdf_eligible
ORDER BY accrued_rebate_k DESC;


-- 1F. Region-level pricing discipline summary
--     Useful for regional finance review meetings
SELECT
    region,
    segment,
    COUNT(*)                                        AS orders,
    ROUND(AVG(discount_rate) * 100, 2)             AS avg_disc_pct,
    ROUND(AVG(gross_margin_pct) * 100, 2)          AS avg_gm_pct,
    ROUND(SUM(net_revenue) / 1e6, 2)               AS net_revenue_mm,
    ROUND(SUM(discount_amount) / 1e6, 2)           AS total_discount_mm
FROM transactions
GROUP BY region, segment
ORDER BY region, avg_disc_pct DESC;


-- ────────────────────────────────────────────
-- SECTION 2: DEAL PIPELINE & APPROVAL ANALYSIS
-- Database: deal_pipeline.db
-- ────────────────────────────────────────────

-- 2A. Pipeline summary by deal stage with weighted value
--     Core pipeline health metric for finance reporting
SELECT
    deal_stage,
    COUNT(*)                                        AS deal_count,
    ROUND(SUM(net_deal_value) / 1e6, 2)            AS total_pipeline_mm,
    ROUND(SUM(weighted_pipeline_value) / 1e6, 2)   AS weighted_pipeline_mm,
    ROUND(AVG(discount_rate) * 100, 2)             AS avg_disc_pct,
    ROUND(AVG(gm_pct) * 100, 2)                    AS avg_gm_pct,
    ROUND(AVG(win_probability) * 100, 1)           AS avg_win_prob_pct
FROM deals
GROUP BY deal_stage
ORDER BY total_pipeline_mm DESC;


-- 2B. Deal approval distribution by composite score band
--     Shows how many deals fall into Auto-Approve / Escalate / Reject
SELECT
    s.recommendation,
    COUNT(*)                                        AS deal_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1)
                                                    AS pct_of_pipeline,
    ROUND(AVG(s.composite_score), 2)               AS avg_score,
    ROUND(SUM(d.net_deal_value) / 1e6, 2)          AS total_value_mm,
    ROUND(AVG(d.gm_pct) * 100, 2)                  AS avg_gm_pct
FROM deal_scores s
JOIN deals d ON s.deal_id = d.deal_id
GROUP BY s.recommendation
ORDER BY avg_score DESC;


-- 2C. High-value deals pending escalation
--     Prioritized list for VP review — largest deals needing sign-off
SELECT
    d.deal_id,
    d.rep_name,
    d.region,
    d.deal_stage,
    d.product_category,
    ROUND(d.net_deal_value / 1000, 0)              AS net_value_k,
    ROUND(d.discount_rate * 100, 1)                AS disc_pct,
    ROUND(d.gm_pct * 100, 1)                       AS gm_pct,
    s.composite_score,
    s.recommendation
FROM deals d
JOIN deal_scores s ON d.deal_id = s.deal_id
WHERE s.recommendation = 'Escalate'
  AND d.deal_stage NOT IN ('Closed Won', 'Closed Lost')
ORDER BY d.net_deal_value DESC
LIMIT 15;


-- 2D. Win/loss analysis by loss reason
--     Informs competitive strategy and pricing policy calibration
SELECT
    loss_reason,
    COUNT(*)                                        AS lost_deals,
    ROUND(SUM(net_deal_value) / 1e6, 2)            AS lost_pipeline_mm,
    ROUND(AVG(discount_rate) * 100, 2)             AS avg_disc_pct,
    ROUND(AVG(gm_pct) * 100, 2)                    AS avg_gm_pct
FROM deals
WHERE deal_stage = 'Closed Lost'
  AND loss_reason IS NOT NULL
GROUP BY loss_reason
ORDER BY lost_pipeline_mm DESC;


-- 2E. Rep-level deal scoring performance
--     Identifies reps whose deals consistently require escalation
SELECT
    d.rep_name,
    d.region,
    COUNT(*)                                        AS total_deals,
    ROUND(AVG(s.composite_score), 2)               AS avg_score,
    COUNT(CASE WHEN s.recommendation = 'Approve'  THEN 1 END)  AS auto_approved,
    COUNT(CASE WHEN s.recommendation = 'Escalate' THEN 1 END)  AS escalated,
    COUNT(CASE WHEN s.recommendation = 'Reject'   THEN 1 END)  AS rejected,
    ROUND(AVG(d.discount_rate) * 100, 2)           AS avg_disc_pct,
    ROUND(AVG(d.gm_pct) * 100, 2)                  AS avg_gm_pct
FROM deals d
JOIN deal_scores s ON d.deal_id = s.deal_id
GROUP BY d.rep_name, d.region
ORDER BY escalated DESC;


-- ────────────────────────────────────────────
-- SECTION 3: CHANNEL SALES PERFORMANCE
-- Database: channel_sales.db
-- ────────────────────────────────────────────

-- 3A. Full rep scorecard — quota attainment ranked
--     Primary input for QBR deck and comp planning
SELECT
    rep_name,
    region,
    segment,
    ROUND(annual_quota / 1e6, 2)                   AS quota_mm,
    ROUND(actual_revenue / 1e6, 2)                 AS actual_mm,
    ROUND(quota_attainment_pct * 100, 1)           AS attainment_pct,
    ROUND((actual_revenue - annual_quota) / 1e6, 2)
                                                    AS variance_to_quota_mm,
    ROUND(avg_deal_size / 1000, 0)                 AS avg_deal_k,
    ROUND(win_rate * 100, 1)                        AS win_rate_pct,
    ROUND(avg_discount_rate * 100, 1)              AS avg_disc_pct,
    ROUND(avg_gross_margin_pct * 100, 1)           AS avg_gm_pct
FROM rep_performance
ORDER BY attainment_pct DESC;


-- 3B. Regional performance summary
--     Aggregated attainment and margin by region for executive reporting
SELECT
    region,
    COUNT(*)                                        AS rep_count,
    ROUND(SUM(annual_quota) / 1e6, 2)              AS total_quota_mm,
    ROUND(SUM(actual_revenue) / 1e6, 2)            AS total_actual_mm,
    ROUND(AVG(quota_attainment_pct) * 100, 1)      AS avg_attainment_pct,
    ROUND(AVG(win_rate) * 100, 1)                   AS avg_win_rate_pct,
    ROUND(AVG(avg_discount_rate) * 100, 1)         AS avg_disc_pct,
    ROUND(AVG(avg_gross_margin_pct) * 100, 1)      AS avg_gm_pct
FROM rep_performance
GROUP BY region
ORDER BY avg_attainment_pct DESC;


-- 3C. Month-end close variance — Q4 2024
--     Actual vs. plan by rep for each month of Q4
SELECT
    month,
    rep_name,
    region,
    ROUND(plan_revenue / 1000, 1)                  AS plan_k,
    ROUND(actual_revenue / 1000, 1)                AS actual_k,
    ROUND(variance_vs_plan / 1000, 1)              AS variance_k,
    ROUND(variance_pct * 100, 1)                   AS variance_pct,
    ROUND(actual_discount_rate * 100, 1)           AS disc_pct,
    ROUND(actual_gm_pct * 100, 1)                  AS gm_pct,
    CASE WHEN variance_vs_plan >= 0 THEN 'Beat' ELSE 'Miss' END
                                                    AS close_status
FROM monthly_actuals
WHERE month IN ('2024-10', '2024-11', '2024-12')
ORDER BY month, variance_vs_plan ASC;


-- 3D. Team-level monthly revenue trend — FY2024
--     Aggregated actuals vs. plan for all 12 months
SELECT
    month,
    ROUND(SUM(actual_revenue) / 1e6, 2)            AS team_actual_mm,
    ROUND(SUM(plan_revenue) / 1e6, 2)              AS team_plan_mm,
    ROUND(SUM(variance_vs_plan) / 1e6, 2)          AS team_variance_mm,
    ROUND(AVG(actual_discount_rate) * 100, 2)      AS avg_disc_pct,
    ROUND(AVG(actual_gm_pct) * 100, 2)             AS avg_gm_pct
FROM monthly_actuals
WHERE month LIKE '2024%'
GROUP BY month
ORDER BY month;


-- 3E. Quota pacing — actual vs. quarterly plan by rep
--     Used mid-quarter to identify reps at risk of missing quota
SELECT
    q.rep_name,
    q.region,
    q.quarter,
    ROUND(q.quarterly_quota / 1000, 1)             AS quarterly_quota_k,
    ROUND(q.plan_discount_rate * 100, 1)           AS plan_disc_pct,
    ROUND(q.plan_gm_pct * 100, 1)                  AS plan_gm_pct,
    r.quota_attainment_pct * 100                   AS fy_attainment_pct
FROM quota_plan q
JOIN rep_performance r ON q.rep_name = r.rep_name
WHERE q.quarter LIKE '%2024%'
ORDER BY q.rep_name, q.quarter;


-- ────────────────────────────────────────────
-- SECTION 4: CROSS-DATABASE SUMMARY
-- Combines key metrics across all three databases
-- Note: Run each block against its respective database
-- ────────────────────────────────────────────

-- 4A. Pricing health snapshot (pricing_rebates.db)
SELECT
    'FY2024 Blended Discount Rate'         AS metric,
    ROUND(AVG(discount_rate) * 100, 2) || '%' AS value
FROM transactions WHERE quarter LIKE '%2024%'
UNION ALL
SELECT
    'FY2024 Blended Gross Margin',
    ROUND(AVG(gross_margin_pct) * 100, 2) || '%'
FROM transactions WHERE quarter LIKE '%2024%'
UNION ALL
SELECT
    'FY2024 Total Net Revenue ($M)',
    ROUND(SUM(net_revenue) / 1e6, 2)
FROM transactions WHERE quarter LIKE '%2024%'
UNION ALL
SELECT
    'FY2024 Total Discount Given ($M)',
    ROUND(SUM(discount_amount) / 1e6, 2)
FROM transactions WHERE quarter LIKE '%2024%';


-- 4B. Deal pipeline health snapshot (deal_pipeline.db)
SELECT
    'Total Pipeline Value ($M)'            AS metric,
    ROUND(SUM(net_deal_value) / 1e6, 2)   AS value
FROM deals
UNION ALL
SELECT
    'Weighted Pipeline Value ($M)',
    ROUND(SUM(weighted_pipeline_value) / 1e6, 2)
FROM deals
UNION ALL
SELECT
    'Auto-Approve Rate (%)',
    ROUND(COUNT(CASE WHEN recommendation = 'Approve' THEN 1 END) * 100.0 / COUNT(*), 1)
FROM deal_scores
UNION ALL
SELECT
    'Closed Won Revenue ($M)',
    ROUND(SUM(net_deal_value) / 1e6, 2)
FROM deals WHERE deal_stage = 'Closed Won';


-- 4C. Channel performance snapshot (channel_sales.db)
SELECT
    'Team Total Revenue ($M)'              AS metric,
    ROUND(SUM(actual_revenue) / 1e6, 2)   AS value
FROM rep_performance
UNION ALL
SELECT
    'Avg Quota Attainment (%)',
    ROUND(AVG(quota_attainment_pct) * 100, 1)
FROM rep_performance
UNION ALL
SELECT
    'Reps At or Above Quota',
    COUNT(CASE WHEN quota_attainment_pct >= 1.0 THEN 1 END)
FROM rep_performance
UNION ALL
SELECT
    'Team Avg Gross Margin (%)',
    ROUND(AVG(avg_gross_margin_pct) * 100, 1)
FROM rep_performance;
