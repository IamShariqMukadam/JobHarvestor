# api/models.py — Pydantic models for FastAPI request/response

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    user_skills: list[str]
    target_tier: str = "mid-market"   # "FAANG", "Series A", "Mid-market"


class SkillGap(BaseModel):
    skill: str
    percentage_in_jds: float


class AnalyzeResponse(BaseModel):
    target_cluster:      str
    readiness_score:     float
    have_required:       list[str]
    missing_required:    list[str]
    have_useful:         list[str]
    missing_useful:      list[str]
    priority_list:       list[str]
    all_ranked:          list[tuple]
    total_jobs_analyzed: int


class ProfilesResponse(BaseModel):
    profiles: list[dict]


class HealthResponse(BaseModel):
    status: str
    clusters_loaded: int