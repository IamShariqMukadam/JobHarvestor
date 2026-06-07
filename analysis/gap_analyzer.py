# analysis/gap_analyzer.py
# Compares user's skills against ground truth profile
# Returns: skills you have, skills you're missing, priority learning list

import json
import os

PROFILES_FILE = os.path.join(os.getenv("JH_SESSION_DIR","data"), "ground_truth_profiles.json")


def load_profiles() -> list[dict]:
    if not os.path.exists(PROFILES_FILE):
        raise FileNotFoundError("Run main4.py first to build profiles.")
    with open(PROFILES_FILE) as f:
        data = json.load(f)
    return data  # always reads fresh from disk


def normalize_skills(skills: list[str]) -> set[str]:
    """Lowercase + strip for comparison."""
    return {s.lower().strip() for s in skills if s.strip()}


def analyze_gap(user_skills: list[str], target_tier: str) -> dict:
    """
    Reads DIRECTLY from raw_jobs.csv every time.
    No stale cluster profiles — always fresh data.
    """
    import pandas as pd
    from collections import Counter
    from config import CSV_OUTPUT

    try:
        df = pd.read_csv(CSV_OUTPUT)
    except Exception:
        return {
            "target_cluster": target_tier,
            "total_jobs_analyzed": 0,
            "readiness_score": 0.0,
            "have_required": [],
            "missing_required": [],
            "have_useful": [],
            "missing_useful": [],
            "priority_list": [],
            "profile_required": [],
            "profile_useful": [],
            "all_ranked": []
        }

    # Collect all skills from CSV
    all_skills = []
    for s in df["Skills Required"].dropna():
        if str(s) not in ["N/A", "nan", ""]:
            all_skills.extend([x.strip().lower() for x in str(s).split(",")])

    total = len(df)
    skill_counts = Counter(all_skills)
    all_ranked = [(s, round(c / total * 100, 1))
                  for s, c in skill_counts.most_common(50)]
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

    score = round(len(have_required) / len(required_set) * 100, 1) \
            if required_set else 0.0

    priority = sorted(
        missing_required + missing_useful,
        key=lambda s: skill_pct.get(s, 0),
        reverse=True
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
        "all_ranked":          all_ranked[:20]
    }


def print_report(result: dict):
    """Pretty-print gap analysis to terminal."""
    print(f"\n{'='*55}")
    print(f"  Gap Analysis — {result['target_cluster']}")
    print(f"  Jobs analyzed: {result['total_jobs_analyzed']}")
    print(f"  Readiness score: {result['readiness_score']}%")
    print(f"{'='*55}")

    print(f"\n  ✓ Required skills you HAVE ({len(result['have_required'])}):")
    for s in result["have_required"]:
        print(f"    + {s}")

    print(f"\n  ✗ Required skills you LACK ({len(result['missing_required'])}):")
    for s in result["missing_required"]:
        pct = dict(result["all_ranked"]).get(s, 0)
        print(f"    - {s:<30} ({pct}% of JDs)")

    print(f"\n  📋 Priority Learning List (top 15):")
    for i, s in enumerate(result["priority_list"], 1):
        pct = dict(result["all_ranked"]).get(s, 0)
        print(f"    {i:>2}. {s:<30} {pct}%")
    print(f"{'='*55}")