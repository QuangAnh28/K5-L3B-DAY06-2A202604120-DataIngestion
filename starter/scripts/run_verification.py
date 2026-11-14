"""Run the offline checks and retain exact outputs with timestamps."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--source',action='store_true',help='Re-extract PDF and replay all searches using the local cache/DB')
args=parser.parse_args()
scripts=['test_contracts.py','test_review_and_logging.py','verify_outputs.py']
if args.source:scripts.append('review_source_checks.py')
rows=[]
for name in scripts:
    print('Checking '+name,flush=True)
    result=subprocess.run([sys.executable,str(ROOT/'starter/scripts'/name)],cwd=ROOT,
                           capture_output=True,text=True,encoding='utf-8',errors='replace')
    output=result.stdout+result.stderr
    print(output,flush=True)
    rows.append(dict(script=name,exit_code=result.returncode,output=output))
    if result.returncode:break
out=ROOT/'starter/results'
audits=['coherence_audit.json','grounding_audit.json','metadata_audit.json']
summary=dict(timestamp=datetime.now(timezone.utc).isoformat(),passed=len(rows)==len(scripts) and all(r['exit_code']==0 for r in rows),
             api_requests=0,unit_tests=sum(int(n) for r in rows for n in re.findall(r'Ran (\d+) tests?',r['output'])),
             checks=rows,source_check_executed=args.source,
             review_sha256={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in audits})
(out/'verification_results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
sys.exit(0 if summary['passed'] else 1)
