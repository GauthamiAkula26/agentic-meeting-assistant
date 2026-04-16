from __future__ import annotations
import re
from typing import Dict, List, Optional

OWNER_HINTS = [
    "Anita", "Ravi", "Maya", "Karan", "John", "Sarah", "Mike", "Priya", "Alex",
    "Team", "Engineering", "Design", "Support", "Legal", "Product", "Marketing"
]

DUE_DATE_REGEX = r"(?i)\b(by\s+[A-Z][a-z]+|before\s+[A-Z][a-z]+|next\s+[A-Z][a-z]+|tomorrow|today|this\s+week|next\s+week|end of day|eod|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b"
PRIORITY_REGEX = r"(?i)\b(asap|urgent|immediately|critical|high priority|must|must be|today|tomorrow|end of day|eod)\b"


def _clean_line(line: str) -> str:
    return line.strip(" -•\t").strip()


def _find_owner(text: str) -> Optional[str]:
    for owner in OWNER_HINTS:
        if re.search(rf"\b{re.escape(owner)}\b", text, flags=re.IGNORECASE):
            return owner
    m = re.match(r"^([A-Za-z][A-Za-z\- ]+):", text)
    if m:
        return m.group(1).strip()
    return None


def _find_due_date(text: str) -> Optional[str]:
    m = re.search(DUE_DATE_REGEX, text)
    return m.group(0) if m else None


def _infer_priority(text: str) -> str:
    if re.search(PRIORITY_REGEX, text):
        return "High"
    if re.search(r"(?i)\b(should|important|review|follow up|due soon|priority)\b", text):
        return "Medium"
    return "Low"


def _dedupe_dicts(items: List[Dict], key: str) -> List[Dict]:
    seen = set()
    result = []
    for item in items:
        value = item.get(key, "").strip().lower()
        if value and value not in seen:
            seen.add(value)
            result.append(item)
    return result


def extract_decisions(text: str) -> List[Dict]:
    patterns = [
        r"(?i)\bdecision[:\-]\s*(.+)",
        r"(?i)\bdecided to\s+(.+?)(?:\.|$)",
        r"(?i)\bagreed to\s+(.+?)(?:\.|$)",
        r"(?i)\bit was decided that\s+(.+?)(?:\.|$)",
        r"(?i)\bwe will\s+(.+?)(?:\.|$)",
    ]
    items: List[Dict] = []
    for line in text.splitlines():
        line = _clean_line(line)
        if not line:
            continue
        for pattern in patterns:
            m = re.search(pattern, line)
            if m:
                items.append({
                    "decision": m.group(1).strip(" .:-"),
                    "speaker": _find_owner(line),
                    "status": "Active",
                    "source": line,
                })
                break
    return _dedupe_dicts(items, "decision")


def extract_action_items(text: str) -> List[Dict]:
    patterns = [
        r"(?i)\baction item[:\-]\s*(.+)",
        r"(?i)\bnext step[:\-]\s*(.+)",
        r"(?i)\bto do[:\-]\s*(.+)",
        r"(?i)\btask[:\-]\s*(.+)",
        r"(?i)\b([A-Z][a-z]+)\s+will\s+(.+?)(?:\.|$)",
        r"(?i)\bneeds to\s+(.+?)(?:\.|$)",
        r"(?i)\bplease\s+(?:follow up|review|share|confirm)\s+(.+?)(?:\.|$)",
    ]
    items: List[Dict] = []
    for line in text.splitlines():
        line = _clean_line(line)
        if not line:
            continue
        for pattern in patterns:
            m = re.search(pattern, line)
            if not m:
                continue
            if pattern == r"(?i)\b([A-Z][a-z]+)\s+will\s+(.+?)(?:\.|$)":
                owner = m.group(1)
                task = m.group(2).strip(" .:-")
            else:
                task = m.group(1).strip(" .:-")
                owner = _find_owner(line)
            items.append({
                "task": task,
                "owner": owner or "Unassigned",
                "due_date": _find_due_date(line) or "Not specified",
                "priority": _infer_priority(line),
                "status": "Open",
                "source": line,
            })
            break
    return _dedupe_dicts(items, "task")


def extract_risks(text: str) -> List[Dict]:
    patterns = [
        r"(?i)\brisk[:\-]\s*(.+)",
        r"(?i)\blocker[:\-]\s*(.+)",
        r"(?i)\bissue[:\-]\s*(.+)",
        r"(?i)\bconcern[:\-]\s*(.+)",
        r"(?i)\bdependency[:\-]\s*(.+)",
        r"(?i)\bproblem[:\-]\s*(.+)",
    ]
    items: List[Dict] = []
    for line in text.splitlines():
        line = _clean_line(line)
        if not line:
            continue
        for pattern in patterns:
            m = re.search(pattern, line)
            if m:
                severity = "High" if re.search(r"(?i)blocker|critical|unstable|delay", line) else "Medium"
                items.append({
                    "risk": m.group(1).strip(" .:-"),
                    "severity": severity,
                    "source": line,
                })
                break
    return _dedupe_dicts(items, "risk")


def build_overview_summary(text: str, decisions: List[Dict], actions: List[Dict], risks: List[Dict]) -> str:
    parts = [
        f"Processed {len(text.split())} words into structured meeting memory.",
        f"Found {len(decisions)} decisions, {len(actions)} action items, and {len(risks)} risks.",
    ]
    if decisions:
        parts.append(f"Top decision: {decisions[0]['decision']}")
    if actions:
        parts.append(f"Top task: {actions[0]['task']} ({actions[0]['owner']})")
    if risks:
        parts.append(f"Key risk: {risks[0]['risk']}")
    parts.append("Review and update before saving to memory.")
    return " ".join(parts)


def enrich_decision_statuses(current_meeting: Dict, prior_meetings: List[Dict]) -> List[Dict]:
    decisions = current_meeting.get("decisions", [])
    prior_decisions = []
    for meeting in prior_meetings:
        for d in meeting.get("decisions", []):
            prior_decisions.append((meeting.get("title"), d.get("decision", "")))
    
    keywords_to_latest = {}
    for idx, decision in enumerate(decisions):
        tokens = [tok.lower() for tok in re.findall(r"[A-Za-z]+", decision.get("decision", "")) if len(tok) > 4]
        for tok in tokens[:4]:
            keywords_to_latest[tok] = idx
    
    for idx, decision in enumerate(decisions):
        tokens = [tok.lower() for tok in re.findall(r"[A-Za-z]+", decision.get("decision", "")) if len(tok) > 4]
        superseded = False
        for tok in tokens[:4]:
            latest_idx = keywords_to_latest.get(tok)
            if latest_idx is not None and latest_idx != idx:
                superseded = True
        
        decision["status"] = "Possibly superseded" if superseded else decision.get("status", "Active")
        
        related_prior = []
        for title, prior_decision in prior_decisions:
            for tok in tokens[:3]:
                if tok and tok in prior_decision.lower():
                    related_prior.append(title)
                    break
        if related_prior:
            decision["related_meetings"] = list(dict.fromkeys(related_prior))
    
    return decisions
