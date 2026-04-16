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
    page_title="Meeting Intelligence Agent v2",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

SAMPLE_DIR = Path("data/sample_meetings")

def inject_css() -> None:
    st.markdown(
        """
        <style>
        .main {background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);}
        .app-title {font-size: 2.3rem; font-weight: 800; color: #0f172a; margin-bottom: 0.2rem;}
        .app-subtitle {color: #475569; margin-bottom: 1rem;}
        .metric-card {background: white; border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem 1.1rem; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);}
        .section-card {background: white; border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem 1.1rem; margin-bottom: 1rem; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);}
        .pill {display: inline-block; padding: 0.25rem 0.65rem; border-radius: 999px; font-size: 0.8rem; font-weight: 700; margin-right: 0.4rem; margin-bottom: 0.25rem;}
        .pill-blue { background: #dbeafe; color: #1d4ed8; }
        .pill-purple { background: #ede9fe; color: #6d28d9; }
        .pill-amber { background: #fef3c7; color: #b45309; }
        .action-card {border-left: 4px solid #4f46e5; background: #ffffff; border-radius: 14px; padding: 0.9rem 1rem; margin-bottom: 0.7rem; border-top: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb;}
        .muted { color: #64748b; font-size: 0.92rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

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

def dashboard_page(meetings: List[Dict]) -> None:
    st.markdown('<div class="app-title">Meeting Intelligence Agent v2</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Agentic task tracking, decision memory, cross-meeting search, and a product-style UI.</div>', unsafe_allow_html=True)
    total_meetings = len(meetings)
    total_actions = sum(len(m.get("actions", [])) for m in meetings)
    open_actions = sum(1 for m in meetings for a in m.get("actions", []) if a.get("status", "Open") == "Open")
    total_decisions = sum(len(m.get("decisions", [])) for m in meetings)
    total_risks = sum(len(m.get("risks", [])) for m in meetings)
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, value in [(c1, "Meetings", total_meetings),(c2, "Action Items", total_actions),(c3, "Open Tasks", open_actions),(c4, "Decisions", total_decisions),(c5, "Risks", total_risks)]:
        with col:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(label, value)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("### Recent Meetings")
    if not meetings:
        st.info("No meetings stored yet. Go to Meeting Workspace to process your first transcript.")
        return
    rows = []
    for m in sorted(meetings, key=lambda x: x.get("date", ""), reverse=True):
        rows.append({"Date": m.get("date"),"Title": m.get("title"),"Project": m.get("project"),"Participants": ", ".join(m.get("participants", [])),"Decisions": len(m.get("decisions", [])),"Actions": len(m.get("actions", [])),"Risks": len(m.get("risks", []))})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

def workspace_page(meetings: List[Dict]) -> None:
    st.markdown("## Meeting Workspace")
    st.caption("Process a transcript, extract structured outcomes, and save it into persistent meeting memory.")
    left, right = st.columns([1.1, 0.9])
    with left:
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
        participants_raw = st.text_input("Participants (comma-separated)", value="Anita, Ravi, Maya, Karan")
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
                meeting = process_meeting(title=title.strip() or "Untitled Meeting", date=str(date_val), text=text, project=project.strip(), participants=participants)
                upsert_meeting(meeting)
                st.session_state["active_meeting_id"] = meeting["meeting_id"]
                st.success("Meeting processed and saved to memory.")
                st.rerun()
    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("### Stored Meetings")
        if not meetings:
            st.info("No meetings saved yet.")
        else:
            for meeting in sorted(meetings, key=lambda x: x.get("date", ""), reverse=True):
                with st.expander(f"{meeting.get('date')} · {meeting.get('title')}"):
                    st.write(meeting.get("overview"))
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button(f"Open", key=f"open_{meeting['meeting_id']}"):
                            st.session_state["active_meeting_id"] = meeting["meeting_id"]
                    with col_b:
                        if st.button(f"Delete", key=f"del_{meeting['meeting_id']}"):
                            delete_meeting(meeting["meeting_id"])
                            st.success("Meeting deleted.")
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    meetings = load_meetings()
    active_id = st.session_state.get("active_meeting_id")
    active = next((m for m in meetings if m.get("meeting_id") == active_id), None)
    if not active and meetings:
        active = sorted(meetings, key=lambda x: x.get("date", ""), reverse=True)[0]
    if active:
        st.markdown("---")
        st.markdown(f"## Active Meeting · {active.get('title')}")
        st.caption(f"{active.get('date')} · {active.get('project')}")
        overview_tab, decisions_tab, tasks_tab, risks_tab, transcript_tab = st.tabs(["Overview", "Decisions", "Action Items", "Risks", "Transcript"])
        with overview_tab:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.write(active.get("overview"))
            st.markdown(
                f'<span class="pill pill-blue">{len(active.get("decisions", []))} decisions</span>'
                f'<span class="pill pill-purple">{len(active.get("actions", []))} tasks</span>'
                f'<span class="pill pill-amber">{len(active.get("risks", []))} risks</span>',
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
        with decisions_tab:
            st.dataframe(decisions_to_df(active.get("decisions", [])), use_container_width=True, hide_index=True)
            for d in active.get("decisions", []):
                st.markdown(f'<div class="action-card"><strong>{d.get("decision")}</strong><div class="muted">Speaker: {d.get("speaker") or "Unknown"} · Status: {d.get("status")}</div></div>', unsafe_allow_html=True)
        with tasks_tab:
            task_df = tasks_to_df(active.get("actions", []))
            edited = st.data_editor(task_df, use_container_width=True, hide_index=True, num_rows="fixed", key="task_editor")
            if st.button("Save Task Status Updates", key="save_tasks"):
                updated_actions = active.get("actions", [])
                for idx, row in edited.iterrows():
                    if idx < len(updated_actions):
                        updated_actions[idx]["status"] = row.get("status", updated_actions[idx]["status"])
                        updated_actions[idx]["priority"] = row.get("priority", updated_actions[idx]["priority"])
                active["actions"] = updated_actions
                upsert_meeting(active)
                st.success("Task updates saved.")
                st.rerun()
        with risks_tab:
            st.dataframe(risks_to_df(active.get("risks", [])), use_container_width=True, hide_index=True)
        with transcript_tab:
            st.text_area("Transcript", value=active.get("raw_text", ""), height=460)

def memory_page(meetings: List[Dict]) -> None:
    st.markdown("## Persistent Meeting Memory")
    st.caption("Search across all stored meetings and surface evidence from past discussions, decisions, and updates.")
    if not meetings:
        st.info("No meetings available yet.")
        return
    question = st.text_input("Ask across all meetings", placeholder="What changed about launch timing across meetings?")
    filters_col1, filters_col2 = st.columns(2)
    with filters_col1:
        project_filter = st.selectbox("Filter by project", ["All"] + sorted(list({m.get("project", "General") for m in meetings})))
    with filters_col2:
        date_filter = st.selectbox("Sort by", ["Best match", "Newest first"])
    filtered = meetings
    if project_filter != "All":
        filtered = [m for m in meetings if m.get("project") == project_filter]
    if question.strip():
        results = search_across_meetings(question, filtered, top_k=10)
        if date_filter == "Newest first":
            results = sorted(results, key=lambda x: x.get("date", ""), reverse=True)
        st.markdown("### Search Results")
        for item in results:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(f"**{item['meeting_title']}** · {item['date']} · score {item['score']:.4f}")
            st.write(item["text"])
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("### Cross-Meeting Decision Table")
        rows = []
        for meeting in filtered:
            for d in meeting.get("decisions", []):
                rows.append({"Meeting": meeting.get("title"),"Date": meeting.get("date"),"Decision": d.get("decision"),"Status": d.get("status")})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Enter a question to search your meeting memory.")

def ask_ai_page(meetings: List[Dict]) -> None:
    st.markdown("## Ask AI")
    st.caption("Ask questions about one meeting or across the full meeting memory.")
    if not meetings:
        st.info("No meetings stored yet.")
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
                answer = llm_answer(question, context, api_key.strip()) if (use_openai and api_key.strip()) else "Top matching evidence is shown below."
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
                context = "\n\n---\n\n".join([f"{r['meeting_title']} ({r['date']}):\n{r['text']}" for r in results])
                answer = llm_answer(question, context, api_key.strip()) if (use_openai and api_key.strip()) else "Top matching evidence from meeting memory is shown below."
                st.subheader("Answer")
                st.write(answer)
                st.subheader("Evidence")
                for idx, r in enumerate(results, start=1):
                    with st.expander(f"{r['meeting_title']} · score {r['score']:.4f}", expanded=(idx == 1)):
                        st.write(r["text"])

def integrations_page(meetings: List[Dict]) -> None:
    st.markdown("## Integrations & Agent Actions")
    st.caption("Prototype-ready actions that close the loop after meetings.")
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Available Agent Actions")
    st.write("- Sync action items to Jira")
    st.write("- Export decisions to Notion / Confluence")
    st.write("- Send summary to Slack / email")
    st.write("- Create follow-up checklist")
    st.markdown('</div>', unsafe_allow_html=True)
    if not meetings:
        st.info("Save at least one meeting to enable exports.")
        return
    options = {f"{m.get('date')} · {m.get('title')}": m for m in meetings}
    selected_label = st.selectbox("Choose meeting for export", list(options.keys()))
    meeting = options[selected_label]
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Generate Jira-ready CSV", use_container_width=True):
            df = tasks_to_df(meeting.get("actions", []))
            st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), f"{meeting.get('title','meeting').replace(' ','_').lower()}_tasks.csv", "text/csv")
    with col2:
        if st.button("Generate Markdown Summary", use_container_width=True):
            md = [f"# {meeting.get('title')}\n", f"Date: {meeting.get('date')}\n", "## Decisions"]
            for d in meeting.get("decisions", []):
                md.append(f"- {d.get('decision')} ({d.get('status')})")
            md.append("\n## Action Items")
            for a in meeting.get("actions", []):
                md.append(f"- {a.get('task')} | Owner: {a.get('owner')} | Due: {a.get('due_date')} | Status: {a.get('status')}")
            md.append("\n## Risks")
            for r in meeting.get("risks", []):
                md.append(f"- {r.get('risk')} | Severity: {r.get('severity')}")
            st.download_button("Download Markdown", "\n".join(md).encode("utf-8"), f"{meeting.get('title','meeting').replace(' ','_').lower()}_summary.md", "text/markdown")
    with col3:
        if st.button("Preview Slack Message", use_container_width=True):
            st.code(f"""*{meeting.get('title')}* ({meeting.get('date')})
Summary: {meeting.get('overview')}

Decisions:
{chr(10).join('- ' + d.get('decision') for d in meeting.get('decisions', [])[:3])}

Action Items:
{chr(10).join('- ' + a.get('task') + ' (' + a.get('owner') + ')' for a in meeting.get('actions', [])[:3])}
""", language="markdown")

def main() -> None:
    inject_css()
    meetings = load_meetings()
    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio("Go to", ["Dashboard", "Meeting Workspace", "Persistent Memory", "Ask AI", "Integrations"], label_visibility="collapsed")
        st.markdown("---")
        st.caption("v2 feature set")
        st.markdown("- Agentic task tracking")
        st.markdown("- Decision memory")
        st.markdown("- Cross-meeting search")
        st.markdown("- Ready-to-use UI")
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
