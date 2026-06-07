# clustering/analyzer.py
# Analyzes each cluster — skill frequency, experience, platform breakdown.
# label_cluster: primary = company name matching (expanded Indian list)
#                secondary = platform distribution (LinkedIn = corporate)
# analyze_all: if all 3 clusters get same label, applies relative
#              differentiation so the UI always shows distinct tiers.

import pandas as pd
from collections import Counter

# ── Tier company lists ────────────────────────────────────────────────────────
_TIER1 = [
    # Global big-tech
    "google", "amazon", "meta", "microsoft", "apple", "netflix",
    "intel", "cisco", "oracle", "salesforce", "adobe", "sap",
    "qualcomm", "samsung", "ibm", "accenture",
    # Indian IT majors
    "infosys", "tcs", "tata consultancy", "wipro", "cognizant",
    "capgemini", "hcl", "tech mahindra", "mphasis", "ltimindtree",
    "l&t infotech", "hexaware", "zensar", "niit",
    # Finance / consulting
    "goldman", "jpmorgan", "mckinsey", "deloitte", "pwc", "ey", "kpmg",
    "mastercard", "hsbc", "barclays", "wells fargo", "unilever",
    # E-commerce majors
    "flipkart", "walmart", "swiggy", "zomato",
]

_STARTUP = [
    "zepto", "razorpay", "cred", "groww", "meesho", "slice",
    "browserstack", "postman", "chargebee", "unacademy",
    "persistent", "tavant", "altimetrik", "freshworks", "zoho",
    "cleartax", "lenskart", "nykaa", "ola", "paytm", "phonepe",
    "spinny", "cars24", "curefit", "darwinbox", "leadsquared",
    "moengage", "sprinklr", "hasura", "setu", "sarvam",
]


def label_cluster(df_cluster: pd.DataFrame) -> str:
    """
    Primary: company-name substring matching.
    Secondary (fallback): platform distribution as tier signal.
    """
    companies = df_cluster["Company"].str.lower().fillna("").tolist()
    total = len(companies)
    if total == 0:
        return "Mid-market"

    t1_count = sum(1 for c in companies if any(t in c for t in _TIER1))
    st_count = sum(1 for c in companies if any(s in c for s in _STARTUP))

    t1_pct = t1_count / total
    st_pct = st_count / total

    # Primary: company name
    if t1_pct >= 0.12:
        return "Tier-1"
    if st_pct >= 0.08:
        return "Series A / Startup"

    # Secondary: platform distribution
    platform_counts = df_cluster["Platform"].value_counts()
    linkedin_pct = platform_counts.get("LinkedIn", 0) / total
    internshala_pct = platform_counts.get("Internshala", 0) / total

    if linkedin_pct >= 0.55:
        return "Tier-1"
    if internshala_pct >= 0.55:
        return "Series A / Startup"

    return "Mid-market"


def analyze_cluster(df_cluster: pd.DataFrame, cluster_id: int) -> dict:
    all_skills = []
    for s in df_cluster["Skills Required"].dropna():
        if str(s) not in ["N/A", ""]:
            all_skills.extend([x.strip().lower() for x in str(s).split(",") if x.strip()])

    skill_counts = Counter(all_skills)
    top_skills_raw = skill_counts.most_common(20)
    total_jobs = len(df_cluster)

    skill_freq = [
        {
            "skill": skill,
            "count": int(count),
            "percentage": round(count / total_jobs * 100, 1),
        }
        for skill, count in top_skills_raw
    ]

    return {
        "cluster_id":           int(cluster_id),
        "label":                label_cluster(df_cluster),
        "total_jobs":           total_jobs,
        "top_skills":           skill_freq,
        "platform_distribution": df_cluster["Platform"].value_counts().to_dict(),
        "role_distribution":    df_cluster["Role Searched"].value_counts().to_dict(),
        "sample_companies":     df_cluster["Company"].value_counts().head(10).to_dict(),
    }


def analyze_all(df: pd.DataFrame) -> list[dict]:
    """
    Analyzes all clusters.
    If primary labeling returns the same label for every cluster
    (common when data is all mid-market Indian companies), applies
    relative differentiation using platform distribution + skill density.
    """
    profiles = []
    cluster_ids = [int(x) for x in sorted(df["Cluster"].unique())]

    for cid in cluster_ids:
        df_cluster = df[df["Cluster"] == cid]
        profile = analyze_cluster(df_cluster, cid)
        profiles.append(profile)

    # ── Relative differentiation when all labels are identical ────────────────
    labels = [p["label"] for p in profiles]
    if len(profiles) >= 2 and len(set(labels)) == 1:
        def _tier_score(profile):
            """
            Higher score → more corporate/senior cluster.
            Primary signal: LinkedIn proportion (corporate = LinkedIn-heavy).
            Secondary signal: skill count density (more skills = more senior).
            """
            cid = profile["cluster_id"]
            df_c = df[df["Cluster"] == cid]
            n = max(len(df_c), 1)
            linkedin_ratio    = len(df_c[df_c["Platform"] == "LinkedIn"]) / n
            internshala_ratio = len(df_c[df_c["Platform"] == "Internshala"]) / n
            skill_density = sum(s["count"] for s in profile["top_skills"]) / n
            return linkedin_ratio * 3 - internshala_ratio * 2 + skill_density * 0.05

        sorted_profiles = sorted(profiles, key=_tier_score, reverse=True)
        tier_labels = ["Tier-1", "Mid-market", "Series A / Startup"]

        for rank, profile in enumerate(sorted_profiles):
            profile["label"] = tier_labels[min(rank, len(tier_labels) - 1)]

    for p in profiles:
        top = p["top_skills"][0]["skill"] if p["top_skills"] else "N/A"
        print(
            f"  [Analyzer] Cluster {p['cluster_id']} ({p['label']}): "
            f"{p['total_jobs']} jobs | Top skill: {top}"
        )

    return profiles