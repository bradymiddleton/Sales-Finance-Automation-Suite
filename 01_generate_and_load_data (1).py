"""
Middleton Finance Suite
Script 01: Generate Synthetic Data & Load into SQLite Databases

Generates three realistic datasets modeled after public sales finance datasets:

  - Superstore Sales (Kaggle: vivek468/superstore-dataset-final)
    → pricing_rebates.db

  - CRM Sales Pipeline (Kaggle: agungpambudi/crm-sales-predictive-analytics)
    → deal_pipeline.db

  - Salesforce Quota Data (Kaggle: rahuldhanola/salesforce-sales-quota-data)
    → channel_sales.db

Each dataset mirrors real Kaggle schema but is fully synthetic for demo
portability — no Kaggle API key or authentication required.

Usage:
    python 01_generate_and_load_data.py

Outputs:
    databases/pricing_rebates.db
    databases/deal_pipeline.db
    databases/channel_sales.db
    exports/*.csv
"""

import sqlite3
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import os

fake = Faker()
np.random.seed(42)
random.seed(42)

DB_DIR     = "databases"
EXPORT_DIR = "exports"
os.makedirs(DB_DIR,     exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# SHARED REFERENCE DATA
# ─────────────────────────────────────────────

REGIONS   = ["West", "East", "Central", "South"]
SEGMENTS  = ["Enterprise", "Commercial", "Public Sector", "SMB"]

PRODUCT_CATEGORIES = ["GPUs", "CPUs", "Embedded", "Semi-Custom", "Adaptive Computing"]

PRODUCT_LINES = {
    "GPUs":               ["Instinct MI300X", "Instinct MI250", "Radeon RX 7900", "Radeon RX 7800", "Radeon PRO W7900"],
    "CPUs":               ["EPYC Genoa 9654", "EPYC Bergamo 9754", "Ryzen 9 7950X", "Ryzen Threadripper PRO"],
    "Embedded":           ["Versal AI Core", "Versal Premium", "Kria K26 SOM"],
    "Semi-Custom":        ["Xbox Custom APU", "PlayStation Custom APU", "Steam Deck APU"],
    "Adaptive Computing": ["Alveo U55C", "Alveo U250", "Alveo V80"],
}

CHANNEL_PARTNERS = [
    "Arrow Electronics", "Avnet", "TD Synnex", "Ingram Micro",
    "CDW", "Insight Direct", "SHI International", "Connection",
    "PC Mall Gov", "Presidio", "World Wide Technology", "Trace3",
]

REPS = [
    {"name": "Jordan Mitchell", "region": "West",    "segment": "Enterprise"},
    {"name": "Priya Nair",      "region": "West",    "segment": "Commercial"},
    {"name": "Marcus Chen",     "region": "East",    "segment": "Enterprise"},
    {"name": "Sofia Delgado",   "region": "East",    "segment": "Public Sector"},
    {"name": "Tyler Brooks",    "region": "Central", "segment": "SMB"},
    {"name": "Aisha Johnson",   "region": "Central", "segment": "Commercial"},
    {"name": "Kenji Tanaka",    "region": "South",   "segment": "Enterprise"},
    {"name": "Rachel Okafor",   "region": "South",   "segment": "Commercial"},
    {"name": "Derek Walsh",     "region": "West",    "segment": "Public Sector"},
    {"name": "Mei-Lin Park",    "region": "East",    "segment": "SMB"},
    {"name": "Carlos Rivera",   "region": "Central", "segment": "Enterprise"},
    {"name": "Natalie Frost",   "region": "South",   "segment": "SMB"},
]


def random_date(start_year=2023, end_year=2025):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year,   12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


# ─────────────────────────────────────────────
# DATABASE 1: pricing_rebates.db
# Tables: transactions, rebate_tiers, discount_plan
# ─────────────────────────────────────────────

def build_pricing_rebates_db():
    print("Building pricing_rebates.db ...")

    records = []
    base_price_map = {
        "GPUs":               (8000,  40000),
        "CPUs":               (3000,  12000),
        "Embedded":           (500,    4000),
        "Semi-Custom":        (1200,   6000),
        "Adaptive Computing": (2000,  18000),
    }
    cogs_pct_map = {
        "GPUs": 0.62, "CPUs": 0.58, "Embedded": 0.55,
        "Semi-Custom": 0.68, "Adaptive Computing": 0.60,
    }

    for i in range(4800):
        rep      = random.choice(REPS)
        category = random.choice(PRODUCT_CATEGORIES)
        product  = random.choice(PRODUCT_LINES[category])
        partner  = random.choice(CHANNEL_PARTNERS)

        lo, hi          = base_price_map[category]
        unit_list_price = round(random.uniform(lo, hi), 2)
        quantity        = random.randint(1, 50)

        base_discount = random.uniform(0.03, 0.08)
        if rep["segment"] == "Enterprise":
            base_discount += random.uniform(0.04, 0.12)
        if partner in ["Arrow Electronics", "Avnet", "TD Synnex", "Ingram Micro"]:
            base_discount += random.uniform(0.02, 0.06)
        discount_rate = min(round(base_discount, 4), 0.35)

        list_revenue    = round(unit_list_price * quantity, 2)
        discount_amount = round(list_revenue * discount_rate, 2)
        net_revenue     = round(list_revenue - discount_amount, 2)
        cogs            = round(unit_list_price * quantity * cogs_pct_map[category], 2)
        gross_profit    = round(net_revenue - cogs, 2)
        gross_margin_pct = round(gross_profit / net_revenue, 4) if net_revenue > 0 else 0

        order_date    = random_date(2023, 2025)
        quarter       = f"Q{((order_date.month - 1) // 3) + 1} {order_date.year}"
        plan_discount = min(round(base_discount * random.uniform(0.80, 1.10), 4), 0.35)

        records.append({
            "order_id":                  f"ORD-{10000 + i}",
            "order_date":                order_date.strftime("%Y-%m-%d"),
            "quarter":                   quarter,
            "rep_name":                  rep["name"],
            "region":                    rep["region"],
            "segment":                   rep["segment"],
            "channel_partner":           partner,
            "product_category":          category,
            "product_name":              product,
            "quantity":                  quantity,
            "unit_list_price":           unit_list_price,
            "list_revenue":              list_revenue,
            "discount_rate":             discount_rate,
            "discount_amount":           discount_amount,
            "net_revenue":               net_revenue,
            "cogs":                      cogs,
            "gross_profit":              gross_profit,
            "gross_margin_pct":          gross_margin_pct,
            "plan_discount_rate":        plan_discount,
            "discount_variance_vs_plan": round(discount_rate - plan_discount, 4),
        })

    df_tx = pd.DataFrame(records)

    rebate_tiers = []
    for partner in CHANNEL_PARTNERS:
        threshold = random.choice([500000, 1000000, 2500000, 5000000, 10000000])
        tier      = "Bronze" if threshold < 1000000 else "Silver" if threshold < 5000000 else "Gold"
        rebate_tiers.append({
            "channel_partner":          partner,
            "tier":                     tier,
            "annual_revenue_threshold": threshold,
            "rebate_pct_tier1":         round(random.uniform(0.01, 0.02), 3),
            "rebate_pct_tier2":         round(random.uniform(0.02, 0.04), 3),
            "rebate_pct_tier3":         round(random.uniform(0.04, 0.07), 3),
            "mdf_eligible":             random.choice([True, False]),
            "contract_start":           "2024-01-01",
            "contract_end":             "2024-12-31",
        })
    df_rebate = pd.DataFrame(rebate_tiers)

    plan_rows = []
    for year in [2023, 2024, 2025]:
        for q in [1, 2, 3, 4]:
            for cat in PRODUCT_CATEGORIES:
                plan_rows.append({
                    "quarter":               f"Q{q} {year}",
                    "product_category":      cat,
                    "plan_discount_rate":    round(random.uniform(0.08, 0.22), 4),
                    "plan_revenue":          round(random.uniform(2000000, 15000000), 2),
                    "plan_gross_margin_pct": round(random.uniform(0.28, 0.45), 4),
                })
    df_plan = pd.DataFrame(plan_rows)

    conn = sqlite3.connect(f"{DB_DIR}/pricing_rebates.db")
    df_tx.to_sql("transactions",  conn, if_exists="replace", index=False)
    df_rebate.to_sql("rebate_tiers",  conn, if_exists="replace", index=False)
    df_plan.to_sql("discount_plan",   conn, if_exists="replace", index=False)
    conn.close()

    df_tx.to_csv(f"{EXPORT_DIR}/transactions.csv",     index=False)
    df_rebate.to_csv(f"{EXPORT_DIR}/rebate_tiers.csv", index=False)
    df_plan.to_csv(f"{EXPORT_DIR}/discount_plan.csv",  index=False)

    print(f"  → {len(df_tx):,} transactions | {len(df_rebate)} rebate tiers | {len(df_plan)} plan rows")


# ─────────────────────────────────────────────
# DATABASE 2: deal_pipeline.db
# Tables: deals, deal_scores, approvals
# ─────────────────────────────────────────────

def build_deal_pipeline_db():
    print("Building deal_pipeline.db ...")

    DEAL_STAGES    = ["Prospect", "Qualified", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
    STAGE_WIN_PROB = {
        "Prospect": 0.10, "Qualified": 0.25, "Proposal": 0.45,
        "Negotiation": 0.70, "Closed Won": 1.0, "Closed Lost": 0.0,
    }
    LOSS_REASONS = ["Price", "Competition", "Budget cut", "No decision", "Technical fit", None]

    deals = []
    for i in range(1200):
        rep      = random.choice(REPS)
        category = random.choice(PRODUCT_CATEGORIES)
        product  = random.choice(PRODUCT_LINES[category])
        partner  = random.choice(CHANNEL_PARTNERS)
        stage    = random.choices(
            DEAL_STAGES, weights=[0.12, 0.18, 0.20, 0.15, 0.25, 0.10]
        )[0]

        deal_size      = round(random.uniform(50000, 5000000), 2)
        discount_rate  = round(random.uniform(0.05, 0.30), 4)
        net_deal_value = round(deal_size * (1 - discount_rate), 2)
        cogs_pct       = random.uniform(0.52, 0.72)
        gross_margin   = round(net_deal_value * (1 - cogs_pct), 2)
        gm_pct         = round(gross_margin / net_deal_value, 4) if net_deal_value > 0 else 0

        created_date    = random_date(2024, 2025)
        cycle_days      = random.randint(14, 180)
        win_prob        = round(max(0, min(1, STAGE_WIN_PROB[stage] + random.uniform(-0.05, 0.05))), 3)

        deals.append({
            "deal_id":                 f"DEAL-{5000 + i}",
            "created_date":            created_date.strftime("%Y-%m-%d"),
            "expected_close_date":     (created_date + timedelta(days=cycle_days)).strftime("%Y-%m-%d"),
            "rep_name":                rep["name"],
            "region":                  rep["region"],
            "segment":                 rep["segment"],
            "channel_partner":         partner,
            "product_category":        category,
            "product_name":            product,
            "deal_stage":              stage,
            "deal_size_list":          deal_size,
            "discount_rate":           discount_rate,
            "net_deal_value":          net_deal_value,
            "gross_margin":            gross_margin,
            "gm_pct":                  gm_pct,
            "win_probability":         win_prob,
            "weighted_pipeline_value": round(net_deal_value * win_prob, 2),
            "sales_cycle_days":        cycle_days,
            "strategic_score":         round(random.uniform(1, 10), 1),
            "risk_score":              round(random.uniform(1, 10), 1),
            "loss_reason":             random.choice(LOSS_REASONS) if stage == "Closed Lost" else None,
        })

    df_deals = pd.DataFrame(deals)

    scores = []
    for _, row in df_deals.iterrows():
        margin_score     = min(10, round((row["gm_pct"] / 0.45) * 10, 1))
        discount_penalty = round((row["discount_rate"] / 0.30) * 10, 1)
        composite        = round(
            (margin_score * 0.35) +
            ((10 - discount_penalty) * 0.25) +
            (row["strategic_score"] * 0.25) +
            ((10 - row["risk_score"]) * 0.15), 2
        )
        scores.append({
            "deal_id":         row["deal_id"],
            "margin_score":    margin_score,
            "discount_score":  round(10 - discount_penalty, 1),
            "strategic_score": row["strategic_score"],
            "risk_score":      round(10 - row["risk_score"], 1),
            "composite_score": composite,
            "recommendation":  "Approve" if composite >= 6.5 else "Escalate" if composite >= 5.0 else "Reject",
        })
    df_scores = pd.DataFrame(scores)

    APPROVERS = ["Sr. Finance Manager", "VP Sales Finance", "CFO", "Auto-Approved"]
    approvals = []
    for _, row in df_deals[df_deals["deal_stage"].isin(["Negotiation", "Closed Won", "Closed Lost"])].iterrows():
        score    = df_scores[df_scores["deal_id"] == row["deal_id"]]["composite_score"].values[0]
        approved = score >= 5.0
        approvals.append({
            "deal_id":       row["deal_id"],
            "approver":      "Auto-Approved" if score >= 7.5 else random.choice(APPROVERS[:-1]),
            "approval_date": row["created_date"],
            "approved":      approved,
            "notes":         f"Score {score}. {'Within policy.' if approved else 'Below margin threshold.'}",
        })
    df_approvals = pd.DataFrame(approvals)

    conn = sqlite3.connect(f"{DB_DIR}/deal_pipeline.db")
    df_deals.to_sql("deals",        conn, if_exists="replace", index=False)
    df_scores.to_sql("deal_scores", conn, if_exists="replace", index=False)
    df_approvals.to_sql("approvals", conn, if_exists="replace", index=False)
    conn.close()

    df_deals.to_csv(f"{EXPORT_DIR}/deals.csv",        index=False)
    df_scores.to_csv(f"{EXPORT_DIR}/deal_scores.csv", index=False)

    print(f"  → {len(df_deals):,} deals | {len(df_scores):,} scores | {len(df_approvals):,} approvals")


# ─────────────────────────────────────────────
# DATABASE 3: channel_sales.db
# Tables: rep_performance, quota_plan, monthly_actuals
# ─────────────────────────────────────────────

def build_channel_sales_db():
    print("Building channel_sales.db ...")

    rep_rows = []
    for rep in REPS:
        annual_quota   = round(random.uniform(3000000, 12000000), 2)
        attainment_pct = round(random.uniform(0.55, 1.35), 4)
        actual_revenue = round(annual_quota * attainment_pct, 2)
        avg_deal_size  = round(random.uniform(80000, 600000), 2)
        deals_won      = int(actual_revenue / avg_deal_size)
        deals_lost     = random.randint(int(deals_won * 0.3), int(deals_won * 0.9))

        rep_rows.append({
            "rep_name":             rep["name"],
            "region":               rep["region"],
            "segment":              rep["segment"],
            "annual_quota":         annual_quota,
            "actual_revenue":       actual_revenue,
            "quota_attainment_pct": attainment_pct,
            "deals_won":            deals_won,
            "deals_lost":           deals_lost,
            "win_rate":             round(deals_won / (deals_won + deals_lost), 4),
            "avg_deal_size":        avg_deal_size,
            "avg_sales_cycle_days": random.randint(28, 120),
            "avg_discount_rate":    round(random.uniform(0.08, 0.25), 4),
            "avg_gross_margin_pct": round(random.uniform(0.25, 0.45), 4),
            "year":                 2024,
        })
    df_reps = pd.DataFrame(rep_rows)

    quota_rows = []
    q_weights  = [0.22, 0.24, 0.25, 0.29]
    for rep in REPS:
        annual = df_reps[df_reps["rep_name"] == rep["name"]]["annual_quota"].values[0]
        for q_idx, weight in enumerate(q_weights):
            quota_rows.append({
                "rep_name":          rep["name"],
                "region":            rep["region"],
                "quarter":           f"Q{q_idx + 1} 2024",
                "quarterly_quota":   round(annual * weight, 2),
                "plan_discount_rate": round(random.uniform(0.10, 0.20), 4),
                "plan_gm_pct":       round(random.uniform(0.30, 0.42), 4),
            })
    df_quota = pd.DataFrame(quota_rows)

    monthly_rows = []
    months       = pd.date_range("2024-01-01", "2024-12-01", freq="MS")
    for rep in REPS:
        annual_actual = df_reps[df_reps["rep_name"] == rep["name"]]["actual_revenue"].values[0]
        monthly_base  = annual_actual / 12
        for month in months:
            season = 1.0 + (0.3 if month.month >= 10 else 0.1 if month.month >= 7 else 0.0)
            actual = round(monthly_base * season * random.uniform(0.75, 1.25), 2)
            plan   = round(monthly_base * season * random.uniform(0.90, 1.10), 2)
            monthly_rows.append({
                "rep_name":             rep["name"],
                "region":               rep["region"],
                "month":                month.strftime("%Y-%m"),
                "actual_revenue":       actual,
                "plan_revenue":         plan,
                "variance_vs_plan":     round(actual - plan, 2),
                "variance_pct":         round((actual - plan) / plan, 4) if plan > 0 else 0,
                "actual_discount_rate": round(random.uniform(0.08, 0.25), 4),
                "actual_gm_pct":        round(random.uniform(0.25, 0.45), 4),
            })
    df_monthly = pd.DataFrame(monthly_rows)

    conn = sqlite3.connect(f"{DB_DIR}/channel_sales.db")
    df_reps.to_sql("rep_performance",   conn, if_exists="replace", index=False)
    df_quota.to_sql("quota_plan",       conn, if_exists="replace", index=False)
    df_monthly.to_sql("monthly_actuals", conn, if_exists="replace", index=False)
    conn.close()

    df_reps.to_csv(f"{EXPORT_DIR}/rep_performance.csv",   index=False)
    df_quota.to_csv(f"{EXPORT_DIR}/quota_plan.csv",       index=False)
    df_monthly.to_csv(f"{EXPORT_DIR}/monthly_actuals.csv", index=False)

    print(f"  → {len(df_reps)} reps | {len(df_quota)} quota rows | {len(df_monthly):,} monthly actuals")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("Middleton Finance Suite — Data Layer")
    print("=" * 55)

    build_pricing_rebates_db()
    build_deal_pipeline_db()
    build_channel_sales_db()

    print("\n✓ All three databases built successfully.")
    print(f"  pricing_rebates.db → {DB_DIR}/")
    print(f"  deal_pipeline.db   → {DB_DIR}/")
    print(f"  channel_sales.db   → {DB_DIR}/")
    print(f"  CSVs exported      → {EXPORT_DIR}/")
