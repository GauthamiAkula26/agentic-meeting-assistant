# Meeting Intelligence Agent v2

A polished, ready-to-use Streamlit application for turning meeting transcripts into structured decisions, tracked action items, searchable meeting memory, and exportable follow-ups.

## What this version includes

- **Production-style UI**
  - sidebar navigation
  - dashboard metrics
  - structured workspace
  - memory search page
  - integrations page
- **Agentic task and decision tracking**
  - action item extraction
  - owners
  - due date heuristics
  - task status editing
- **Persistent meeting memory**
  - save multiple meetings
  - search across meetings
  - compare decision changes over time
- **Integrations-ready exports**
  - Jira-ready CSV
  - markdown summary export
  - Slack message preview
- **Optional OpenAI mode**
  - synthesized answers from transcript evidence

## Why this deploys well

This repo uses lightweight BM25 transcript retrieval instead of heavy embedding libraries, so it is much faster to deploy on Streamlit Community Cloud.

## Run locally

```bash
python -m venv .venv
```

### Windows PowerShell
```bash
.venv\Scripts\Activate.ps1
```

### macOS / Linux
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Demo flow

1. Open **Meeting Workspace**
2. Use `Launch Readiness Review`
3. Click **Process and Save Meeting**
4. Save the second sample meeting too
5. Open **Persistent Memory**
6. Ask:
   - `What changed about launch timing?`
   - `Which decisions were updated later?`
   - `What blockers still remain?`
