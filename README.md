# JobHarvestor — Niche Job Market Intelligence Agent

> Built an AI agent that crawls 200+ live job postings across LinkedIn, Naukri, 
> and Internshala via Selenium and BeautifulSoup, passing each through an LLM 
> extraction layer to output structured skill frequency data in a multi-sheet Excel report.

## Problem
AI role JDs show 70%+ inconsistency across companies causing candidates to waste 
6-12 months on wrong skills. JobHarvestor clusters postings by company stage 
(FAANG/Series-A/Mid-market) producing a heatmap of what actually matters vs JD filler.

## Solution
A LangGraph agent that:
1. Crawls 200+ JDs from LinkedIn, Naukri, Internshala
2. Extracts structured skills via Groq LLM
3. Clusters JDs by company tier using sentence-transformers + k-means
4. Builds ground truth role profiles per tier
5. Generates personalized skill gap analysis + priority learning list

## Tech Stack
`Selenium` `BeautifulSoup4` `Groq LLM` `LangGraph` `sentence-transformers` 
`scikit-learn` `FastAPI` `Streamlit` `Plotly` `pandas` `openpyxl`

## Architecture
main.py   → scrape jobs (LinkedIn, Naukri, Internshala)
main2.py  → LLM extract skills from JDs (Groq)
main3.py  → embeddings + k-means clustering
main4.py  → ground truth profiles + gap analysis + FastAPI
streamlit_app.py → LangGraph agent + UI

## Quick Start
```bash
# 1. Install
pip install -r requirements.txt

# 2. Set env vars
cp .env.example .env  # fill in GROQ_API_KEY, credentials

# 3. Run pipeline
python3 main.py       # scrape
python3 main2.py      # extract skills
python3 main3.py      # cluster
python3 main4.py      # build profiles

# 4. Launch UI
streamlit run streamlit_app.py
```

## Output
- `data/raw_jobs.csv` — 600+ scraped jobs
- `data/JobHarvestor.xlsx` — 4-sheet Excel tracker
- `data/cluster_report.json` — per-tier skill profiles
- Streamlit dashboard at localhost:8501