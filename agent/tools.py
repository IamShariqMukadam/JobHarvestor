# agent/tools.py
# 4 LangChain tools the agent can call
# Each tool wraps existing project logic — no duplication

import json
import pandas as pd
from langchain.tools import tool
from config import CSV_OUTPUT


@tool
def search_jobs_tool(role: str, tier: str = "all") -> str:
    """
    Searches raw_jobs.csv for jobs matching the given role and tier.
    Returns JSON string of matching jobs with their JD URLs.
    Use this first to find relevant jobs before extracting skills.
    """
    try:
        df = pd.read_csv(CSV_OUTPUT)

        # Filter by role
        mask = df["Role Searched"].str.lower().str.contains(
            role.lower(), na=False
        )
        df_filtered = df[mask]

        # Filter by tier if specified
        if tier.lower() not in ["all", ""]:
            tier_map = {
                "faang": ["google", "amazon", "meta", "microsoft", "apple",
                          "goldman", "jpmorgan", "mckinsey", "netflix"],
                "series a": ["zepto", "razorpay", "cred", "groww", "meesho",
                             "slice", "browserstack"],
            }
            tier_companies = tier_map.get(tier.lower(), [])
            if tier_companies:
                pattern = "|".join(tier_companies)
                mask2 = df_filtered["Company"].str.lower().str.contains(
                    pattern, na=False
                )
                # If tier filter gives results use it, else return all
                if mask2.sum() > 0:
                    df_filtered = df_filtered[mask2]

        result = df_filtered[["Title","Company","Platform",
                               "Location","URL","Skills Required"]
                             ].head(50).to_dict("records")
        return json.dumps({
            "found": len(result),
            "jobs": result
        })
    except Exception as e:
        return json.dumps({"error": str(e), "found": 0, "jobs": []})


@tool
def extract_skills_tool(role: str) -> str:
    """
    Reads already-extracted skills from raw_jobs.csv for a given role.
    Returns aggregated skill frequency across all JDs for that role.
    Use this after search_jobs_tool to understand what skills appear most.
    """
    try:
        from collections import Counter
        df = pd.read_csv(CSV_OUTPUT)
        mask = df["Role Searched"].str.lower().str.contains(role.lower(), na=False)
        df_role = df[mask]

        all_skills = []
        for s in df_role["Skills Required"].dropna():
            if s not in ["N/A", ""]:
                all_skills.extend([x.strip().lower() for x in s.split(",")])

        counts = Counter(all_skills)
        top_skills = [
            {"skill": skill, "count": count,
             "percentage": round(count / len(df_role) * 100, 1)}
            for skill, count in counts.most_common(25)
        ]
        return json.dumps({
            "role": role,
            "total_jds": len(df_role),
            "top_skills": top_skills
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def cluster_analysis_tool(tier: str) -> str:
    """
    Returns ground truth skill profile for the specified company tier.
    tier options: 'FAANG', 'Series A', 'Mid-market'
    Use this to understand what a specific tier actually requires.
    """
    try:
        from analysis.gap_analyzer import load_profiles
        profiles = load_profiles()
        for p in profiles:
            if tier.lower() in p["label"].lower():
                return json.dumps({
                    "tier": p["label"],
                    "total_jobs": p["total_jobs"],
                    "required_skills": p["required_skills"],
                    "useful_skills": p["useful_skills"],
                    "top_10": p["all_ranked"][:10]
                })
        # Return all profiles if tier not found
        return json.dumps([{
            "tier": p["label"],
            "required": p["required_skills"][:5]
        } for p in profiles])
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def gap_analysis_tool(user_skills_csv: str, target_tier: str) -> str:
    """
    Performs personalized gap analysis.
    user_skills_csv: comma-separated string of user's skills e.g. "Python,SQL,Pandas"
    target_tier: 'FAANG', 'Series A', or 'Mid-market'
    Returns readiness score, missing skills, and priority learning list.
    Use this LAST after you understand the role requirements.
    """
    try:
        from analysis.gap_analyzer import analyze_gap
        import importlib
        import analysis.gap_analyzer as _ga
        importlib.reload(_ga)
        user_skills = [s.strip() for s in user_skills_csv.split(",") if s.strip()]
        result = analyze_gap(user_skills, target_tier)
        return json.dumps({
            "readiness_score": result["readiness_score"],
            "target": result["target_cluster"],
            "have_required": result["have_required"],
            "missing_required": result["missing_required"],
            "priority_list": result["priority_list"][:10],
            "total_jobs_analyzed": result["total_jobs_analyzed"]
        })
    except Exception as e:
        return json.dumps({"error": str(e)})