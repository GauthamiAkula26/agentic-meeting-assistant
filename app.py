from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from utils.extractors import (
    build_overview_summary,
    enrich_decision_statuses,
    extract_action_items,
    extract_decisions,
    extract_risks,
)
from utils.formatting import decisions_to_df, risks_to_df, tasks_to_df
from utils.llm import llm_answer
from utils.nlp import chunk_text, search_across_meetings, search_chunks
from utils.storage import delete_meeting, load_meetings, upsert_meeting

load_dotenv()

st.set_page_config(
    page_title="Agentic Meeting Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

SAMPLE_DIR = Path("data/sample_meetings")


def apply_premium_ui() -> None:
    st.markdown(
        """
        <style>
        .main {
            background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
        }

        .block-container {
            padding-top: 1.3rem;
            padding-bottom: 2rem;
        }

        h1, h2, h3 {
            font-weight: 700;
            color: #0f172a;
        }

        .hero-card {
            background: linear-gradient(135deg, #ffffff 0%, #eef2ff 100%);
            padding: 24px;
            border-radius: 22px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 10px 30px rgba(0,0,0,0.06);
            margin-bottom: 18px;
        }

        .card {
            background: white;
            padding: 18px;
            border-radius: 18px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 6px 20px rgba(0,0,0,0.05);
            margin-bottom: 16px;
        }

        .metric-card {
            background: white;
            padding: 18px 12px;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            text-align: center;
            box-shadow: 0 6px 20px rgba(0,0,0,0.05);
        }

        .metric-title {
            color: #64748b;
            font-size: 0.9rem;
            margin-top: 6px;
        }

        .metric-value {
            color: #0f172a;
            font-size: 1.8rem;
            font-weight: 800;
        }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            margin-right: 8px;
            margin-top: 6px;
        }

        .badge-blue { background:#dbeafe; color:#1d4ed8; }
        .badge-green { background:#dcfce7; color:#166534; }
        .badge-red { background:#fee2e2; color:#b91c1c; }
        .badge-yellow { background:#fef3c7; color:#92400e; }
        .badge-purple { background:#ede9fe; color:#6d28d9; }

        .muted {
            color:#64748b;
            font-size:0.95rem;
        }

        .section-label {
            font-size: 1.05rem;
            font-weight: 700;
            color:#0f172a;
            margin-bottom: 10px;
        }

        .risk-card {
            background: white;
            padding: 18px;
            border-radius: 16px;
            border: 1px solid #fecaca;
            border-left: 6px solid #ef4444;
            box-shadow: 0 6px 20px rgba(0,0,0,0.04);
            margin-bottom: 14px;
        }

        .action-card {
            background: white;
            padding: 18px;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            border-left: 6px solid #4f46e5;
            box-shadow: 0 6px 20px rgba(0,0,0,0.04);
            margin-bottom: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <h1>🧠 Agentic Meeting Assistant</h1>
            <p class="muted">
                Turn meetings into decisions, action items, risks, and persistent memory.
                Search across meetings, track follow-ups, and export structured outputs.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(title: str, value: int) -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-title">{title}</div>
    </div>
    """


def sample_meeting_options() -> Dict[str, Path]:
    return {p.stem.replace("_", " ").title(): p for p in SAMPLE_DIR.glob("*.txt")}


def read_uploaded_text(uploaded_file) -> str:
    return uploaded_file.read().decode("utf-8", errors="ignore")


def process_meeting(title: str, date: str, text: str, project: str, participants: List[str]) -> Dict:
    decisions = extract_decisions(text)
    actions = extract_action_items(text)
    risks = extract_risks(text)
    chunks = chunk_text(text, chunk_size=900, overlap=120)
    overview = build_overview_summary(text, decisions, actions, risks)

    existing = load_meetings()
    prior = [m for m in existing if m.get("title") != title]

    meeting = {
        "meeting_id": str(uuid.uuid4()),
        "title": title,
        "date": date,
        "project": project or "General",
        "participants": participants,
        "raw_text": text,
        "chunks": chunks,
        "decisions": decisions,
        "actions": actions,
        "risks": risks,
        "overview": overview,
        "created_at": datetime.utcnow().isoformat(),
    }

    meeting["decisions"] = enrich_decision_statuses(meeting, prior)
    return meeting


def render_empty_state(message: str) -> None:
    st.markdown(
        f"""
        <div class="card">
            <h3>No data yet</h3>
            <p class="muted">{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_decision_cards(decisions: List[Dict]) -> None:
    if not decisions:
        st.info("No decisions found.")
        return

    for d in decisions:
        related = ""
        if d.get("related_meetings"):
            related = f'<span class="badge badge-purple">Related: {", ".join(d["related_meetings"])}</span>'

        st.markdown(
            f"""
            <div class="card">
                <div><strong>📌 {d.get("decision")}</strong></div>
                <div class="muted" style="margin-top:8px;">{d.get("source","")}</div>
                <div>
                    <span class="badge badge-blue">Speaker: {d.get("speaker") or "Unknown"}</span>
                    <span class="badge badge-green">{d.get("status","Active")}</span>
                    {related}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_action_cards(actions: List[Dict]) -> None:
    if not actions:
        st.info("No action items found.")
        return

    for task in actions:
        status_badge = "badge-green" if task.get("status") == "Done" else "badge-yellow"
        st.markdown(
            f"""
            <div class="action-card">
                <div><strong>✅ {task.get("task")}</strong></div>
                <div class="muted" style="margin-top:8px;">{task.get("source","")}</div>
                <div>
                    <span class="badge badge-blue">Owner: {task.get("owner")}</span>
                    <span class="badge badge-purple">Due: {task.get("due_date")}</span>
                    <span class="badge {status_badge}">{task.get("status")}</span>
                    <span class="badge badge-yellow">Priority: {task.get("priority")}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_risk_cards(risks: List[Dict]) -> None:
    if not risks:
        st.success("No risks detected.")
        return

    for risk in risks:
        severity_class = "badge-red" if risk.get("severity") == "High" else "badge-yellow"
        st.markdown(
            f"""
            <div class="risk-card">
                <div><strong>⚠️ {risk.get("risk")}</strong></div>
                <div class="muted" style="margin-top:8px;">{risk.get("source","")}</div>
                <div>
                    <span class="badge {severity_class}">{risk.get("severity")}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def dashboard_page(meetings: List[Dict]) -> None:
    render_hero()

    total_meetings = len(meetings)
    total_actions = sum(len(m.get("actions", [])) for m in meetings)
    open_tasks = sum(
        1 for m in meetings for a in m.get("actions", []) if a.get("status", "Open") == "Open"
    )
    total_decisions = sum(len(m.get("decisions", [])) for m in meetings)
    total_risks = sum(len(m.get("risks", [])) for m in meetings)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(metric_card("Meetings", total_meetings), unsafe_allow_html=True)
    c2.markdown(metric_card("Decisions", total_decisions), unsafe_allow_html=True)
    c3.markdown(metric_card("Action Items", total_actions), unsafe_allow_html=True)
    c4.markdown(metric_card("Open Tasks", open_tasks), unsafe_allow_html=True)
    c5.markdown(metric_card("Risks", total_risks), unsafe_allow_html=True)

    st.markdown("### Recent Meetings")

    if not meetings:
        render_empty_state("Upload or process a transcript to create your first meeting record.")
        return

    rows = []
    for m in sorted(meetings, key=lambda x: x.get("date", ""), reverse=True):
        rows.append(
            {
                "Date": m.get("date"),
                "Title": m.get("title"),
                "Project": m.get("project"),
                "Participants": ", ".join(m.get("participants", [])),
                "Decisions": len(m.get("decisions", [])),
                "Actions": len(m.get("actions", [])),
                "Risks": len(m.get("risks", [])),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("### Quick Capabilities")
    st.markdown(
        """
        <div class="card">
            <span class="badge badge-blue">Decision Tracking</span>
            <span class="badge badge-purple">Task Extraction</span>
            <span class="badge badge-yellow">Risk Detection</span>
            <span class="badge badge-green">Cross-Meeting Memory</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workspace_page(meetings: List[Dict]) -> None:
    render_hero()
    st.markdown("## Meeting Workspace")
    st.caption("Upload or select a transcript, process it, and save structured meeting memory.")

    left, right = st.columns([1.1, 0.9])

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        source_mode = st.radio("Transcript source", ["Use sample transcript", "Upload transcript"], horizontal=True)
        sample_map = sample_meeting_options()
        selected_sample = None
        uploaded = None

        if source_mode == "Use sample transcript":
            selected_sample = st.selectbox("Choose sample meeting", list(sample_map.keys()))
        else:
            uploaded = st.file_uploader("Upload transcript (.txt)", type=["txt"])

        title = st.text_input("Meeting title", value="Launch Readiness Review")
        date_val = st.date_input("Meeting date", value=datetime.utcnow().date())
        project = st.text_input("Project / Workstream", value="Customer Insights Dashboard")
        participants_raw = st.text_input(
            "Participants (comma-separated)",
            value="Anita, Ravi, Maya, Karan",
        )

        if st.button("Process and Save Meeting", use_container_width=True):
            text = ""

            if source_mode == "Use sample transcript" and selected_sample:
                text = sample_map[selected_sample].read_text(encoding="utf-8")
            elif uploaded is not None:
                text = read_uploaded_text(uploaded)

            if not text.strip():
                st.error("Please provide a transcript.")
            else:
                participants = [p.strip() for p in participants_raw.split(",") if p.strip()]
                meeting = process_meeting(
                    title=title.strip() or "Untitled Meeting",
                    date=str(date_val),
                    text=text,
                    project=project.strip(),
                    participants=participants,
                )
                upsert_meeting(meeting)
                st.session_state["active_meeting_id"] = meeting["meeting_id"]
                st.success("✅ Meeting processed and saved.")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Stored Meetings")
        if not meetings:
            st.info("No meetings saved yet.")
        else:
            for meeting in sorted(meetings, key=lambda x: x.get("date", ""), reverse=True):
                with st.expander(f"{meeting.get('date')} · {meeting.get('title')}"):
                    st.write(meeting.get("overview"))
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Open", key=f"open_{meeting['meeting_id']}"):
                            st.session_state["active_meeting_id"] = meeting["meeting_id"]
                            st.rerun()
                    with col_b:
                        if st.button("Delete", key=f"delete_{meeting['meeting_id']}"):
                            delete_meeting(meeting["meeting_id"])
                            st.success("Meeting deleted.")
                            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    meetings = load_meetings()
    active_id = st.session_state.get("active_meeting_id")
    active = next((m for m in meetings if m.get("meeting_id") == active_id), None)

    if not active and meetings:
        active = sorted(meetings, key=lambda x: x.get("date", ""), reverse=True)[0]

    if active:
        st.markdown("---")
        st.markdown(f"## Active Meeting · {active.get('title')}")
        st.caption(f"{active.get('date')} · {active.get('project')}")

        overview_tab, decisions_tab, tasks_tab, risks_tab, transcript_tab = st.tabs(
            ["Overview", "Decisions", "Action Items", "Risks", "Transcript"]
        )

        with overview_tab:
            st.markdown(
                f"""
                <div class="card">
                    <div class="section-label">Meeting Summary</div>
                    <p>{active.get("overview")}</p>
                    <span class="badge badge-blue">{len(active.get("decisions", []))} decisions</span>
                    <span class="badge badge-purple">{len(active.get("actions", []))} action items</span>
                    <span class="badge badge-yellow">{len(active.get("risks", []))} risks</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with decisions_tab:
            st.dataframe(decisions_to_df(active.get("decisions", [])), use_container_width=True, hide_index=True)
            st.markdown("### Decision Cards")
            render_decision_cards(active.get("decisions", []))

        with tasks_tab:
            task_df = tasks_to_df(active.get("actions", []))
            edited = st.data_editor(
                task_df,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key="task_editor",
            )

            if st.button("Save Task Status Updates"):
                updated_actions = active.get("actions", [])
                for idx, row in edited.iterrows():
                    if idx < len(updated_actions):
                        updated_actions[idx]["status"] = row.get("status", updated_actions[idx]["status"])
                        updated_actions[idx]["priority"] = row.get("priority", updated_actions[idx]["priority"])
                active["actions"] = updated_actions
                upsert_meeting(active)
                st.success("Task updates saved.")
                st.rerun()

            st.markdown("### Action Item Cards")
            render_action_cards(active.get("actions", []))

        with risks_tab:
            st.dataframe(risks_to_df(active.get("risks", [])), use_container_width=True, hide_index=True)
            st.markdown("### Risk Cards")
            render_risk_cards(active.get("risks", []))

        with transcript_tab:
            st.text_area("Transcript", value=active.get("raw_text", ""), height=450)


def memory_page(meetings: List[Dict]) -> None:
    render_hero()
    st.markdown("## Persistent Meeting Memory")
    st.caption("Search across all meetings and track changes in discussion context over time.")

    if not meetings:
        render_empty_state("Save at least one meeting to enable persistent memory search.")
        return

    question = st.text_input(
        "Ask across all meetings",
        placeholder="What changed about launch timing across meetings?",
    )

    col1, col2 = st.columns(2)
    with col1:
        project_filter = st.selectbox(
            "Filter by project",
            ["All"] + sorted(list({m.get("project", "General") for m in meetings})),
        )
    with col2:
        sort_by = st.selectbox("Sort results", ["Best match", "Newest first"])

    filtered = meetings
    if project_filter != "All":
        filtered = [m for m in meetings if m.get("project") == project_filter]

    if question.strip():
        results = search_across_meetings(question, filtered, top_k=10)
        if sort_by == "Newest first":
            results = sorted(results, key=lambda x: x.get("date", ""), reverse=True)

        st.markdown("### Search Results")
        for res in results:
            st.markdown(
                f"""
                <div class="card">
                    <strong>{res.get("meeting_title")}</strong> · {res.get("date")} · {res.get("project")}
                    <div class="muted" style="margin-top:8px;">{res.get("text")}</div>
                    <div>
                        <span class="badge badge-blue">Score: {res.get("score"):.4f}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        rows = []
        for meeting in filtered:
            for d in meeting.get("decisions", []):
                rows.append(
                    {
                        "Meeting": meeting.get("title"),
                        "Date": meeting.get("date"),
                        "Decision": d.get("decision"),
                        "Status": d.get("status"),
                    }
                )

        if rows:
            st.markdown("### Cross-Meeting Decisions")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("💡 Try: What changed about launch timing?")


def ask_ai_page(meetings: List[Dict]) -> None:
    render_hero()
    st.markdown("## Ask AI")
    st.caption("Ask questions about a single meeting or across the entire meeting history.")

    if not meetings:
        render_empty_state("Save meetings first to use AI search.")
        return

    scope = st.radio("Question scope", ["Single meeting", "All meetings"], horizontal=True)
    use_openai = st.checkbox("Use OpenAI for synthesized answer", value=False)
    api_key = st.text_input("OpenAI API Key", type="password")

    if scope == "Single meeting":
        options = {f"{m.get('date')} · {m.get('title')}": m for m in meetings}
        selected_label = st.selectbox("Choose meeting", list(options.keys()))
        meeting = options[selected_label]
        question = st.text_input("Question", placeholder="What are the highest-priority blockers?")

        if st.button("Run Query", use_container_width=True):
            if not question.strip():
                st.error("Enter a question.")
            else:
                results = search_chunks(question, meeting.get("chunks", []), top_k=5)
                context = "\n\n---\n\n".join([r["text"] for r in results])

                if use_openai and api_key.strip():
                    answer = llm_answer(question, context, api_key.strip())
                else:
                    answer = "Top matching evidence is shown below."

                st.subheader("Answer")
                st.write(answer)

                st.subheader("Evidence")
                for idx, r in enumerate(results, start=1):
                    with st.expander(f"Chunk {idx} · score {r['score']:.4f}", expanded=(idx == 1)):
                        st.write(r["text"])

    else:
        question = st.text_input("Question across all meetings", placeholder="Which decisions have changed over time?")

        if st.button("Run Memory Query", use_container_width=True):
            if not question.strip():
                st.error("Enter a question.")
            else:
                results = search_across_meetings(question, meetings, top_k=8)
                context = "\n\n---\n\n".join(
                    [f"{r['meeting_title']} ({r['date']}):\n{r['text']}" for r in results]
                )

                if use_openai and api_key.strip():
                    answer = llm_answer(question, context, api_key.strip())
                else:
                    answer = "Top matching evidence from meeting memory is shown below."

                st.subheader("Answer")
                st.write(answer)

                st.subheader("Evidence")
                for idx, r in enumerate(results, start=1):
                    with st.expander(f"{r['meeting_title']} · score {r['score']:.4f}", expanded=(idx == 1)):
                        st.write(r["text"])


def integrations_page(meetings: List[Dict]) -> None:
    render_hero()
    st.markdown("## Integrations & Agent Actions")
    st.caption("Export structured outputs and close the loop after meetings.")

    st.markdown(
        """
        <div class="card">
            <strong>Available Actions</strong>
            <div class="muted" style="margin-top:8px;">
                Sync action items to Jira · Export markdown summary · Preview Slack message
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not meetings:
        render_empty_state("Save at least one meeting to enable exports.")
        return

    options = {f"{m.get('date')} · {m.get('title')}": m for m in meetings}
    selected_label = st.selectbox("Choose meeting for export", list(options.keys()))
    meeting = options[selected_label]

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Generate Jira-ready CSV", use_container_width=True):
            df = tasks_to_df(meeting.get("actions", []))
            st.download_button(
                label="Download CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"{meeting.get('title','meeting').replace(' ','_').lower()}_tasks.csv",
                mime="text/csv",
            )

    with col2:
        if st.button("Generate Markdown Summary", use_container_width=True):
            md = [f"# {meeting.get('title')}\n", f"Date: {meeting.get('date')}\n", "## Decisions"]
            for d in meeting.get("decisions", []):
                md.append(f"- {d.get('decision')} ({d.get('status')})")

            md.append("\n## Action Items")
            for a in meeting.get("actions", []):
                md.append(
                    f"- {a.get('task')} | Owner: {a.get('owner')} | Due: {a.get('due_date')} | Status: {a.get('status')}"
                )

            md.append("\n## Risks")
            for r in meeting.get("risks", []):
                md.append(f"- {r.get('risk')} | Severity: {r.get('severity')}")

            st.download_button(
                label="Download Markdown",
                data="\n".join(md).encode("utf-8"),
                file_name=f"{meeting.get('title','meeting').replace(' ','_').lower()}_summary.md",
                mime="text/markdown",
            )

    with col3:
        if st.button("Preview Slack Message", use_container_width=True):
            st.code(
                f"""*{meeting.get('title')}* ({meeting.get('date')})
Summary: {meeting.get('overview')}

Decisions:
{chr(10).join('- ' + d.get('decision') for d in meeting.get('decisions', [])[:3])}

Action Items:
{chr(10).join('- ' + a.get('task') + ' (' + a.get('owner') + ')' for a in meeting.get('actions', [])[:3])}
""",
                language="markdown",
            )


def main() -> None:
    apply_premium_ui()
    meetings = load_meetings()

    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        page = st.radio(
            "",
            [
                "Dashboard",
                "Meeting Workspace",
                "Persistent Memory",
                "Ask AI",
                "Integrations",
            ],
        )

        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        st.caption("Agentic Meeting Assistant v2")
        st.markdown("- Premium SaaS UI")
        st.markdown("- Decision tracking")
        st.markdown("- Task extraction")
        st.markdown("- Persistent memory")

    if page == "Dashboard":
        dashboard_page(meetings)
    elif page == "Meeting Workspace":
        workspace_page(meetings)
    elif page == "Persistent Memory":
        memory_page(meetings)
    elif page == "Ask AI":
        ask_ai_page(meetings)
    else:
        integrations_page(meetings)


if __name__ == "__main__":
    main()
