# agent/state.py
# LangGraph requires a typed state dict that flows through all nodes
# Each node reads from and writes to this state

from typing import TypedDict, Annotated
import operator


class AgentState(TypedDict):
    # Input
    role:         str
    target_tier:  str
    user_skills:  list[str]

    # Populated by tools
    raw_jobs:     list[dict]
    jd_texts:     list[str]
    extracted:    list[dict]    # LLM extraction results per JD
    cluster_data: dict          # cluster profiles
    gap_report:   dict          # final gap analysis

    # Agent messaging — Annotated[list, operator.add] means append-only
    messages:     Annotated[list, operator.add]

    # Control flow
    error:        str
    done:         bool