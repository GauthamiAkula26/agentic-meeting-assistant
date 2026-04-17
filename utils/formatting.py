from __future__ import annotations

from typing import Dict, List

import pandas as pd


def tasks_to_df(tasks: List[Dict]) -> pd.DataFrame:
    if not tasks:
        return pd.DataFrame(columns=["task", "owner", "due_date", "priority", "status"])
    return pd.DataFrame(tasks)[["task", "owner", "due_date", "priority", "status"]]


def decisions_to_df(decisions: List[Dict]) -> pd.DataFrame:
    if not decisions:
        return pd.DataFrame(columns=["decision", "speaker", "status"])

    df = pd.DataFrame(decisions)

    if "related_meetings" in df.columns:
        df["related_meetings"] = df["related_meetings"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else ""
        )
        return df[["decision", "speaker", "status", "related_meetings"]]

    return df[["decision", "speaker", "status"]]


def risks_to_df(risks: List[Dict]) -> pd.DataFrame:
    if not risks:
        return pd.DataFrame(columns=["risk", "severity"])
    return pd.DataFrame(risks)[["risk", "severity"]]
