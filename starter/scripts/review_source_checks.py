"""Rebuild corpus/chunks and replay persisted search offline, without overwriting traces."""
import hashlib
import json
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ingestion import load_pdf
from src.chunking import regions, fixed_size, by_paragraph
from src.store import VectorStore

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'starter/results'
read=lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
pdf=ROOT/manifest['local_path']
assert hashlib.sha256(pdf.read_bytes()).hexdigest()==manifest['sha256']
pages=load_pdf(pdf,manifest['source_id'],manifest['source_path_or_url'])
saved=read('pages.json')
assert len(pages)==len(saved)==84
assert all(a.text==b['text'] and a.metadata==b['metadata'] for a,b in zip(pages,saved))
assert len(set(manifest['counted_pages']))>=30
for s in 'ABC':
    chunks=[]
    for page in pages:
        if page.page not in manifest['counted_pages']: continue
        assert len(page.text)>100
        for part in regions(page):
            chunks.extend(fixed_size(part,800,100) if s=='A' else by_paragraph(part,1000))
    assert [vars(c) for c in chunks]==read('chunks_'+s+'.json')
    for c in chunks:
        assert isinstance(c.source,str) and isinstance(c.document_id,str) and type(c.page) is int
        assert type(c.metadata['year']) is int
        assert all(isinstance(c.metadata[k],str) for k in ['chapter','section','article'] if k in c.metadata)

count=0
cachepath=OUT/'embedding_cache.json'
assert cachepath.exists(), 'First run the pipeline to populate the local vector cache (this check itself makes no API calls)'
cache=read('embedding_cache.json')
store=VectorStore(OUT/'qdrant')
try:
    for s in 'ABC': assert store.count(s)==len(read('chunks_'+s+'.json'))
    for row in read('traces_dev.json')+read('traces_test.json'):
        key=hashlib.sha256(('openai/text-embedding-3-small|1536|'+row['question']['question']).encode()).hexdigest()
        hits=store.search(row['strategy'],cache[key],filters=row['applied_filter'])
        assert [h['chunk_id'] for h in hits]==[h['chunk_id'] for h in row['hits']]
        assert all(abs(a['score']-b['score'])<1e-6 for a,b in zip(hits,row['hits']))
        count+=1
finally:
    store.close()

secret_matches=[]
for path in ROOT.rglob('*'):
    if not path.is_file() or any(part in path.parts for part in ['.git','.venv','qdrant','tmp']) or path.name=='.env': continue
    if path.suffix not in ['.py','.json','.jsonl','.md','.csv','.txt','.yml']: continue
    if re.search(r'sk-or-v1-[A-Za-z0-9]{20,}',path.read_text(encoding='utf-8',errors='replace')):
        secret_matches.append(str(path.relative_to(ROOT)))
assert not secret_matches,secret_matches
summary=dict(timestamp=datetime.now(timezone.utc).isoformat(),pdf_pages=84,content_pages=len(manifest['counted_pages']),
    reconstructed_chunks={s:len(read('chunks_'+s+'.json')) for s in 'ABC'},replayed_queries=count,
    source_text_matches=True,source_sha256_matches=True,submission_secret_scan_passed=True,api_requests=0)
(OUT/'source_verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
