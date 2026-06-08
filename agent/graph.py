# agent/graph.py
# LangGraph StateGraph ReAct agent
# Nodes: agent_node ↔ tool_node
# Edges: conditional routing — has tool_calls → tools, else END
# MemorySaver checkpointer persists multi-turn state per thread_id

import os
import re as _re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from agent.state import AgentState
from agent.tools import (
    search_jobs_tool, extract_skills_tool,
    cluster_analysis_tool, gap_analysis_tool,
)

load_dotenv()

# ── Tool registry ─────────────────────────────────────────────────────────────
TOOLS = [search_jobs_tool, extract_skills_tool, cluster_analysis_tool, gap_analysis_tool]

# ── System prompt ─────────────────────────────────────────────────────────────
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


# ── LLM factory ───────────────────────────────────────────────────────────────
def _get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
    ).bind_tools(TOOLS)


# ── Graph nodes ───────────────────────────────────────────────────────────────
def _agent_node(state: AgentState) -> dict:
    """
    Calls LLM with full message history.
    System prompt prepended at call time — not stored in state.
    """
    messages = list(state["messages"])
    llm_input = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = _get_llm().invoke(llm_input)
    return {"messages": [response]}


def _should_continue(state: AgentState):
    """
    Conditional routing:
    - has tool_calls → execute tools
    - no tool_calls  → end this turn
    """
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return END


# ── Graph singleton ───────────────────────────────────────────────────────────
_checkpointer = MemorySaver()
_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    builder = StateGraph(AgentState)

    # Nodes
    builder.add_node("agent", _agent_node)
    builder.add_node("tools", ToolNode(TOOLS))

    # Entry
    builder.set_entry_point("agent")

    # Edges
    builder.add_conditional_edges(
        "agent",
        _should_continue,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "agent")   # after tools → back to agent

    _compiled_graph = builder.compile(checkpointer=_checkpointer)
    return _compiled_graph


# ── Public API ────────────────────────────────────────────────────────────────
def run_chat_turn(
    user_message: str,
    history: list,
    thread_id: str = "default",
) -> tuple[str, list]:
    """
    Process one user turn through the LangGraph StateGraph agent.

    Args:
        user_message : text from the user
        history      : kept for backward-compat; LangGraph manages state
                       internally via MemorySaver + thread_id
        thread_id    : unique ID per conversation session

    Returns:
        (response_text, updated_messages_list)
    """
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
    )

    messages = result.get("messages", [])

    # Find the last plain AI response (no pending tool calls)
    final_content = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            final_content = msg.content
            break

    return final_content, messages


# ── Helper ────────────────────────────────────────────────────────────────────
def extract_role_from_message(text: str) -> str | None:
    _KNOWN = [
        "data analyst", "data scientist", "data engineer", "business analyst",
        "software engineer", "software developer", "flutter developer",
        "react developer", "python developer", "java developer",
        "frontend developer", "backend developer", "full stack developer",
        "machine learning engineer", "ml engineer", "ai engineer",
        "product manager", "devops engineer",
    ]
    tl = text.lower()
    for r in _KNOWN:
        if r in tl:
            return r.title()
    m = _re.search(
        r'\b([a-z]+(?:\s+[a-z]+)?)\s+'
        r'(developer|analyst|engineer|manager|designer|scientist)\b', tl
    )
    if m and m.group(1) not in ("a", "the", "any", "software"):
        return (m.group(1) + " " + m.group(2)).title()
    return None


# ── Greeting ──────────────────────────────────────────────────────────────────
GREETING = (
    "👋 Hi! I'm <span style='color:#F0C040'>**JobHarvestor**</span>, your AI job market intelligence agent.\n\n"
    "I analyze real job postings scraped from <span style='color:#F0C040'>**LinkedIn**</span>, "
    "<span style='color:#F0C040'>**Naukri**</span>, and <span style='color:#F0C040'>**Internshala**</span> "
    "to tell you exactly what the market demands — with real percentages, not guesses.\n\n"
    "Here's what I can do:\n"
    "• Find jobs for <span style='color:#F0C040'>**any role**</span> in your local market\n"
    "• Show you the <span style='color:#F0C040'>**top skills**</span> with their % frequency in JDs\n"
    "• Show you **what you know vs what the market requires**\n"
    "• Build a **ranked learning roadmap** based on your skill gaps\n\n"
    "**What <span style='color:#F0C040'>role</span> are you looking to explore, and which <span style='color:#F0C040'>city</span>?**\n"
    "*(e.g. \"Data Analyst in Pune\", \"Flutter Developer in Bangalore\", "
    "\"ML Engineer remote\" — any role + location works)*"
)


# ── Legacy one-shot mode (backward compat) ────────────────────────────────────
def run_agent(
    role: str,
    user_skills: list[str],
    target_tier: str,
    location: str = "India",
) -> dict:
    user_skills_str = ", ".join(user_skills)
    query = (
        f"Please analyze '{role}' jobs for someone targeting {target_tier} companies. "
        f"My current skills are: {user_skills_str}. "
        f"Search the jobs, extract market skill requirements, and run a gap analysis for me."
    )
    response_text, _ = run_chat_turn(query, [], thread_id="legacy_oneshot")

    gap_data = None
    try:
        from analysis.gap_analyzer import analyze_gap
        gap_data = analyze_gap(user_skills, target_tier)
    except Exception:
        pass

    return {"agent_response": response_text, "gap_data": gap_data, "messages": []}