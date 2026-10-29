"""Durable request ceilings and aggregate telemetry. Never stores student answers or keys."""
import json
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import time

class UsageLimit(Exception):
    pass

def _number(settings, name, default):
    try:
        return max(1, int(os.environ.get(name) or settings.get(name, default)))
    except (ValueError, TypeError):
        return default

def reserve_generation(session_id, settings=None, db_path=None, now=None):
    settings = settings or {}
    now = time.time() if now is None else now
    path = Path(db_path or os.environ.get('SRF_USAGE_DB', Path(__file__).parent / '.runtime' / 'usage.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(path, timeout=10)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS requests (session TEXT NOT NULL, created REAL NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM requests WHERE created < ?', (now-86400,))
            global_count = db.execute('SELECT count(*) FROM requests').fetchone()[0]
            session_count, latest = db.execute('SELECT count(*), max(created) FROM requests WHERE session=? AND created>?', (session_id, now-3600)).fetchone()
            if global_count >= _number(settings, 'SRF_GLOBAL_DAILY_LIMIT', 60):
                raise UsageLimit('The demo has reached its daily request budget. Please try again tomorrow; your current results remain available.')
            if session_count >= _number(settings, 'SRF_SESSION_HOURLY_LIMIT', 6):
                raise UsageLimit('You have reached six recommendations requests this hour. Please use your current plan and try later.')
            cooldown = _number(settings, 'SRF_COOLDOWN_SECONDS', 20)
            if latest is not None and now-latest < cooldown:
                raise UsageLimit(f'Please wait {int(cooldown-(now-latest))+1} seconds before another AI request.')
            db.execute('INSERT INTO requests VALUES (?, ?)', (session_id, now))
    except sqlite3.Error:
        raise UsageLimit('The request budget could not be checked. Please ask the administrator to check the runtime folder.') from None

def record_metrics(metrics, path=None):
    """Allowlist aggregate fields. No query text, profile, resource text, IDs or IPs."""
    allowed = {'success','seconds','search_requests','extraction_requests','tavily_credits','extracted_pages','failed_pages',
               'rejected_campus','duplicate_pages','recommendations','distinct_categories','evidence_pages','total_tokens',
               'prompt_tokens','completion_tokens','estimated_nebius_usd','cache_used','refinement','candidate_count'}
    safe = {k:v for k,v in metrics.items() if k in allowed and isinstance(v,(int,float,bool,type(None)))}
    safe['timestamp'] = int(time.time())
    target = Path(path or Path(__file__).parent / '.runtime' / 'metrics.jsonl')
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('a',encoding='utf-8') as handle:
            handle.write(json.dumps(safe)+'\n')
    except OSError:
        pass  # telemetry must never turn a usable plan into a failed request

def estimate_nebius_cost(usage, settings, model=None):
    try:
        input_value = os.environ.get('NEBIUS_INPUT_USD_PER_MILLION') or settings.get('NEBIUS_INPUT_USD_PER_MILLION')
        output_value = os.environ.get('NEBIUS_OUTPUT_USD_PER_MILLION') or settings.get('NEBIUS_OUTPUT_USD_PER_MILLION')
        if input_value is None or output_value is None:
            rates=json.loads((Path(__file__).parent/'model_rates.json').read_text())
            age=(datetime.now(timezone.utc).date()-datetime.fromisoformat(rates['checked_at']).date()).days
            actual_model=model or usage.get('model') or os.environ.get('NEBIUS_MODEL') or settings.get('NEBIUS_MODEL','nvidia/nemotron-3-super-120b-a12b')
            if actual_model != rates['model'] or not 0 <= age <= rates['valid_days']: return None
            input_value,output_value=rates['input_usd_per_million'],rates['output_usd_per_million']
        input_rate,output_rate=float(input_value),float(output_value)
        if input_rate < 0 or output_rate < 0: return None
        return round((usage['prompt_tokens']*input_rate + usage['completion_tokens']*output_rate)/1_000_000, 6)
    except (KeyError, ValueError, TypeError, OSError):
        return None
