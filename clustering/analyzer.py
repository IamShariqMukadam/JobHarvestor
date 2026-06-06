# clustering/analyzer.py
# Analyzes each cluster — what skills dominate, what experience level
# Builds "ground truth role profile" per cluster
# Labels clusters as FAANG/Series A/Mid-market based on companies found

import pandas as pd
from collections import Counter


# BEFORE — too narrow, misses Indian companies
FAANG = ["google", "amazon", "meta", "microsoft", "apple", "netflix", ...]
SERIES_A = ["zepto", "razorpay", ...]

# AFTER — tier detection based on company size signals in data
def label_cluster(df_cluster: pd.DataFrame) -> str:
    companies = df_cluster["Company"].str.lower().tolist()
    
    tier1 = ["google", "amazon", "meta", "microsoft", "apple", "netflix",
             "goldman", "jpmorgan", "mckinsey", "accenture", "ibm",
             "infosys", "tcs", "tata consultancy", "wipro", "cognizant",
             "capgemini", "deloitte", "pwc", "ey", "kpmg", "mastercard",
             "jpmorgan", "wells fargo", "hsbc", "barclays", "unilever",
             "amazon", "flipkart", "walmart", "samsung", "intel"]
    
    startup = ["zepto", "razorpay", "cred", "groww", "meesho", "slice",
               "browserstack", "postman", "chargebee", "unacademy",
               "persistent", "tavant", "altimetrik", "ecolab"]
    
    total = len(companies)
    tier1_count   = sum(1 for c in companies if any(t in c for t in tier1))
    startup_count = sum(1 for c in companies if any(s in c for s in startup))
    
    if tier1_count / total > 0.20:
        return "Tier-1"
    elif startup_count / total > 0.10:
        return "Series A / Startup"
    else:
        return "Mid-market"


def analyze_cluster(df_cluster: pd.DataFrame, cluster_id: int) -> dict:
    """
    For one cluster: top skills, experience distribution, salary range.
    Returns dict with all analysis.
    """
    # Skill frequency
    all_skills = []
    for s in df_cluster["Skills Required"].dropna():
        if s not in ["N/A", ""]:
            all_skills.extend([x.strip().lower() for x in s.split(",")])
    
    skill_counts = Counter(all_skills)
    top_skills = skill_counts.most_common(20)
    total_jobs = len(df_cluster)
    
    skill_freq = [
    {
        "skill": skill,
        "count": int(count),
        "percentage": round(count / total_jobs * 100, 1)
    }
    for skill, count in top_skills
]
    
    # Experience distribution
    exp_values = df_cluster["Experience Required"].dropna()
    exp_values = exp_values[~exp_values.isin(["N/A", "nan", ""])]
    
    # Platform breakdown
    platform_dist = df_cluster["Platform"].value_counts().to_dict()
    
    # Role breakdown
    role_dist = df_cluster["Role Searched"].value_counts().to_dict()

    return {
        "cluster_id": int(cluster_id),
        "label": label_cluster(df_cluster),
        "total_jobs": total_jobs,
        "top_skills": skill_freq,
        "platform_distribution": platform_dist,
        "role_distribution": role_dist,
        "sample_companies": df_cluster["Company"].value_counts().head(10).to_dict()
    }


def analyze_all(df: pd.DataFrame) -> list[dict]:
    """Analyzes all clusters, returns list of cluster profiles."""
    profiles = []
    cluster_ids = [int(x) for x in sorted(df["Cluster"].unique())]
    
    for cid in cluster_ids:
        df_cluster = df[df["Cluster"] == cid]
        profile = analyze_cluster(df_cluster, cid)
        profiles.append(profile)
        print(f"  [Analyzer] Cluster {cid} ({profile['label']}): "
              f"{profile['total_jobs']} jobs | "
              f"Top skill: {profile['top_skills'][0]['skill'] if profile['top_skills'] else 'N/A'}")
    
    return profiles