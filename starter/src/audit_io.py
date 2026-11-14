"""Validate review records without regenerating or overwriting reviewer edits."""
import hashlib
import json
from pathlib import Path


def load_audits(folder):
    folder = Path(folder)
    read = lambda name: json.loads((folder / name).read_text(encoding='utf-8'))
    for name, digest in read('audit_review_reference.json').items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Audit input changed; re-review required: ' + name)
    traces = read('traces_test.json')
    chunks = {s: {c['chunk_id']: c for c in read('chunks_' + s + '.json')} for s in 'ABC'}
    coherence = read('coherence_audit.json')
    grounding = read('grounding_audit.json')
    metadata = read('metadata_audit.json')
    expected_meta = {(r['strategy'], r['question']['id'], i, h['chunk_id'])
                     for r in traces for i, h in enumerate(r['hits'], 1)}
    expected_ground = {(r['strategy'], r['question']['id']) for r in traces}
    expected_coherence = {(s, x['page'], x['chunk']['chunk_id'])
                          for s in 'ABC' for x in read('coherence_samples.json')
                          if x['strategy'] == ('B' if s == 'C' else s)}
    def require_keys(rows, expected, fields):
        keys = [tuple(row[k] for k in fields) for row in rows]
        if len(keys) != len(set(keys)) or set(keys) != expected:
            raise ValueError('Incomplete, duplicate or stale audit records: ' + ','.join(fields))
    require_keys(coherence, expected_coherence, ('strategy', 'page', 'chunk_id'))
    require_keys(grounding, expected_ground, ('strategy', 'question_id'))
    require_keys(metadata, expected_meta, ('strategy', 'question_id', 'rank', 'chunk_id'))
    for row in coherence + grounding:
        if type(row.get('score')) is not int or row['score'] not in (0, 1, 2) or not row.get('reason'):
            raise ValueError('Score 0/1/2 and a reason are required')
    for row in metadata:
        if type(row.get('metadata_sufficient_and_correct')) is not bool or not row.get('reason'):
            raise ValueError('Metadata review requires a Boolean decision and reason')
    for row in coherence + grounding + metadata:
        if row.get('student_confirmed') is True and not row.get('confirmed_by'):
            raise ValueError('A student confirmation requires confirmed_by')
        if row.get('review_status') == 'reviewed':
            if not row.get('reviewed_at') or row.get('reviewer_kind') not in ('AI', 'human'):
                raise ValueError('Reviewed records require timestamp and reviewer kind')
    for row in coherence:
        if row['page'] != chunks[row['strategy']][row['chunk_id']]['page']:
            raise ValueError('Coherence page mismatch')
    for row in grounding:
        trace = next(r for r in traces if r['strategy'] == row['strategy'] and r['question']['id'] == row['question_id'])
        if row['chunk_ids'] != [h['chunk_id'] for h in trace['hits']]:
            raise ValueError('Grounding evidence mismatch')
    return dict(coherence=coherence, grounding=grounding, metadata=metadata)
