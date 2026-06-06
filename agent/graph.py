# agent/graph.py
# Proper conversational ReAct agent — NOT a one-shot pipeline
# run_chat_turn() handles one user message, returns response + updated history
# History is a list of LangChain message objects persisted in st.session_state

import json
import re as _re
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from agent.tools import (
    search_jobs_tool, extract_skills_tool,
    cluster_analysis_tool, gap_analysis_tool
)

load_dotenv()

# ── Tools registry ────────────────────────────────────────────────────────────
TOOLS     = [search_jobs_tool, extract_skills_tool, cluster_analysis_tool, gap_analysis_tool]
TOOLS_MAP = {t.name: t for t in TOOLS}
def extract_role_from_message(text: str) -> str | None:
    """
    LangGraph-side role extractor.
    Used by the graph state to seed 'role' without waiting for LLM.
    """
    _KNOWN = [
        "data analyst","data scientist","data engineer","business analyst",
        "software engineer","software developer","flutter developer",
        "react developer","python developer","java developer","frontend developer",
        "backend developer","full stack developer","machine learning engineer",
        "ml engineer","ai engineer","product manager","devops engineer",
    ]
    tl = text.lower()
    for r in _KNOWN:
        if r in tl:
            return r.title()
    m = _re.search(
        r'\b([a-z]+(?:\s+[a-z]+)?)\s+'
        r'(developer|analyst|engineer|manager|designer|scientist)\b', tl)
    if m and m.group(1) not in ("a","the","any","software"):
        return (m.group(1) + " " + m.group(2)).title()
    return None


# ── System prompt: conversational, question-driven ────────────────────────────
SYSTEM_PROMPT = """You are JobHarvestor, an AI job market intelligence agent. You help people understand what the job market actually demands — with real percentages from scraped job descriptions — and give them a personalized skill gap analysis.

YOU ARE CONVERSATIONAL. You ask questions one at a time. You DO NOT dump all analysis at once.

CONVERSATION FLOW (follow this order):
1. Ask what role/job they want to explore — extract the keyword from their answer
1b. IMMEDIATELY ask for location if not already provided: "Which city or region should I search in? (e.g. Pune, Mumbai, Bangalore, Delhi, Remote)" — do NOT skip this step
2. Call search_jobs_tool with that role + location → report what you found (how many jobs, top companies)
3. Ask about their target company tier: FAANG/Big-tech, Startup/Series A, or Mid-market/Consulting
4. Call extract_skills_tool(role) + cluster_analysis_tool(tier) simultaneously
5. Share the top 5 in-demand skills with their % — then ask "what are your current skills?"
6. Call gap_analysis_tool(user_skills_csv, target_tier) with what they told you
7. Present: readiness score, skills they have ✓, critical gaps ✗, ranked learning roadmap

LOCATION RULES (CRITICAL):
- Location is MANDATORY before calling search_jobs_tool. Never skip asking for it.
- Extract location from natural language: "in Pune", "Bangalore jobs", "remote", "Mumbai market"
- If user says the role and location in one message (e.g. "Data Analyst in Pune") extract both and proceed
- If user gives only the role, ask: "Got it! Which city should I focus on? (Pune, Mumbai, Bangalore, Delhi, Remote, India-wide)"
- Only after BOTH role AND location are known should you call search_jobs_tool

TOOL CALLING RULES:
- search_jobs_tool: call only after BOTH role AND location are confirmed
- extract_skills_tool: call after role is confirmed  
- cluster_analysis_tool: call after tier is confirmed
- gap_analysis_tool: call ONLY after user has shared their skills — use EXACTLY what they said
- Never call the same tool twice with the same args

CONVERSATION RULES:
- ONE question per message
- Extract info from natural language ("I know Python and SQL" → user_skills_csv="Python,SQL")
- After tool results, always summarize what you found in 1-2 sentences before asking next question
- Quote real numbers: "Python appears in 67% of JDs" not "Python is popular"
- If user asks something off-topic, answer briefly then steer back to the analysis
- If no CSV data exists yet, tell them to run the scrape pipeline first

TONE: Warm, direct, data-driven. Like a career coach who actually looked at the data."""


# ── LLM factory ──────────────────────────────────────────────────────────────
def _get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3
    ).bind_tools(TOOLS)


# ── Core conversational turn ──────────────────────────────────────────────────
def run_chat_turn(user_message: str, history: list) -> tuple[str, list]:
    """
    Process one user message through the agent.

    Args:
        user_message: what the user just typed
        history: list of LangChain message objects from previous turns
                 (starts empty, grows each turn — persisted in st.session_state)

    Returns:
        (response_text, updated_history)

    The agent loop:
        invoke LLM → if tool_calls → execute tools → append ToolMessages → invoke again
        Repeat until LLM returns a plain text response (no tool calls).
    """
    llm = _get_llm()

    # Initialize history with system prompt on first turn
    if not history:
        history = [SystemMessage(content=SYSTEM_PROMPT)]

    history.append(HumanMessage(content=user_message))

    # ReAct loop — max 10 iterations to prevent infinite loops
    final_content = ""
    for iteration in range(10):
        response = llm.invoke(history)
        history.append(response)

        # No tool calls → agent is done for this turn
        if not (hasattr(response, "tool_calls") and response.tool_calls):
            final_content = response.content
            break

        # Execute each tool call and append results
        for tc in response.tool_calls:
            tool_name = tc.get("name", "")
            tool_args = tc.get("args", {})
            tool_call_id = tc.get("id", f"call_{iteration}")

            try:
                if tool_name in TOOLS_MAP:
                    result = TOOLS_MAP[tool_name].invoke(tool_args)
                    result_str = str(result) if not isinstance(result, str) else result
                else:
                    result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})
            except Exception as e:
                result_str = json.dumps({"error": str(e), "tool": tool_name})

            history.append(
                ToolMessage(content=result_str, tool_call_id=tool_call_id)
            )

    return final_content, history


# ── Greeting message ──────────────────────────────────────────────────────────
GREETING = (
    "👋 Hi! I'm **JobHarvestor**, your AI job market intelligence agent.\n\n"
    "I analyze real job postings scraped from LinkedIn, Naukri, and Internshala "
    "to tell you exactly what the market demands — with real percentages, not guesses.\n\n"
    "Here's what I can do:\n"
    "• Find jobs for **any role** in your local market\n"
    "• Show you the **top skills** with their % frequency in JDs\n"
    "• Give you a **readiness score** vs what the market requires\n"
    "• Build a **ranked learning roadmap** based on your skill gaps\n\n"
    "**What role are you looking to explore, and which city?**\n"
    "*(e.g. \"Data Analyst in Pune\", \"Flutter Developer in Bangalore\", \"ML Engineer remote\" — any role + location works)*"
)


# ── Legacy one-shot mode (kept for backward compat) ───────────────────────────
def run_agent(role: str, user_skills: list[str], target_tier: str, location: str = "India") -> dict:
    """
    One-shot mode. Kept so existing sidebar analyze button still works.
    Internally uses run_chat_turn with a constructed query.
    """
    user_skills_str = ", ".join(user_skills)
    query = (
        f"Please analyze '{role}' jobs for someone targeting {target_tier} companies. "
        f"My current skills are: {user_skills_str}. "
        f"Search the jobs, extract market skill requirements, and run a gap analysis for me."
    )
    response_text, _ = run_chat_turn(query, [])

    gap_data = None
    try:
        from analysis.gap_analyzer import analyze_gap
        gap_data = analyze_gap(user_skills, target_tier)
    except Exception:
        pass

    return {"agent_response": response_text, "gap_data": gap_data, "messages": []}