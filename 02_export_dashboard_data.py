"""
Middleton Finance Suite
Script 02: Export Dashboard Data

Reads from all three SQLite databases and writes a single data.js file
that all four HTML dashboards import. When the source data changes
(rerun 01_generate_and_load_data.py), rerun this script and all
dashboards update automatically on next browser open.

Usage:
    python 02_export_dashboard_data.py

Output:
    data.js  (same directory — dashboards import via <script src="data.js">)
"""

import sqlite3
import pandas as pd
import json
import os

DB_DIR = "databases"


def q(db_path, sql):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


def build_data():
    pricing_db = f"{DB_DIR}/pricing_rebates.db"
    deals_db   = f"{DB_DIR}/deal_pipeline.db"
    channel_db = f"{DB_DIR}/channel_sales.db"

    data = {}

    # ── PRICING ─────────────────────────────────────────────

    kpi = q(pricing_db, """
        SELECT
            ROUND(SUM(net_revenue)/1e9,3)           AS total_rev_b,
            ROUND(AVG(discount_rate)*100,2)          AS blended_disc,
            ROUND(AVG(gross_margin_pct)*100,2)       AS blended_gm,
            ROUND(SUM(net_revenue)*0.03/1e6,2)       AS rebate_accrual_mm,
            COUNT(DISTINCT channel_partner)          AS partner_count
        FROM transactions WHERE quarter LIKE '%2024%'
    """).iloc[0].to_dict()

    data["kpi_pricing"] = kpi

    data["by_category"] = q(pricing_db, """
        SELECT product_category,
            COUNT(*)                                     AS orders,
            ROUND(SUM(net_revenue)/1e6,2)               AS net_rev_mm,
            ROUND(AVG(discount_rate)*100,2)              AS act_disc,
            ROUND(AVG(plan_discount_rate)*100,2)         AS plan_disc,
            ROUND((AVG(discount_rate)-AVG(plan_discount_rate))*100,2) AS variance_pp,
            ROUND(AVG(gross_margin_pct)*100,2)           AS act_gm,
            CASE product_category
                WHEN 'GPUs'               THEN 35.0
                WHEN 'CPUs'               THEN 38.0
                WHEN 'Embedded'           THEN 42.0
                WHEN 'Semi-Custom'        THEN 28.0
                WHEN 'Adaptive Computing' THEN 40.0
            END                                          AS target_gm
        FROM transactions
        GROUP BY product_category
        ORDER BY net_rev_mm DESC
    """).to_dict(orient="records")

    data["by_quarter"] = q(pricing_db, """
        SELECT quarter,
            COUNT(*)                                     AS orders,
            ROUND(SUM(net_revenue)/1e6,2)               AS net_rev_mm,
            ROUND(AVG(discount_rate)*100,2)              AS act_disc,
            ROUND(AVG(plan_discount_rate)*100,2)         AS plan_disc,
            ROUND(AVG(gross_margin_pct)*100,2)           AS avg_gm
        FROM transactions WHERE quarter LIKE '%2024%'
        GROUP BY quarter ORDER BY quarter
    """).to_dict(orient="records")

    data["rebate_partners"] = q(pricing_db, """
        SELECT t.channel_partner, r.tier,
            ROUND(SUM(t.net_revenue)/1e6,2) AS net_rev_mm,
            CASE r.tier
                WHEN 'Gold'   THEN 0.05
                WHEN 'Silver' THEN 0.03
                ELSE 0.015
            END                             AS rebate_rate,
            CASE r.mdf_eligible WHEN 1 THEN 'Yes' ELSE 'No' END AS mdf_eligible
        FROM transactions t
        JOIN rebate_tiers r ON t.channel_partner = r.channel_partner
        GROUP BY t.channel_partner, r.tier, r.mdf_eligible
        ORDER BY net_rev_mm DESC
    """).to_dict(orient="records")

    # ── DEALS ────────────────────────────────────────────────

    kpi_d = q(deals_db, """
        SELECT
            ROUND(SUM(d.net_deal_value)/1e9,3)      AS pipeline_b,
            ROUND(SUM(d.weighted_pipeline_value)/1e6,1) AS weighted_mm,
            COUNT(CASE WHEN s.recommendation='Approve'  THEN 1 END) AS approved,
            COUNT(CASE WHEN s.recommendation='Escalate' THEN 1 END) AS escalated,
            COUNT(CASE WHEN s.recommendation='Reject'   THEN 1 END) AS rejected,
            ROUND(SUM(CASE WHEN d.deal_stage='Closed Won'
                      THEN d.net_deal_value END)/1e6,1)  AS closed_won_mm,
            COUNT(CASE WHEN d.deal_stage='Closed Won' THEN 1 END) AS closed_won_count,
            ROUND(AVG(CASE WHEN d.deal_stage='Closed Won'
                      THEN d.gm_pct END)*100,1)          AS closed_won_gm
        FROM deals d JOIN deal_scores s ON d.deal_id=s.deal_id
    """).iloc[0].to_dict()

    data["kpi_deals"] = kpi_d

    data["by_stage"] = q(deals_db, """
        SELECT deal_stage,
            COUNT(*)                                     AS deals,
            ROUND(SUM(net_deal_value)/1e6,2)            AS pipeline_mm,
            ROUND(AVG(gm_pct)*100,2)                    AS avg_gm,
            ROUND(AVG(win_probability)*100,1)           AS avg_win_prob
        FROM deals GROUP BY deal_stage
        ORDER BY pipeline_mm DESC
    """).to_dict(orient="records")

    data["approval_dist"] = q(deals_db, """
        SELECT s.recommendation,
            COUNT(*)                                     AS deals,
            ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(),1) AS pct,
            ROUND(AVG(s.composite_score),2)             AS avg_score,
            ROUND(SUM(d.net_deal_value)/1e6,2)          AS total_mm
        FROM deal_scores s JOIN deals d ON s.deal_id=d.deal_id
        GROUP BY s.recommendation ORDER BY avg_score DESC
    """).to_dict(orient="records")

    data["top_deals"] = q(deals_db, """
        SELECT d.deal_id, d.deal_stage, d.product_category, d.region,
            d.channel_partner,
            ROUND(d.net_deal_value/1000,0)              AS net_val_k,
            ROUND(d.discount_rate*100,1)                AS disc_pct,
            ROUND(d.gm_pct*100,1)                       AS gm_pct,
            ROUND(s.composite_score,1)                  AS score,
            s.recommendation
        FROM deals d JOIN deal_scores s ON d.deal_id=s.deal_id
        ORDER BY s.composite_score DESC LIMIT 30
    """).to_dict(orient="records")

    data["loss_reasons"] = q(deals_db, """
        SELECT loss_reason,
            COUNT(*)                                     AS lost_deals,
            ROUND(SUM(net_deal_value)/1e6,2)            AS lost_mm
        FROM deals
        WHERE deal_stage='Closed Lost' AND loss_reason IS NOT NULL
        GROUP BY loss_reason ORDER BY lost_mm DESC
    """).to_dict(orient="records")

    # ── CHANNEL ──────────────────────────────────────────────

    kpi_c = q(channel_db, """
        SELECT
            ROUND(SUM(actual_revenue)/1e6,1)            AS total_rev_mm,
            ROUND(AVG(quota_attainment_pct)*100,1)      AS avg_attainment,
            COUNT(CASE WHEN quota_attainment_pct>=1.0 THEN 1 END) AS reps_at_quota,
            COUNT(*)                                     AS total_reps,
            ROUND(AVG(avg_gross_margin_pct)*100,1)      AS avg_gm,
            ROUND(MAX(quota_attainment_pct)*100,1)      AS top_attainment
        FROM rep_performance
    """).iloc[0].to_dict()

    top_rep = q(channel_db, """
        SELECT rep_name FROM rep_performance
        ORDER BY quota_attainment_pct DESC LIMIT 1
    """).iloc[0]["rep_name"]

    kpi_c["top_rep"] = top_rep
    data["kpi_channel"] = kpi_c

    data["reps"] = q(channel_db, """
        SELECT rep_name, region, segment,
            ROUND(annual_quota/1e6,2)                   AS quota_mm,
            ROUND(actual_revenue/1e6,2)                 AS actual_mm,
            ROUND(quota_attainment_pct*100,1)           AS attainment,
            ROUND((actual_revenue-annual_quota)/1e6,2)  AS var_mm,
            ROUND(avg_deal_size/1000,0)                 AS avg_deal_k,
            ROUND(win_rate*100,1)                        AS win_rate,
            ROUND(avg_discount_rate*100,1)              AS disc_pct,
            ROUND(avg_gross_margin_pct*100,1)           AS gm_pct
        FROM rep_performance ORDER BY attainment DESC
    """).to_dict(orient="records")

    data["monthly"] = q(channel_db, """
        SELECT month,
            ROUND(SUM(actual_revenue)/1e6,2)            AS actual_mm,
            ROUND(SUM(plan_revenue)/1e6,2)              AS plan_mm,
            ROUND(SUM(variance_vs_plan)/1e6,2)          AS var_mm,
            ROUND(AVG(actual_discount_rate)*100,2)      AS disc_pct,
            ROUND(AVG(actual_gm_pct)*100,2)             AS gm_pct
        FROM monthly_actuals WHERE month LIKE '2024%'
        GROUP BY month ORDER BY month
    """).to_dict(orient="records")

    data["q4_close"] = q(channel_db, """
        SELECT month, rep_name, region,
            ROUND(plan_revenue/1000,1)                  AS plan_k,
            ROUND(actual_revenue/1000,1)                AS actual_k,
            ROUND(variance_vs_plan/1000,1)              AS var_k,
            ROUND(variance_pct*100,1)                   AS var_pct,
            ROUND(actual_discount_rate*100,1)           AS disc_pct,
            ROUND(actual_gm_pct*100,1)                  AS gm_pct
        FROM monthly_actuals
        WHERE month IN ('2024-10','2024-11','2024-12')
        ORDER BY month, rep_name
    """).to_dict(orient="records")

    data["by_region"] = q(channel_db, """
        SELECT region,
            COUNT(*)                                     AS reps,
            ROUND(AVG(quota_attainment_pct)*100,1)      AS avg_attainment,
            ROUND(SUM(actual_revenue)/1e6,2)            AS total_rev_mm,
            ROUND(AVG(avg_gross_margin_pct)*100,1)      AS avg_gm
        FROM rep_performance GROUP BY region
        ORDER BY avg_attainment DESC
    """).to_dict(orient="records")

    return data


def main():
    print("=" * 55)
    print("Middleton Finance Suite — Dashboard Data Export")
    print("=" * 55)

    if not os.path.exists(f"{DB_DIR}/pricing_rebates.db"):
        print("\n✗ Databases not found. Run 01_generate_and_load_data.py first.")
        return

    data = build_data()

    js = "// Middleton Finance Suite — Auto-generated by 02_export_dashboard_data.py\n"
    js += "// Do not edit manually. Rerun the script to refresh from source databases.\n\n"
    js += f"const MFS = {json.dumps(data, indent=2)};\n"

    with open("data.js", "w") as f:
        f.write(js)

    print(f"\n✓ data.js written successfully")
    print(f"  Pricing rows:  {len(data['by_category'])} categories, {len(data['by_quarter'])} quarters, {len(data['rebate_partners'])} partners")
    print(f"  Deal rows:     {len(data['by_stage'])} stages, {len(data['top_deals'])} scored deals")
    print(f"  Channel rows:  {len(data['reps'])} reps, {len(data['monthly'])} months, {len(data['q4_close'])} Q4 close rows")
    print(f"\n  Open index.html in a browser — all dashboards now reflect live data.")


if __name__ == "__main__":
    main()
