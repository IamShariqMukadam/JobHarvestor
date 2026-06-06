# api/main.py — FastAPI app
# Endpoints:
#   GET  /health          → health check
#   GET  /profiles        → all cluster profiles
#   POST /analyze         → gap analysis for user
#   GET  /skills/{tier}   → top skills for a tier

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.models import (
    AnalyzeRequest, AnalyzeResponse,
    ProfilesResponse, HealthResponse
)
from analysis.gap_analyzer import analyze_gap, load_profiles

app = FastAPI(
    title="JobHarvestor API",
    description="Job market intelligence + skill gap analysis",
    version="1.0.0"
)

# Allow Streamlit to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health():
    try:
        profiles = load_profiles()
        return {"status": "ok", "clusters_loaded": len(profiles)}
    except Exception:
        return {"status": "profiles_not_found", "clusters_loaded": 0}


@app.get("/profiles")
def get_profiles():
    """Returns all cluster ground truth profiles."""
    try:
        profiles = load_profiles()
        return {"profiles": profiles}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/skills/{tier}")
def get_skills(tier: str):
    """Returns top skills for a given tier label."""
    try:
        profiles = load_profiles()
        for p in profiles:
            if tier.lower() in p["label"].lower():
                return {
                    "tier": p["label"],
                    "required": p["required_skills"],
                    "useful": p["useful_skills"],
                    "all_ranked": p["all_ranked"]
                }
        raise HTTPException(status_code=404, detail=f"Tier '{tier}' not found")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    """
    Main endpoint — takes user skills + target tier,
    returns full gap analysis.
    """
    if not request.user_skills:
        raise HTTPException(status_code=400, detail="user_skills cannot be empty")

    try:
        result = analyze_gap(request.user_skills, request.target_tier)
        return AnalyzeResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))