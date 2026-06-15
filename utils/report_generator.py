# utils/report_generator.py
# Generates a formatted multi-sheet XLSX gap analysis report.
# This is the "research report" mentioned in the resume:
# "outputs a prioritized gap analysis — a research report that would
#  otherwise take weeks to compile manually."

import datetime
from io import BytesIO
from collections import Counter

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import (Font, PatternFill, Alignment,
                               Border, Side, GradientFill)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference


# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "navy":      "1F4E79",
    "teal":      "2E86AB",
    "teal_light":"D6EAF8",
    "green":     "1E8449",
    "green_light":"D5F5E3",
    "red":       "C0392B",
    "red_light": "FADBD8",
    "amber":     "D4AC0D",
    "amber_light":"FEF9E7",
    "gray_hdr":  "2C3E50",
    "gray_light":"F2F3F4",
    "white":     "FFFFFF",
    "black":     "000000",
}

thin  = Side(style="thin",  color="CCCCCC")
thick = Side(style="medium", color="AAAAAA")
THIN_BORDER  = Border(left=thin,  right=thin,  top=thin,  bottom=thin)
THICK_BORDER = Border(left=thick, right=thick, top=thick, bottom=thick)


def _hdr(ws, row, col, value, bg=C["navy"], fg=C["white"],
          bold=True, size=11, align="center", colspan=1):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font      = Font(bold=bold, color=fg, size=size)
    cell.fill      = PatternFill("solid", fgColor=bg)
    cell.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=True)
    cell.border    = THICK_BORDER
    if colspan > 1:
        ws.merge_cells(start_row=row, start_column=col,
                       end_row=row, end_column=col + colspan - 1)
    return cell


def _cell(ws, row, col, value, bg=None, fg=C["black"],
           bold=False, size=10, align="left", number_format=None):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font      = Font(bold=bold, color=fg, size=size)
    cell.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=True)
    cell.border    = THIN_BORDER
    if bg:
        cell.fill = PatternFill("solid", fgColor=bg)
    if number_format:
        cell.number_format = number_format
    return cell


def _set_col_widths(ws, widths: dict):
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w


# ── Sheet 1: Executive Summary ────────────────────────────────────────────────
def _sheet_summary(wb, gap, role, target_tier, user_skills):
    ws = wb.active
    ws.title = "📋 Summary"
    ws.sheet_view.showGridLines = False

    # Title block
    ws.row_dimensions[1].height = 40
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 18
    _hdr(ws, 1, 1, "JobHarvestor — Personalized Gap Analysis Report",
         bg=C["navy"], size=16, colspan=6)
    _hdr(ws, 2, 1, f"Role: {role or 'All roles'}  |  Target Tier: {target_tier}  "
         f"|  Generated: {datetime.date.today().strftime('%d %b %Y')}",
         bg=C["teal"], fg=C["white"], size=10, bold=False, colspan=6)

    ws.append([])  # row 3 spacer

    # Readiness Score
    score = gap["readiness_score"]
    score_color = (C["green"]  if score >= 70
                   else C["amber"] if score >= 40
                   else C["red"])
    score_label = ("Strong Match" if score >= 70
                   else "Developing" if score >= 40
                   else "Significant Gaps")

    _hdr(ws, 4, 1, "Readiness Score", bg=C["gray_hdr"], align="left", size=11, colspan=2)
    _hdr(ws, 4, 3, "Status",          bg=C["gray_hdr"], align="left", size=11, colspan=2)
    _hdr(ws, 4, 5, "Jobs Analysed",   bg=C["gray_hdr"], align="left", size=11, colspan=2)

    ws.row_dimensions[5].height = 36
    _cell(ws, 5, 1, f"{score}%", bold=True, size=20,
          bg=score_color, fg=C["white"], align="center", colspan=2)
    ws.merge_cells("A5:B5")
    _cell(ws, 5, 3, score_label, bold=True, size=13,
          bg=score_color, fg=C["white"], align="center")
    ws.merge_cells("C5:D5")
    _cell(ws, 5, 5, str(gap["total_jobs_analyzed"]), bold=True, size=13,
          bg=C["teal_light"], align="center")
    ws.merge_cells("E5:F5")

    ws.append([])  # spacer

    # Skills overview
    _hdr(ws, 7, 1, "Your Skills Submitted", bg=C["gray_hdr"], colspan=6, align="left")
    skills_str = ", ".join(user_skills) if user_skills else "None provided"
    _cell(ws, 8, 1, skills_str, bg=C["gray_light"], colspan=6)
    ws.merge_cells("A8:F8")

    ws.append([])

    # Have vs Missing
    _hdr(ws, 10, 1, "✓  Required Skills You HAVE",  bg=C["green"])
    _hdr(ws, 10, 2, "✗  Required Skills You LACK",  bg=C["red"])
    _hdr(ws, 10, 3, "◐  Useful Skills You HAVE",    bg=C["teal"])
    _hdr(ws, 10, 4, "○  Useful Skills You LACK",    bg=C["gray_hdr"])
    _hdr(ws, 10, 5, "Top Priority to Learn",        bg=C["amber"])
    _hdr(ws, 10, 6, "Demand (%)",                   bg=C["amber"])

    have_req  = gap["have_required"]
    miss_req  = gap["missing_required"]
    have_use  = gap["have_useful"]
    miss_use  = gap["missing_useful"]
    priority  = gap["priority_list"]
    all_pct   = dict(gap["all_ranked"])

    max_rows = max(len(have_req), len(miss_req), len(have_use),
                   len(miss_use), len(priority), 1)

    for i in range(max_rows):
        r = 11 + i
        _cell(ws, r, 1,
              have_req[i] if i < len(have_req) else "",
              bg=C["green_light"])
        _cell(ws, r, 2,
              miss_req[i] if i < len(miss_req) else "",
              bg=C["red_light"])
        _cell(ws, r, 3,
              have_use[i] if i < len(have_use) else "",
              bg=C["teal_light"])
        _cell(ws, r, 4,
              miss_use[i] if i < len(miss_use) else "",
              bg=C["gray_light"])
        sk = priority[i] if i < len(priority) else ""
        _cell(ws, r, 5, sk,
              bg=C["amber_light"], bold=(i < 3))
        _cell(ws, r, 6,
              f"{all_pct.get(sk, 0)}%" if sk else "",
              bg=C["amber_light"], align="center", bold=(i < 3))

    _set_col_widths(ws, {"A":22,"B":22,"C":22,"D":22,"E":24,"F":12})


# ── Sheet 2: Market Intelligence ──────────────────────────────────────────────
def _sheet_market(wb, gap, role):
    ws = wb.create_sheet("📊 Market Intelligence")
    ws.sheet_view.showGridLines = False

    _hdr(ws, 1, 1, f"Top Skill Signals — {role or 'All Roles'} Market",
         bg=C["navy"], size=13, colspan=4)
    _hdr(ws, 2, 1, "Rank", bg=C["gray_hdr"], size=10)
    _hdr(ws, 2, 2, "Skill",       bg=C["gray_hdr"], size=10)
    _hdr(ws, 2, 3, "% of JDs",    bg=C["gray_hdr"], size=10)
    _hdr(ws, 2, 4, "Tier",        bg=C["gray_hdr"], size=10)

    all_ranked = gap["all_ranked"]
    req_set    = set(gap["profile_required"])
    use_set    = set(gap["profile_useful"])

    for i, (skill, pct) in enumerate(all_ranked, 1):
        r = 2 + i
        if skill in req_set:
            tier_label = "Required (≥30%)"
            bg = C["red_light"]
        elif skill in use_set:
            tier_label = "Useful (15–30%)"
            bg = C["amber_light"]
        else:
            tier_label = "Supplementary"
            bg = C["gray_light"]
        _cell(ws, r, 1, i,          bg=bg, align="center", bold=(i <= 5))
        _cell(ws, r, 2, skill,      bg=bg, bold=(i <= 5))
        _cell(ws, r, 3, f"{pct}%",  bg=bg, align="center", bold=(i <= 5))
        _cell(ws, r, 4, tier_label, bg=bg)

    # Bar chart
    chart = BarChart()
    chart.type        = "bar"
    chart.grouping    = "clustered"
    chart.title       = "Skill Demand (% of JDs)"
    chart.y_axis.title = "Skill"
    chart.x_axis.title = "% of Job Descriptions"
    chart.width  = 20
    chart.height = 14
    n = min(len(all_ranked), 15)
    data_ref   = Reference(ws, min_col=3, min_row=2, max_row=2 + n)
    cat_ref    = Reference(ws, min_col=2, min_row=3, max_row=2 + n)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cat_ref)
    ws.add_chart(chart, "F2")

    _set_col_widths(ws, {"A":8,"B":26,"C":14,"D":20})


# ── Sheet 3: Learning Roadmap ─────────────────────────────────────────────────
def _sheet_roadmap(wb, gap):
    ws = wb.create_sheet("🗺️ Learning Roadmap")
    ws.sheet_view.showGridLines = False

    _hdr(ws, 1, 1, "Personalised Learning Roadmap — Ordered by Market Demand",
         bg=C["navy"], size=13, colspan=5)
    _hdr(ws, 2, 1, "Priority",     bg=C["gray_hdr"])
    _hdr(ws, 2, 2, "Skill to Learn", bg=C["gray_hdr"])
    _hdr(ws, 2, 3, "Market Demand", bg=C["gray_hdr"])
    _hdr(ws, 2, 4, "Type",          bg=C["gray_hdr"])
    _hdr(ws, 2, 5, "Why It Matters", bg=C["gray_hdr"])

    all_pct  = dict(gap["all_ranked"])
    miss_req = set(gap["missing_required"])
    priority = gap["priority_list"]

    WHY = {
        "python":       "Foundation for data pipelines, ML, and automation",
        "sql":          "Universal querying skill — every analyst role requires it",
        "excel":        "Still dominant in mid-market reporting and finance",
        "power bi":     "Most-requested BI tool in Indian corporate market",
        "tableau":      "Preferred in analytics and consulting roles",
        "machine learning": "Core for AI/ML roles and data scientist positions",
        "pandas":       "Standard data manipulation library for Python",
        "numpy":        "Scientific computing backbone for data roles",
        "r":            "Statistical analysis in research and pharma sectors",
        "spark":        "Big data processing for senior data engineering roles",
        "aws":          "Cloud infrastructure requirement in most tech companies",
        "docker":       "Containerisation — growing requirement across all tiers",
        "git":          "Version control — baseline expectation everywhere",
    }

    for i, skill in enumerate(priority, 1):
        r = 2 + i
        pct = all_pct.get(skill, 0)
        is_req = skill in miss_req

        if i <= 3:
            bg = C["red_light"]
            priority_label = f"🔴 #{i} — Urgent"
        elif i <= 7:
            bg = C["amber_light"]
            priority_label = f"🟡 #{i} — High"
        else:
            bg = C["green_light"]
            priority_label = f"🟢 #{i} — Useful"

        why = WHY.get(skill.lower(), "Appears frequently in job descriptions for this market")
        _cell(ws, r, 1, priority_label, bg=bg, bold=(i <= 3))
        _cell(ws, r, 2, skill.title(),  bg=bg, bold=(i <= 3))
        _cell(ws, r, 3, f"{pct}% of JDs", bg=bg, align="center")
        _cell(ws, r, 4, "Required" if is_req else "Useful", bg=bg, align="center")
        _cell(ws, r, 5, why, bg=bg)

    _set_col_widths(ws, {"A":20,"B":22,"C":16,"D":12,"E":50})
    ws.row_dimensions[1].height = 28
    for r in range(3, 3 + len(priority)):
        ws.row_dimensions[r].height = 20


# ── Sheet 4: Cluster Comparison ───────────────────────────────────────────────
def _sheet_clusters(wb, target_tier):
    ws = wb.create_sheet("🏢 Cluster Comparison")
    ws.sheet_view.showGridLines = False

    _hdr(ws, 1, 1, "Company Tier Comparison — What Each Tier Actually Demands",
         bg=C["navy"], size=13, colspan=4)
    _hdr(ws, 2, 1, "Tier",           bg=C["gray_hdr"])
    _hdr(ws, 2, 2, "Required Skills", bg=C["gray_hdr"])
    _hdr(ws, 2, 3, "Useful Skills",   bg=C["gray_hdr"])
    _hdr(ws, 2, 4, "Typical Companies", bg=C["gray_hdr"])

    TIER_DATA = [
        ("FAANG / Tier-1",
         "Python, SQL, Spark, ML, System Design, AWS, Docker, Git",
         "Scala, Kafka, Kubernetes, A/B Testing, Statistics",
         "Google, Amazon, Microsoft, Goldman Sachs, Flipkart, Infosys"),
        ("Series A / Startup",
         "Python, SQL, FastAPI, React, AWS, Git",
         "LLMs, LangChain, Docker, Redis, Postgres",
         "Zepto, Razorpay, CRED, Groww, BrowserStack"),
        ("Mid-market / Consulting",
         "SQL, Excel, Power BI, Python, Tableau",
         "Pandas, NumPy, Looker, R, Alteryx",
         "Deloitte, Capgemini, TCS, Wipro, KPMG"),
    ]

    for i, (tier, req, use, cos) in enumerate(TIER_DATA, 1):
        r = 2 + i
        highlight = tier.lower().replace(" ","").replace("/","") in \
                    target_tier.lower().replace(" ","").replace("/","")
        bg = C["teal_light"] if highlight else C["gray_light"]
        bold = highlight
        _cell(ws, r, 1, ("★ " if highlight else "") + tier,
              bg=bg, bold=bold)
        _cell(ws, r, 2, req, bg=bg, bold=bold)
        _cell(ws, r, 3, use, bg=bg)
        _cell(ws, r, 4, cos, bg=bg)
        ws.row_dimensions[r].height = 36

    if highlight is not None:
        note_r = 6
        _hdr(ws, note_r, 1,
             f"★ Highlighted row = your target tier ({target_tier})",
             bg=C["teal"], bold=False, size=10, colspan=4)

    _set_col_widths(ws, {"A":22,"B":40,"C":36,"D":44})


# ── Public entry point ────────────────────────────────────────────────────────
def generate_gap_report(user_skills: list[str],
                         target_tier: str,
                         role: str = "") -> BytesIO:
    """
    Full pipeline:
      1. Runs analyze_gap() fresh from CSV
      2. Builds 4-sheet XLSX workbook
      3. Returns BytesIO ready for st.download_button

    Sheets:
      📋 Summary          — readiness score, have/missing matrix
      📊 Market Intelligence — top 20 skills ranked by % frequency + bar chart
      🗺️ Learning Roadmap  — priority-ordered skill plan with WHY
      🏢 Cluster Comparison — what each company tier actually needs
    """
    from analysis.gap_analyzer import analyze_gap
    gap = analyze_gap(user_skills, target_tier)

    wb = Workbook()
    _sheet_summary(wb, gap, role, target_tier, user_skills)
    _sheet_market(wb, gap, role)
    _sheet_roadmap(wb, gap)
    _sheet_clusters(wb, target_tier)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf