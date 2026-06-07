# analysis/gap_analyzer.py
# Compares user skills against market-scraped job data.
# target_tier filters the dataset to the matching cluster when cluster
# data exists, so FAANG vs Mid-market analysis produces different results.

import json
import os

PROFILES_FILE = "data/ground_truth_profiles.json"
CLUSTER_REPORT = "data/cluster_report.json"


def load_profiles() -> list[dict]:
    if not os.path.exists(PROFILES_FILE):
        raise FileNotFoundError("Run main4.py first to build profiles.")
    with open(PROFILES_FILE) as f:
        return json.load(f)


def _empty(target_tier: str) -> dict:
    return {
        "target_cluster":      target_tier,
        "total_jobs_analyzed": 0,
        "readiness_score":     0.0,
        "have_required":       [],
        "missing_required":    [],
        "have_useful":         [],
        "missing_useful":      [],
        "priority_list":       [],
        "profile_required":    [],
        "profile_useful":      [],
        "all_ranked":          [],
    }


def analyze_gap(user_skills: list[str], target_tier: str) -> dict:
    """
    Reads from raw_jobs.csv every time (always fresh).
    When target_tier is set and cluster data exists, filters the DataFrame
    to only jobs belonging to clusters matching that tier label.
    """
    import pandas as pd
    from collections import Counter
    from config import CSV_OUTPUT

    try:
        df = pd.read_csv(CSV_OUTPUT)
    except Exception:
        return _empty(target_tier)

    if df.empty:
        return _empty(target_tier)

    # ── Tier filtering via cluster data ───────────────────────────────────────
    if (
        target_tier.lower() not in ["all", ""]
        and "Cluster" in df.columns
        and os.path.exists(CLUSTER_REPORT)
    ):
        try:
            with open(CLUSTER_REPORT) as f:
                cluster_report = json.load(f)

            # Find cluster IDs whose label contains the requested tier
            matching_ids = [
                c["cluster_id"]
                for c in cluster_report
                if target_tier.lower() in c["label"].lower()
            ]

            if matching_ids:
                df_filtered = df[df["Cluster"].isin(matching_ids)]
                # Only use filtered set if it has meaningful data
                if len(df_filtered) >= 5:
                    df = df_filtered
        except Exception:
            pass  # graceful fall-through to full dataset

    # ── Skill frequency analysis ──────────────────────────────────────────────
    all_skills = []
    for s in df["Skills Required"].dropna():
        if str(s) not in ["N/A", "nan", ""]:
            all_skills.extend([x.strip().lower() for x in str(s).split(",") if x.strip()])

    total = len(df)
    if total == 0 or not all_skills:
        return _empty(target_tier)

    skill_counts = Counter(all_skills)
    all_ranked = [
        (s, round(c / total * 100, 1))
        for s, c in skill_counts.most_common(50)
    ]
    skill_pct = dict(all_ranked)

    required = [s for s, pct in all_ranked if pct >= 30]
    useful    = [s for s, pct in all_ranked if 15 <= pct < 30]

    user_set     = {s.lower().strip() for s in user_skills if s.strip()}
    required_set = set(required)
    useful_set   = set(useful)

    have_required    = sorted(required_set & user_set)
    missing_required = sorted(required_set - user_set)
    have_useful      = sorted(useful_set & user_set)
    missing_useful   = sorted(useful_set - user_set)

    score = (
        round(len(have_required) / len(required_set) * 100, 1)
        if required_set else 0.0
    )

    priority = sorted(
        missing_required + missing_useful,
        key=lambda s: skill_pct.get(s, 0),
        reverse=True,
    )

    return {
        "target_cluster":      target_tier,
        "total_jobs_analyzed": total,
        "readiness_score":     score,
        "have_required":       have_required,
        "missing_required":    missing_required,
        "have_useful":         have_useful,
        "missing_useful":      missing_useful,
        "priority_list":       priority[:15],
        "profile_required":    required,
        "profile_useful":      useful,
        "all_ranked":          all_ranked[:20],
    }


def print_report(result: dict):
    print(f"\n{'='*55}")
    print(f"  Gap Analysis — {result['target_cluster']}")
    print(f"  Jobs analyzed: {result['total_jobs_analyzed']}")
    print(f"  Readiness score: {result['readiness_score']}%")
    print(f"{'='*55}")

    print(f"\n  ✓ Required skills you HAVE ({len(result['have_required'])}):")
    for s in result["have_required"]:
        print(f"    + {s}")

    print(f"\n  ✗ Required skills you LACK ({len(result['missing_required'])}):")
    ranked_d = dict(result["all_ranked"])
    for s in result["missing_required"]:
        print(f"    - {s:<30} ({ranked_d.get(s, 0)}% of JDs)")

    print(f"\n  📋 Priority Learning List (top 15):")
    for i, s in enumerate(result["priority_list"], 1):
        print(f"    {i:>2}. {s:<30} {ranked_d.get(s, 0)}%")
    print(f"{'='*55}")