# Meeting Intelligence Agent

A polished Streamlit application for transforming meeting transcripts into structured decisions, tracked action items, searchable meeting memory, and export-ready follow-up artifacts.

## Key Features

- **Modern Dashboard & Analytics**
  - Real-time metrics (meetings, actions, decisions, risks)
  - Recent meetings timeline
  - Project overview

- **Intelligent Extraction**
  - Smart decision, action item, and risk extraction
  - Multi-level priority inference (ASAP, High, Medium, Low)
  - Owner and due date heuristics
  - Automatic cross-meeting comparison

- **Persistent Meeting Memory**
  - Save unlimited meetings with metadata (type, tags, project)
  - Full-text search using BM25
  - Decision timeline and evolution tracking
  - Filter by project and meeting type

- **Ask & Analyze**
  - Query single or all meetings
  - Optional OpenAI synthesis for contextual answers
  - Evidence-based retrieval with scoring

- **Export & Integration**
  - Jira-ready CSV exports
  - Markdown summaries
  - Slack message previews
  - JSON meeting archives

## Installation & Setup

```bash
# Clone the repository
git clone https://github.com/GauthamiAkula26/agentic-meeting-assistant.git
cd agentic-meeting-assistant

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (macOS / Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Run Locally

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to [Streamlit Cloud](https://share.streamlit.io)
3. Click "New app"
4. Select repository, branch, and `app.py`
5. Click Deploy

For OpenAI features, add `OPENAI_API_KEY` in app secrets.

## Workflow

1. **Meeting Workspace**: Upload or select a sample transcript
2. **Analyze**: Review extracted decisions, actions, and risks
3. **Save**: Store meeting to persistent memory
4. **Search**: Use Persistent Memory to query across all meetings
5. **Export**: Download CSV, Markdown, or JSON for follow-up actions

## File Structure

```
.
├── app.py                    # Main Streamlit app
├── utils/
│   ├── extractors.py        # Decision, action, risk extraction
│   ├── formatting.py        # DataFrame formatters
│   ├── llm.py               # OpenAI integration
│   ├── nlp.py               # BM25 search and chunking
│   └── storage.py           # JSON persistence
├── data/sample_meetings/    # Sample transcripts
├── storage/                 # Meeting database
├── requirements.txt         # Python dependencies
└── README.md
```

## Technologies

- **Streamlit**: Interactive UI
- **rank-bm25**: Lightweight full-text search
- **OpenAI**: Optional LLM synthesis
- **Pandas**: Data handling
- **Python 3.10+**: Core language

## License

MIT
