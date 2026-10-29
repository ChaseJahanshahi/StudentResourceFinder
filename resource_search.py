"""Bounded category-by-category discovery and full-page extraction through Tavily."""
import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener

from campuses import resolve_campus
from evidence import APPROVED_NONPROFITS, CATEGORIES, canonical_url, deduplicate, topics_in, resource_kind, campus_scope
from nebius_ai import NoRedirect

MAX_SEARCHES = 10
MAX_PAGES = 12
SEARCH_TERMS = {
    'Food':'food pantry emergency meal grocery assistance',
    'Housing':'emergency housing crisis response student assistance',
    'Healthcare':'student health medical care assistance fund uninsured',
    'Financial Aid':'emergency financial grants scholarships student support',
    'Childcare':'student parent childcare subsidy child care',
}

class SearchError(Exception):
    pass

def get_search_key(secrets=None):
    return str(os.environ.get('TAVILY_API_KEY') or (secrets or {}).get('TAVILY_API_KEY') or '').strip()

def clean(value, limit=120):
    return re.sub(r'[^\w\s.,&-]', '', value or '')[:limit].strip()

def query_specs(profile):
    campus = resolve_campus(profile.get('college', ''))
    college = campus['name'] if campus else clean(profile.get('college', ''))
    location = clean(profile.get('location', ''), 100)
    zip_code = profile.get('zip_code', '')
    zip_code = zip_code if re.fullmatch(r'[0-9]{5}', zip_code) else ''
    specs = []
    # Interleave campus and home queries so a bounded budget still covers all needs.
    for category in CATEGORIES:
        if category not in profile.get('needs', []):
            continue
        if college:
            domain = f"site:{campus['domain']}" if campus else 'site:edu'
            specs.append(dict(query=f'"{college}" {SEARCH_TERMS[category]} eligibility {domain}', category=category, scope='campus'))
        if location or zip_code:
            state = 'California' if profile.get('california') == 'Yes' else ''
            specs.append(dict(query=f'{location} {zip_code} {state} {category} assistance student eligibility government nonprofit', category=category, scope='home'))
    return specs[:MAX_SEARCHES]

def build_queries(profile):
    return [spec['query'] for spec in query_specs(profile)]

def official_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or '').lower()
        approved = host.endswith(('.edu', '.gov', '.ca.us')) or any(host == domain or host.endswith('.'+domain) for domain in APPROVED_NONPROFITS)
        return bool(parsed.scheme == 'https' and host and not parsed.username and not parsed.password and parsed.port is None and approved)
    except (ValueError, AttributeError):
        return False

def _post(endpoint, payload, key):
    request = Request('https://api.tavily.com/'+endpoint, method='POST', data=json.dumps(payload).encode(),
                      headers={'Authorization':'Bearer '+key, 'Content-Type':'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=35) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise SearchError('The source response was too large. Try again later.')
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get('results'), list):
                raise SearchError('The source service returned an unexpected response.')
            return data
    except HTTPError as error:
        if error.code in (401,403):
            raise SearchError('Search could not authenticate. The server administrator must check the Tavily key.') from None
        if error.code in (429,432,433):
            raise SearchError('Search reached its usage limit. Try later or ask the administrator to check credits.') from None
        raise SearchError('Source retrieval is temporarily unavailable.') from None
    except (URLError, OSError, ValueError, UnicodeError):
        raise SearchError('Source retrieval could not complete. Check the connection and try again.') from None

def _search(query, key):
    return _post('search', dict(query=query, search_depth='basic', topic='general', max_results=3,
                               include_answer=False, include_raw_content=False, auto_parameters=False, include_usage=True), key)

def _extract(urls, key):
    return _post('extract', dict(urls=urls, extract_depth='basic', format='text', include_images=False,
                                include_usage=True, timeout=20), key)

def evidence_excerpt(text, limit=6500):
    """Keep the opening plus requirement/application paragraphs, with a hard size bound."""
    paragraphs = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines() if line.strip()]
    relevant = [p for p in paragraphs if re.search(r'\b(eligib|require|qualif|apply|application|enroll|deadline|residen|income|contact|available|funding|must|only)\w*', p, re.I)]
    selected = list(dict.fromkeys(paragraphs[:5] + relevant))
    return '\n'.join(selected)[:limit] or text[:limit]

def discover_resources(profile, key):
    if not key:
        raise SearchError('Add TAVILY_API_KEY on the server to enable source discovery.')
    specs = query_specs(profile)
    if not specs:
        raise SearchError('Enter a campus or home city/county/ZIP to find local resources.')
    report = dict(search_requests=len(specs), extraction_requests=0, extracted_pages=0, failed_pages=0,
                  rejected_campus=0, duplicate_pages=0, tavily_credits=0, notices=[], queries=[s['query'] for s in specs])
    def run(spec):
        try:
            return spec, _search(spec['query'], key), None
        except SearchError as error:
            return spec, None, str(error)
    resources, seen = [], set()
    expected = resolve_campus(profile.get('college', ''))
    now = datetime.now(timezone.utc).isoformat()
    with ThreadPoolExecutor(max_workers=3) as executor:
        for spec, data, error in executor.map(run, specs):
            if error:
                report['notices'].append(error); continue
            if isinstance(data, list):
                data = {'results': data}  # simple offline transport fixtures
            report['tavily_credits'] += (data.get('usage') or {}).get('credits', 0)
            for result in data['results']:
                if not isinstance(result, dict):
                    continue
                url, title, content = result.get('url', ''), result.get('title', ''), result.get('content', '')
                if not official_url(url) or not isinstance(title,str) or not title.strip() or not isinstance(content,str) or not content.strip():
                    continue
                if re.search(r'list of service organizations|annual report|board (?:meeting|agenda)|employment opportunities|center in the news|newsroom',title,re.I):
                    continue
                host = (urlparse(url).hostname or '').lower()
                if expected and host.endswith('.edu') and not (host == expected['domain'] or host.endswith('.'+expected['domain'])):
                    report['rejected_campus'] += 1; continue
                url = canonical_url(url)
                if url in seen:
                    report['duplicate_pages'] += 1; continue
                categories = topics_in(title+' '+content)
                if spec['category'] not in categories:
                    continue  # query alone is not evidence that the page covers this need
                seen.add(url)
                resources.append(dict(
                    id='web_'+hashlib.sha256(url.encode()).hexdigest()[:16], name=title[:180], categories=categories,
                    description=content[:2400], source_url=url, apply_url=url, source_kind='search_result',
                    retrieved_at=now, verified_at=None, reviewed_on=None, evidence_kind='search_excerpt',
                    resource_kind=resource_kind(title), discovery_scope=spec['scope'],
                    status='Search lead; eligibility and current availability need confirmation',
                    reasons=['Found for a selected support need and the campus or home search target.'],
                    checks=['Confirm the program serves your campus or home area, is currently available, and accepts your enrollment status.'],
                    next_step='Read the official source and contact the listed office to confirm eligibility and application steps.',
                ))
    resources = deduplicate(resources)[:MAX_PAGES]
    if resources:
        report['extraction_requests'] = 1
        try:
            data = _extract([r['source_url'] for r in resources], key)
            report['tavily_credits'] += (data.get('usage') or {}).get('credits', 0)
            extracted = {canonical_url(r.get('url','')): r.get('raw_content','') for r in data['results'] if isinstance(r,dict) and official_url(r.get('url',''))}
            for resource in resources:
                text = extracted.get(resource['source_url'])
                if isinstance(text,str) and text.strip():
                    resource['description'] = evidence_excerpt(text)
                    resource['evidence_kind'] = 'page_extract'
                    resource['categories'] = topics_in(resource['name']+' '+text)
                    report['extracted_pages'] += 1
            report['failed_pages'] = len(resources)-report['extracted_pages']
        except SearchError as error:
            report['failed_pages'] = len(resources)
            report['notices'].append(str(error)+' Recommendations will identify excerpts that could not be expanded.')
    for resource in resources:
        resource['campus_scope'] = campus_scope(resource, profile)
    report['notices'] = list(dict.fromkeys(report['notices']))
    return resources, report
