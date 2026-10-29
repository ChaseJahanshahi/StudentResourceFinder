"""Source labels, topic inference and conservative program deduplication."""
import re
from urllib.parse import urlparse, urlunparse
from campuses import campus_from_host, resolve_campus

CATEGORIES = ['Food', 'Healthcare', 'Housing', 'Financial Aid', 'Childcare']
TOPICS = {
    'Food': r'\b(food|meals?|grocer(?:y|ies)|pantr(?:y|ies)|calfresh|snap)\b',
    'Healthcare': r'\b(health(?:care)?|medical|insurance|medi-cal|clinic)\b',
    'Housing': r'\b(housing|rent(?:al)?|shelter|homeless(?:ness)?)\b',
    'Financial Aid': r'\b(financial aid|financial assistance|scholarships?|grants?|tuition|fafsa|emergency fund(?:s|ing)?)\b',
    'Childcare': r'\b(childcare|child care|dependent care|daycare|student parents?)\b',
}
APPROVED_NONPROFITS = {'211.org', '211la.org', '211oc.org', 'feedingamerica.org', 'findhelp.org'}

def topics_in(text):
    return [category for category, pattern in TOPICS.items() if re.search(pattern, text, re.I)]

def canonical_url(url):
    parsed = urlparse(url)
    # Tracking queries do not define distinct programs. Preserve meaningful parameters.
    query = '&'.join(part for part in parsed.query.split('&') if part and not part.lower().startswith(('utm_', 'fbclid=', 'gclid=')))
    return urlunparse((parsed.scheme, parsed.netloc.lower(), re.sub(r'/+', '/', parsed.path).rstrip('/') or '/', '', query, ''))

def source_badges(resource):
    host = (urlparse(resource.get('source_url') or resource.get('apply_url', '')).hostname or '').lower()
    campus = campus_from_host(host)
    provider = campus['short'] if campus else resource.get('provider_label') or ('Government' if host.endswith(('.gov', '.ca.us')) else 'Community resource')
    # Curated labels are editorial; search labels come from bounded-word evidence.
    categories = resource.get('categories', [])
    if resource.get('source_kind') == 'search_result':
        categories = topics_in(resource.get('name', '') + ' ' + resource.get('description', ''))
    return provider, categories

def resource_kind(title, text=''):
    if re.search(r'\b(directory|resources|resource hub|resource guide|find your|basic.needs|student support office)\b', title, re.I):
        return 'referral'
    return 'program' if re.search(r'\b(grant|pantry|scholarship|program|calfresh|medi-cal|child care|childcare|(?:assistance|emergency) fund)\b', title, re.I) else 'information'

KNOWN_PROGRAMS = {
    'calfresh': r'\bcalfresh\b', 'medi_cal': r'\bmedi-cal\b', 'pell_grant': r'\bpell grant\b',
    'cal_grant': r'\bcal grant\b', 'promise_grant': r'\bcalifornia college promise grant\b',
    'campus_ecrt': r'\b(ecrt|economic crisis response team)\b',
}

def program_identity(resource):
    title = resource.get('name', '').split(' | ')[0]
    text = title.lower()+' '+urlparse(resource.get('source_url','')).path.replace('-',' ')
    # A generic "Applying" title can be the same benefit as a named record.
    # Only use leading body evidence for narrow application pages, not broad hubs.
    if re.fullmatch(r'\s*(applying|apply|eligibility|how to apply)\s*',title,re.I):
        text += ' '+resource.get('description','')[:1200].lower()
    host = (urlparse(resource.get('source_url', '')).hostname or '').lower()
    campus = campus_from_host(host)
    for identity, pattern in KNOWN_PROGRAMS.items():
        if re.search(pattern, text):
            return (campus['domain'] if identity.startswith('campus_') and campus else '') + ':' + identity
    title = re.sub(r'\b(home|overview|welcome|official|application|apply|eligibility)\b', '', text)
    title = re.sub(r'[^a-z0-9]+', ' ', title).strip()
    return (campus['domain'] if campus else host.removeprefix('www.')) + ':' + title

def deduplicate(resources):
    chosen, urls, identities = [], set(), {}
    # Curated records carry mandatory checks; retain those when a web page repeats them.
    ordered = sorted(resources, key=lambda r: r.get('source_kind') == 'search_result')
    for resource in ordered:
        url = canonical_url(resource.get('source_url') or resource.get('apply_url', ''))
        identity = program_identity(resource)
        if url in urls or identity in identities:
            existing = identities.get(identity)
            if existing is not None:
                existing.setdefault('additional_sources', [])
                if url != existing.get('source_url') and url not in existing['additional_sources']:
                    existing['additional_sources'].append(url)
                    if resource.get('evidence_kind') == 'page_extract':
                        existing['additional_evidence'] = (existing.get('additional_evidence','')+'\n'+resource.get('description',''))[:5000]
            continue
        item = dict(resource)
        urls.add(url); identities[identity] = item; chosen.append(item)
    return chosen

def campus_scope(resource, profile):
    expected = resolve_campus(profile.get('college', ''))
    host = (urlparse(resource.get('source_url', '')).hostname or '').lower()
    found = campus_from_host(host)
    if expected and found and found['domain'] != expected['domain']:
        return 'different_campus'
    if expected and (host == expected['domain'] or host.endswith('.'+expected['domain'])):
        return 'campus_domain'
    return 'needs_confirmation'
