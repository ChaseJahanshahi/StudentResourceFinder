"""Summarize anonymous runtime metrics without exposing profiles or keys."""
import json
from pathlib import Path
from statistics import median

path=Path(__file__).parent/'.runtime'/'metrics.jsonl'
rows=[]
if path.exists():
    for line in path.read_text(encoding='utf-8').splitlines():
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: pass
successful=[row for row in rows if row.get('success')]
report=dict(requests=len(rows),successful=len(successful),failures=len(rows)-len(successful),
            median_seconds=median([r['seconds'] for r in successful]) if successful else None,
            tokens=sum(r.get('total_tokens') or 0 for r in rows),
            tavily_reported_credits=sum(r.get('tavily_credits') or 0 for r in rows),
            estimated_nebius_usd=sum(r.get('estimated_nebius_usd') or 0 for r in rows) if any(r.get('estimated_nebius_usd') is not None for r in rows) else None,
            note='Dollar estimates use configured rates or a fresh exact-model catalog snapshot; source truth needs human review.')
print(json.dumps(report,indent=2))
