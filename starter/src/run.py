"""Run the frozen corpus experiment, with explicit dev/test stages."""
from .event_log import logged


@logged('pipeline.run')
def main() -> None:
    """Pipeline:

    1. Load the corpus and benchmark; validate at least 30 content pages.
    2. Build strategies A (fixed), B (paragraph) and C (B + metadata filter).
    3. Embed with the same model and store vectors/metadata per strategy.
    4. Run the same dev/test questions and save full top-3 traces.
    5. Report retrieval metrics and prepare samples for manual assessment.

    Follow the five dimensions in ../../BENCHMARK.md.
    """
    import argparse, json, time, hashlib, statistics, os
    from pathlib import Path
    from datetime import datetime, timezone
    from dotenv import load_dotenv
    from .models import DocumentPage
    from .chunking import fixed_size, by_paragraph, regions
    from .embeddings import MyEmbedder
    from .store import VectorStore
    from .evaluation import evaluate_query, summarize
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['dev','test'], default='dev')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'starter/results'
    load_dotenv(root/'starter/.env')
    def save(name, value):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    raw = json.loads((out/'pages.json').read_text(encoding='utf-8'))
    manifest = json.loads((root/'data/manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['counted_pages'])>=30
    pages = [DocumentPage(manifest['source_id'],manifest['source_path_or_url'],p['page'],p['text'],p['metadata']) for p in raw if p['page'] in manifest['counted_pages']]
    questions = json.loads((root/'benchmark/questions.json').read_text(encoding='utf-8'))
    assert sum(q['split']=='dev' for q in questions)>=15 and sum(q['split']=='test' for q in questions)>=5
    assert sum(bool(q['filter']) for q in questions)>=3
    for q in questions:
        assert q['evidence_quote'] in raw[q['gold_page']-1]['text'], q['id']
    if args.split=='test' and not (out/'selection.json').exists():
        raise RuntimeError('Freeze dev selection before test')
    embedder = MyEmbedder(os.getenv('EMBEDDING_MODEL','openai/text-embedding-3-small'))
    ledger = out/('api_usage_'+args.split+'.json')
    if ledger.exists():
        embedder.usage = json.loads(ledger.read_text(encoding='utf-8'))
    cachepath = out/'embedding_cache.json'
    cache = json.loads(cachepath.read_text()) if cachepath.exists() else {}
    def embed(texts):
        keys = [hashlib.sha256((embedder.model_name+'|1536|'+t).encode()).hexdigest() for t in texts]
        missing = dict((k,t) for k,t in zip(keys,texts) if k not in cache)
        ks = list(missing)
        for start in range(0,len(ks),64):
            batch=ks[start:start+64]
            vectors=embedder.embed_documents([missing[k] for k in batch])
            cache.update(zip(batch,vectors))
            cachepath.write_text(json.dumps(cache),encoding='utf-8')
            save('api_usage_'+args.split+'.json',embedder.usage)
            print('Embedded',min(start+64,len(ks)),'/',len(ks),flush=True)
        return [cache[k] for k in keys]
    dbpath=out/'qdrant'
    store=VectorStore(dbpath)
    stats=[]
    for strategy in 'ABC':
        started=time.perf_counter()
        chunks=[]
        for page in pages:
            for part in regions(page):
                chunks.extend(fixed_size(part,800,100) if strategy=='A' else by_paragraph(part,1000))
        assert len({c.chunk_id for c in chunks})==len(chunks)
        vectors=embed([c.text for c in chunks])
        store.upsert(strategy,chunks,vectors)
        count1=store.count(strategy)
        store.upsert(strategy,chunks,vectors)
        assert store.count(strategy)==count1==len(chunks)
        save('chunks_'+strategy+'.json',[vars(c) for c in chunks])
        lengths=[len(c.text) for c in chunks]
        stats.append(dict(strategy=strategy,chunks=len(chunks),characters=sum(lengths),
           length_min=min(lengths),length_median=statistics.median(lengths),length_max=max(lengths),
           ingest_seconds=time.perf_counter()-started,reingest_count=count1,
           note='B/C reuse cached embeddings; time includes two snapshot writes; warm runs reuse all vectors'))
    store.close()
    store=VectorStore(dbpath)
    traces=[]
    for q in questions:
        if q['split']!=args.split: continue
        vector=embed([q['question']])[0]
        for strategy in 'ABC':
            hits=store.search(strategy,vector,filters=q['filter'] if strategy=='C' else None)
            row=evaluate_query(q,hits)
            row.update(strategy=strategy,applied_filter=q['filter'] if strategy=='C' else {})
            traces.append(row)
    store.close()
    save('traces_'+args.split+'.json',traces)
    save('metrics_'+args.split+'.json',[m for m in summarize(traces) if m['n']])
    save('resources_'+args.split+'.json',stats)
    save('run_'+args.split+'.json',dict(timestamp=datetime.now(timezone.utc).isoformat(),model=embedder.model_name,
       dimensions=1536,metric='cosine',search='exact',store='Qdrant local persistent',reopen_verified=True,
       benchmark_sha256=hashlib.sha256((root/'benchmark/questions.json').read_bytes()).hexdigest(),
       usage=embedder.usage))
    print(json.dumps([m for m in summarize(traces) if m['n']],ensure_ascii=False),flush=True)


if __name__ == "__main__":
    main()
