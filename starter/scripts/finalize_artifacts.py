"""Summarize measured outputs and serialize Codex's disclosed semantic review."""
import argparse,json,csv,sys,statistics,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--results-dir', type=Path, default=ROOT/'starter/results')
parser.add_argument('--experiment-log', type=Path, default=ROOT/'artifacts/experiment_log.csv')
args = parser.parse_args()
OUT=args.results_dir
def read(name): return json.loads((OUT/name).read_text(encoding='utf-8'))
def save(name,data): (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

sys.path.insert(0, str(ROOT/'starter'))
from src.audit_io import load_audits
reviews = load_audits(OUT)  # Input-only: reviewer scores, notes and confirmations are never rewritten.
traces=read('traces_test.json')
pages={p['page']:p for p in read('pages.json')}
metadata_checks=[]
for row in traces:
    for rank,h in enumerate(row['hits'],1):
        page=pages[h['page']]
        ok=(h['source']==page['metadata']['source'] and h['document_id']==page['metadata']['document_id']
            and h['text'] in page['text'])
        metadata_checks.append(dict(strategy=row['strategy'],question_id=row['question']['id'],rank=rank,
                                    chunk_id=h['chunk_id'],structural_valid=ok))
save('metadata_checks.json',metadata_checks)
filter_rows=[]
for row in read('traces_dev.json')+traces:
    q=row['question']
    if not q['filter']: continue
    filter_rows.append(dict(strategy=row['strategy'],split=q['split'],question_id=q['id'],
       requested_filter=q['filter'],applied_filter=row['applied_filter'],
       compliant=len(row['hits'])==3 and all(all(h[k]==v for k,v in q['filter'].items()) for h in row['hits'])))
save('filter_audit.json',filter_rows)
metrics=read('metrics_dev.json')+read('metrics_test.json')
save('metrics.json',metrics)
usage=read('api_usage_dev.json')+read('api_usage_test.json')
save('cost_summary.json',dict(requests=len(usage),prompt_tokens=sum(x['usage'].get('prompt_tokens',0) for x in usage),
       cost_usd=sum(x['usage'].get('cost',0) for x in usage),method='Sum provider usage.cost for recorded successful requests; shared cache across strategies'))
args.experiment_log.parent.mkdir(parents=True, exist_ok=True)
with args.experiment_log.open('w',encoding='utf-8',newline='') as f:
    fields=['strategy','chunking','chunk_size','overlap','metadata','filter','vectorizer','hypothesis','dev_hit1','dev_hit3','test_hit1','test_hit3','notes']
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for s in 'ABC':
        dev=next(m for m in metrics if m['strategy']==s and m['split']=='dev');test=next(m for m in metrics if m['strategy']==s and m['split']=='test')
        reviewed_rows=[r for group in reviews.values() for r in group if r['strategy']==s]
        confirmed=sum(bool(r.get('student_confirmed')) for r in reviewed_rows)
        w.writerow(dict(strategy=s,chunking='fixed' if s=='A' else 'paragraph',chunk_size=800 if s=='A' else 1000,
           overlap=100 if s=='A' else 0,metadata='document_id/source/page/chapter/year',filter='chapter when supplied' if s=='C' else 'none',
           vectorizer='openai/text-embedding-3-small',hypothesis={'A':'Baseline','B':'Paragraph boundaries may preserve evidence','C':'Chapter filter may reduce out-of-scope results'}[s],
           dev_hit1=f"{dev['hit1']}/{dev['n']}",dev_hit3=f"{dev['hit3']}/{dev['n']}",test_hit1=f"{test['hit1']}/{test['n']}",test_hit3=f"{test['hit3']}/{test['n']}",notes=f'Actual run; AI-assisted audit; student confirmed {confirmed}/{len(reviewed_rows)} records'))
save('processing_log.json',dict(empty_pages=[],excluded=[dict(page=84,reason='13 characters, signer name only')],
        known_issues=['pypdf extraction inserts whitespace inside Vietnamese words; retained without guessing',
                      'Chapter boundaries shared by all strategies; page boundaries may cut clauses',
                      'Qdrant local ResourceWarning on Python 3.14 in unit tests; assertions and reopen passed']))
print(read('cost_summary.json'))
