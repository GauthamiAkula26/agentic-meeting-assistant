from __future__ import annotations
import re
from typing import Dict, List
from rank_bm25 import BM25Okapi

def tokenize(text: str) -> List[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [tok for tok in cleaned.split() if tok.strip()]

def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> List[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 <= chunk_size:
            current += ("\n" if current else "") + para
        else:
            if current:
                chunks.append(current)
            if len(para) <= chunk_size:
                current = para
            else:
                start = 0
                while start < len(para):
                    end = min(start + chunk_size, len(para))
                    piece = para[start:end]
                    chunks.append(piece)
                    start = max(end - overlap, start + 1)
                current = ""
    if current:
        chunks.append(current)
    return chunks

def search_chunks(question: str, chunks: List[str], top_k: int = 5) -> List[Dict]:
    if not chunks:
        return []
    tokenized_chunks = [tokenize(chunk) for chunk in chunks]
    bm25 = BM25Okapi(tokenized_chunks)
    scores = bm25.get_scores(tokenize(question))
    ranked = sorted(
        [{"text": chunks[i], "score": float(scores[i]), "chunk_index": i} for i in range(len(chunks))],
        key=lambda x: x["score"],
        reverse=True,
    )
    return ranked[:top_k]

def search_across_meetings(question: str, meetings: List[Dict], top_k: int = 8) -> List[Dict]:
    records: List[Dict] = []
    corpus: List[List[str]] = []
    for meeting in meetings:
        for idx, chunk in enumerate(meeting.get("chunks", [])):
            records.append({
                "meeting_id": meeting.get("meeting_id"),
                "meeting_title": meeting.get("title"),
                "date": meeting.get("date"),
                "chunk_index": idx,
                "text": chunk,
            })
            corpus.append(tokenize(chunk))
    if not corpus:
        return []
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(question))
    ranked = sorted(
        [{**records[i], "score": float(scores[i])} for i in range(len(records))],
        key=lambda x: x["score"],
        reverse=True,
    )
    return ranked[:top_k]
