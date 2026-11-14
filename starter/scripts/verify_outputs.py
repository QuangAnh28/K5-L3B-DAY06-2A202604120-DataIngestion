"""Check generated outputs without network calls or altering benchmark."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.models import DocumentPage
from src.chunking import regions
from src.evaluation import summarize, evaluate_query
from src.audit_io import load_audits
p=Path(__file__).resolve().parents[1]/'results'
read=lambda n:json.loads((p/n).read_text(encoding='utf-8'))
pages={x['page']:x for x in read('pages.json')}
traces=read('traces_dev.json')+read('traces_test.json')
assert len(traces)==60
key=lambda x:(x['strategy'],x['split'])
assert sorted(summarize(traces),key=key)==sorted(read('metrics.json'),key=key)
assert read('chunks_B.json')==read('chunks_C.json')
for row in traces:
    recomputed=evaluate_query(row['question'],row['hits'])
    assert (recomputed['hit1'],recomputed['hit3'])==(row['hit1'],row['hit3'])
    q=row['question']; assert q['evidence_quote'] in pages[q['gold_page']]['text']
    assert len(row['hits'])==3
    for h in row['hits']:
        page=pages[h['page']]
        assert h['text'] in page['text'] and h['source']==page['metadata']['source']
        parts=regions(DocumentPage(h['document_id'],h['source'],h['page'],page['text'],page['metadata']))
        assert any(h['text'] in part.text and h.get('chapter')==part.metadata.get('chapter') for part in parts)
        if row['applied_filter']: assert all(h[k]==v for k,v in row['applied_filter'].items())
    if row['strategy']=='C' and not q['filter']:
        b=next(x for x in traces if x['strategy']=='B' and x['question']['id']==q['id'])
        assert row['hits']==b['hits']
assert len(read('coherence_audit.json'))==30
assert len(read('grounding_audit.json'))==15
assert len(read('metadata_audit.json'))==45
audits=load_audits(p)
for group in audits.values():
    assert all(x.get('review_status')=='reviewed' and x.get('reviewer_kind') in ('AI','human') for x in group)
for row in audits['metadata']:
    assert type(row['metadata_sufficient_and_correct']) is bool
    assert row['reason']
print('OK: 60 traces, 20 gold evidence, metrics, B=C chunks, source/page/chapter, filters, audit sizes.')
