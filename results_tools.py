"""Action plans, source checks, contact drafts and printable, escaped exports."""
from datetime import datetime, timezone
from html import escape
from urllib.parse import urlparse
from evidence import source_badges

def safe_link(url):
    try:
        parsed = urlparse(url)
        return url if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password else '#'
    except ValueError:
        return '#'

def mandatory_checks(resource):
    """Keep conflicts visible regardless of the AI's prose selection."""
    checks = resource.get('checks', [])
    important = []
    for check in checks:
        lowered = check.lower()
        if any(term in lowered for term in ('more than half','under 22','student exemption','graduate','not a guaranteed','immigration','location','residence','residency','coverage household')):
            important.append(check)
    # Concise wording of existing source checks; complete originals remain in
    # the source panel and exports. Never derive a new eligibility criterion.
    pid=resource.get('id')
    if pid=='calfresh':
        short=[]
        if any('more than half' in c.lower() for c in checks): short.append('A campus meal plan covering over half your meals can prevent CalFresh eligibility.')
        if any('under 22' in c.lower() for c in checks): short.append('Under 22 and living with a parent: parents may need to be included in your food household.')
        if any('need a student exemption' in c.lower() for c in checks): short.append('At least half-time students ages 18–49 generally need a student exemption.')
        short.append('The county must review household income, household composition, and citizenship or eligible immigration rules.')
        return short
    if pid=='medi_cal': return ['DHCS or the county must review your coverage household, income, age, immigration rules, and enrollment restrictions.']
    if pid=='cal_grant':
        short=['Confirm residency or qualifying exemption, eligible program, GPA, financial need, deadlines, and remaining eligibility.']
        if any('graduate study' in c.lower() for c in checks): short.insert(0,'General graduate study is usually outside Cal Grant coverage; teacher credentials have separate rules.')
        return short
    if pid=='pell_grant':
        short=['Confirm federal aid eligibility, degree history, financial need, academic progress, and lifetime grant usage.']
        if any('graduate students' in c.lower() for c in checks): short.insert(0,'Graduate students generally do not receive Pell Grants; some teacher-certification programs have an exception.')
        return short
    if pid=='campus_basic_needs': return ['A campus referral does not guarantee a grant or housing placement. Confirm services and enrollment requirements.']
    return list(dict.fromkeys(important)) or checks[:1]

def card_checks(resource, recommendation):
    source=mandatory_checks(resource)
    extra=[]
    for text in recommendation.get('missing_requirements',[]):
        words=set(text.lower().replace(',','').split())-{'the','and','or','a','an','must','confirm','provider','current'}
        if not any(words and len(words & set(s.lower().replace(',','').split()))/len(words) >= .55 for s in source):
            extra.append(text)
    return list(dict.fromkeys(source+extra))

def ordered_recommendations(plan, resources):
    # The model's order carries the action priority; no client-side re-sorting.
    return [r for r in plan['recommendations'] if r['program_id'] in resources]

def action_plan_html(plan, resources):
    items = []
    for item in ordered_recommendations(plan, resources)[:3]:
        resource = resources[item['program_id']]
        items.append(f'<li><strong>{escape(resource["name"].split(" | ")[0])}</strong><span>{escape(item["action"])}</span></li>')
    return '<section class="sr-action-plan"><h2>Start here</h2><ol>'+''.join(items)+'</ol></section>'

def contact_draft(resource, recommendation):
    checks = list(dict.fromkeys(recommendation.get('missing_requirements', []) + mandatory_checks(resource)))
    questions = '\n'.join('- '+check for check in checks[:4])
    return (f'Subject: Question about {resource["name"].split(" | ")[0]}\n\n'
            'Hello,\n\nI am a college student exploring available support. '
            f'I found your page about {resource["name"].split(" | ")[0]} and would like to confirm whether I can apply.\n\n'
            f'My suggested next step was: {recommendation["action"]}\n\n'
            f'Could you clarify these points?\n{questions}\n\n'
            'Please let me know the current availability, application steps, and the correct contact if this is a referral.\n\n'
            'Thank you,\n[Your name]\n\n'
            f'Source: {safe_link(resource["source_url"])}')

def export_text(plan, resources, ids=None):
    allowed = set(ids) if ids is not None else None
    rows = ['Student Resource Finder — My plan', 'Potential matches; providers confirm eligibility and availability.', '']
    for number,item in enumerate(ordered_recommendations(plan,resources),1):
        if allowed is not None and item['program_id'] not in allowed: continue
        resource = resources[item['program_id']]
        provider,categories = source_badges(resource)
        rows += [f'{number}. {resource["name"]}', provider+' | '+', '.join(categories),
                 item.get('about',resource['description']), 'Why: '+item['why'], 'Next: '+item['action'],
                 'Checks:']
        rows += ['- '+check for check in list(dict.fromkeys(item.get('missing_requirements',[])+resource.get('checks',[])))]
        rows += ['Source: '+safe_link(resource['source_url']), 'Explore: '+safe_link(resource['apply_url']), '']
    return '\n'.join(rows)

def export_html(plan, resources, ids=None):
    allowed = set(ids) if ids is not None else None
    articles = []
    for item in ordered_recommendations(plan,resources):
        if allowed is not None and item['program_id'] not in allowed: continue
        r = resources[item['program_id']]
        checks = ''.join('<li>'+escape(check)+'</li>' for check in list(dict.fromkeys(item.get('missing_requirements',[])+r.get('checks',[]))))
        articles.append(f'<article><h2>{escape(r["name"])}</h2><p>{escape(item.get("about",r["description"]))}</p><p><b>Why:</b> {escape(item["why"])}</p><p><b>Next:</b> {escape(item["action"])}</p><h3>Requirements to confirm</h3><ul>{checks}</ul><a href="{escape(safe_link(r["apply_url"]),quote=True)}">Explore this program</a><p class="source">Source: {escape(safe_link(r["source_url"]))}</p></article>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>My student resource plan</title>
<style>body{font:17px/1.7 system-ui,sans-serif;color:#201a2b;max-width:900px;margin:40px auto;padding:0 24px}h1{font-size:32px}h2{font-size:24px}article{border-top:1px solid #ccc;padding:24px 0;break-inside:avoid}a{color:#542b8f}.source{font-size:13px;overflow-wrap:anywhere}button{padding:12px 20px;background:#e4d5ff;border:0;border-radius:8px;font:inherit}@media print{button{display:none}body{margin:0;max-width:none}a{color:#201a2b}}</style>
<h1>My student resource plan</h1><p>Potential matches; providers confirm eligibility and availability.</p><p>This export excludes your questionnaire answers. Keep it private if you add personal notes.</p><button onclick="window.print()">Print / save as PDF</button>''' + ''.join(articles) + '</html>'
