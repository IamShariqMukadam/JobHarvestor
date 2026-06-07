# agent/state.py
# AgentState TypedDict — flows through all LangGraph nodes.
# messages uses operator.add (list concatenation) as the reducer,
# so each node's returned messages are appended to the running list.

from typing import TypedDict, Annotated
import operator


class AgentState(TypedDict):
    # Conversation messages — append-only via operator.add reducer
    messages: Annotated[list, operator.add]

    # Optional context populated by tools / caller
    role:         str
    target_tier:  str
    user_skills:  list[str]

    # Pipeline outputs
    raw_jobs:     list[dict]
    jd_texts:     list[str]
    extracted:    list[dict]   # per-JD LLM extraction results
    cluster_data: dict         # cluster profiles
    gap_report:   dict         # final gap analysis

    # Control flow
    error:        str
    done:         bool