"""Evaluate retrieved evidence and preserve per-query traces."""
import re
from typing import Any


def _normalize_match_str(text: str) -> str:
    """Normalize string for robust evidence match (ignores case, spaces, and punctuation)."""
    return re.sub(r"[^a-zA-Z0-9]", "", text).lower()


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and gold evidence match; record Hit@1 and Evidence Hit@3 trace."""
    gold_page = question.get("gold_page")
    evidence_quote = question.get("evidence_quote", "")
    norm_evidence = _normalize_match_str(evidence_quote)

    detailed_hits = []
    hit_at_1 = False
    hit_at_3 = False

    for rank, hit in enumerate(hits, start=1):
        hit_page = hit.get("page")
        hit_text = hit.get("text", "")
        norm_hit_text = _normalize_match_str(hit_text)

        # Check page and evidence substring presence
        page_match = (hit_page == gold_page)
        evidence_match = (norm_evidence in norm_hit_text) if norm_evidence else True
        is_hit = page_match and evidence_match

        if rank == 1 and is_hit:
            hit_at_1 = True
        if is_hit:
            hit_at_3 = True

        detailed_hits.append(
            {
                "rank": rank,
                "chunk_id": hit.get("chunk_id"),
                "page": hit_page,
                "section": hit.get("section"),
                "score": round(hit.get("score", 0.0), 4),
                "page_match": page_match,
                "evidence_match": evidence_match,
                "is_hit": is_hit,
                "text_snippet": (hit_text[:120] + "...") if len(hit_text) > 120 else hit_text,
            }
        )

    return {
        "question_id": question.get("id"),
        "split": question.get("split"),
        "question": question.get("question"),
        "expected_answer": question.get("expected_answer"),
        "gold_page": gold_page,
        "evidence_quote": evidence_quote,
        "filter": question.get("filter"),
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hits": detailed_hits,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by dev, test, and overall splits."""
    splits = ["dev", "test", "all"]
    summary: dict[str, Any] = {}

    for s in splits:
        subset = traces if s == "all" else [t for t in traces if t.get("split") == s]
        total = len(subset)
        if total == 0:
            summary[s] = {
                "total": 0,
                "hit1_count": 0,
                "hit3_count": 0,
                "hit1_rate": "0/0 (N/A)",
                "hit3_rate": "0/0 (N/A)",
                "hit1_pct": 0.0,
                "hit3_pct": 0.0,
            }
            continue

        hit1_count = sum(1 for t in subset if t.get("hit_at_1"))
        hit3_count = sum(1 for t in subset if t.get("hit_at_3"))

        summary[s] = {
            "total": total,
            "hit1_count": hit1_count,
            "hit3_count": hit3_count,
            "hit1_rate": f"{hit1_count}/{total}",
            "hit3_rate": f"{hit3_count}/{total}",
            "hit1_pct": round(hit1_count / total * 100, 1),
            "hit3_pct": round(hit3_count / total * 100, 1),
        }

    return summary
