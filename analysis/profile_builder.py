# analysis/profile_builder.py
# Builds "ground truth role profile" per cluster from cluster_report.json
# Profile = what skills actually matter at what % threshold

import json
import os

CLUSTER_REPORT = "data/cluster_report.json"
PROFILES_FILE  = "data/ground_truth_profiles.json"

# Skills appearing in X% of JDs in a cluster = "required" for that tier
REQUIRED_THRESHOLD  = 40   # 40%+ = must have
USEFUL_THRESHOLD    = 20   # 20-40% = good to have


def build_profiles() -> list[dict]:
    """
    Reads cluster_report.json → builds structured ground truth profile per cluster.
    """
    if not os.path.exists(CLUSTER_REPORT):
        raise FileNotFoundError(f"Run main3.py first — {CLUSTER_REPORT} missing.")

    with open(CLUSTER_REPORT) as f:
        clusters = json.load(f)

    profiles = []
    for cluster in clusters:
        label     = cluster["label"]
        total     = cluster["total_jobs"]
        skills    = cluster["top_skills"]

        required   = [s["skill"] for s in skills if s["percentage"] >= REQUIRED_THRESHOLD]
        useful     = [s["skill"] for s in skills
                      if USEFUL_THRESHOLD <= s["percentage"] < REQUIRED_THRESHOLD]
        all_ranked = [(s["skill"], s["percentage"]) for s in skills]

        profile = {
            "cluster_id":      cluster["cluster_id"],
            "label":           label,
            "total_jobs":      total,
            "required_skills": required,
            "useful_skills":   useful,
            "all_ranked":      all_ranked,
            "platform_dist":   cluster["platform_distribution"],
            "role_dist":       cluster["role_distribution"],
            "top_companies":   cluster["sample_companies"]
        }
        profiles.append(profile)

        print(f"  Cluster {cluster['cluster_id']} — {label}")
        print(f"    Required ({REQUIRED_THRESHOLD}%+): {required[:5]}")
        print(f"    Useful   ({USEFUL_THRESHOLD}%+): {useful[:5]}")

    os.makedirs("data", exist_ok=True)
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)
    print(f"\n  [Profiles] Saved → {PROFILES_FILE}")

    return profiles