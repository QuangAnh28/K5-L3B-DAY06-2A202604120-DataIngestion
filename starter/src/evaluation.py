"""Evaluate evidence containment and preserve per-query traces."""
from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and complete gold quote; preserve hit@1/hit@3 trace.

    Accept any documented alternative gold evidence. Do not infer human grounding
    or chunk coherence labels from exact string match.
    """
    import re
    def norm(s):
        return re.sub(r'\s+', ' ', s).strip()
    golds = question.get('alternative_gold', []) + [dict(source_id=question['gold_source_id'], page=question['gold_page'], evidence=question['evidence_quote'])]
    correct = [any(h['document_id'] == g['source_id'] and h['page'] == g['page'] and norm(g['evidence']) in norm(h['text']) for g in golds) for h in hits]
    return dict(question=question, hits=hits, hit1=bool(correct and correct[0]), hit3=any(correct))


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and split."""
    result = []
    for strategy in 'ABC':
        for split in ('dev', 'test'):
            rows = [r for r in traces if r['strategy'] == strategy and r['question']['split'] == split]
            result.append(dict(strategy=strategy, split=split, n=len(rows), hit1=sum(r['hit1'] for r in rows), hit3=sum(r['hit3'] for r in rows)))
    return result
