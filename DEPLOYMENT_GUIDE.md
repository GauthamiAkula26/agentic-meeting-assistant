# Meeting Intelligence Agent - Deployment Guide

## GitHub Setup & Deployment

### Step 1: Initialize Git Repository

```bash
cd C:\Users\gauth\Downloads\meeting-intelligence-agent-v2

# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Meeting Intelligence Agent with improved UI and features"

# Add remote (replace with your repo)
git remote add origin https://github.com/YOUR_USERNAME/agentic-meeting-assistant.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign up with GitHub
3. Click "New app"
4. Select:
   - Repository: `YOUR_USERNAME/agentic-meeting-assistant`
   - Branch: `main`
   - App path: `app.py`
5. Click "Deploy"

### Step 3: Add OpenAI Support (Optional)

In Streamlit Cloud:
1. Go to app settings (gear icon)
2. Click "Secrets"
3. Add:
```toml
OPENAI_API_KEY = "your-api-key-here"
```

## Environment Variables

Create `.env` file locally:
```
OPENAI_API_KEY=sk-xxx...
```

## Project Structure

```
meeting-intelligence-agent-v2/
├── app.py                 # Main Streamlit application (480 lines)
├── utils/
│   ├── extractors.py     # AI extraction logic (improved)
│   ├── formatting.py     # DataFrame helpers
│   ├── llm.py            # OpenAI integration
│   ├── nlp.py            # BM25 search
│   └── storage.py        # JSON database
├── data/
│   └── sample_meetings/  # Sample transcripts
├── storage/
│   └── meetings_db.json  # Persistent meeting storage
├── .env                  # Environment variables
├── .gitignore            # Git ignore rules
├── requirements.txt      # Python dependencies
├── runtime.txt           # Python version
└── README.md            # Documentation
```

## Key Improvements in This Version

### Backend Enhancements
✅ Better action item extraction with multi-level priority (ASAP, High, Medium, Low)
✅ Extended owner hints (16+ team roles)
✅ Improved due date detection (today, tomorrow, end of day, EOD, etc.)
✅ New patterns for decision extraction ("we will", "it was decided that")
✅ Risk severity inference with "Problem" pattern support

### UI/UX Improvements
✅ Modern dashboard with metrics cards (gradient background)
✅ Enhanced meeting workspace with preview-and-save workflow
✅ Extraction preview tabs (decisions, actions, risks)
✅ Better visual hierarchy with pills and action cards
✅ Improved navigation with feature descriptions
✅ Decision timeline table with related meetings tracking
✅ Better expander organization and colors

### Feature Additions
✅ Meeting metadata (type: Planning/Review/Standup/Retrospective/Stakeholder/Workshop)
✅ Tags support for meetings
✅ Project and meeting type filtering in memory search
✅ Enhanced search with BM25 ranking
✅ Related meetings tracking for decisions
✅ Decision status enrichment (Active/Possibly superseded)
✅ Priority inference for action items
✅ Export improvements (CSV, Markdown, JSON formatting)

## Running Tests

```bash
# Test extraction
python -c "from utils.extractors import extract_decisions; print(extract_decisions('Decision: We will launch next week'))"

# Test locally
streamlit run app.py

# Test in browser
# Visit http://localhost:8501
```

## Sample Meeting Format

Transcripts should contain lines like:

```text
Decision: We will launch by end of month
Action item: John will prepare marketing materials by Friday
Risk: Budget approval is still pending
Blocker: Database migration is critical and unstable
```

## Troubleshooting

**Issue**: "ModuleNotFoundError"
- Solution: `pip install -r requirements.txt`

**Issue**: "Connection refused on localhost:8501"
- Solution: Check port 8501 is available or use `streamlit run app.py --server.port 8502`

**Issue**: "OPENAI_API_KEY not found"
- Solution: Add to `.env` or Streamlit secrets

## Production Considerations

- Database: Currently JSON file (upgrade to PostgreSQL/Firebase for production)
- Search: BM25 with in-memory indexing (upgrade to Elasticsearch for large scale)
- Authentication: None (add with Streamlit authentication)
- Rate limiting: None (add with middleware)
- Logging: Basic (add structured logging with Python logging)

## Next Steps

1. Customize sample meetings in `data/sample_meetings/`
2. Add team-specific owner names to `OWNER_HINTS` in `extractors.py`
3. Deploy to Streamlit Cloud
4. Gather user feedback and iterate
5. Integrate with actual tools (Jira, Slack, Notion)

---

**Built with:** Streamlit + OpenAI + BM25
**Python:** 3.10+
**License:** MIT
