# main4.py — Day 4 runner
# 1. Builds ground truth profiles from cluster data
# 2. Tests gap analysis with YOUR skills
# 3. Starts FastAPI server

import json
from analysis.profile_builder import build_profiles
from analysis.gap_analyzer import analyze_gap, print_report

# ── YOUR SKILLS — update this list ────────────────────────────────────────
MY_SKILLS = [
    "Python", "SQL", "Pandas", "NumPy",
    "Machine Learning", "Scikit-learn",
    "Matplotlib", "Power BI", "Excel",
    "Data Analysis", "Data Visualization"
]
TARGET_TIER = "mid-market"   # "FAANG", "Series A", "mid-market"
# ──────────────────────────────────────────────────────────────────────────


def run():
    print("=" * 55)
    print("  JobHarvestor — Day 4: Profiles + Gap Analysis")
    print("=" * 55)

    # Step 1 — Build profiles
    print("\n[1/3] Building ground truth profiles...")
    profiles = build_profiles()
    print(f"  ✓ {len(profiles)} profiles built")

    # Step 2 — Run gap analysis with your skills
    print("\n[2/3] Running gap analysis for your skills...")
    print(f"  Your skills: {MY_SKILLS}")
    print(f"  Target tier: {TARGET_TIER}")
    result = analyze_gap(MY_SKILLS, TARGET_TIER)
    print_report(result)

    # Step 3 — Save your personal report
    with open("data/my_gap_report.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n  [Report] Saved → data/my_gap_report.json")

    print("\n[3/3] To start FastAPI server run:")
    print("  uvicorn api.main:app --reload --port 8000")
    print("\n  Then test at: http://localhost:8000/docs")
    print("=" * 55)


if __name__ == "__main__":
    run()