"""Responsive recommendation grid. All generated text is escaped as plain text."""
from html import escape
from urllib.parse import urlparse
from evidence import source_badges
from results_tools import mandatory_checks, safe_link, card_checks

def resource_category(resource):
    provider, categories = source_badges(resource)
    return ' · '.join([provider] + categories)


def recommendation_grid(plan, resources, saved_ids=()):
    cards = []
    saved_ids = set(saved_ids)
    recommendations = plan['recommendations']
    for recommendation in recommendations:
        resource = resources[recommendation['program_id']]
        saved = recommendation['program_id'] in saved_ids
        border, footer = ('#75dfab' if saved else '#a88dce'), '#30223f'
        saved_badge = '<span class="bb-saved-badge"><span aria-hidden="true">✓</span> Saved</span>' if saved else ''
        provider, categories = source_badges(resource)
        category = '<span class="bb-provider">'+escape(provider)+'</span>' + ''.join('<span class="bb-topic">'+escape(c)+'</span>' for c in categories)
        kind = {'program':'Program', 'referral':'Referral / directory', 'information':'Information page'}.get(resource.get('resource_kind','program'), 'Information page')
        evidence = 'Page content retrieved' if resource.get('evidence_kind') == 'page_extract' else 'Search excerpt only' if resource.get('source_kind') == 'search_result' else 'Curated source'
        source_note = escape(kind+' · '+evidence)
        link_label = 'View referral' if resource.get('resource_kind') == 'referral' else 'Read source page' if resource.get('resource_kind') == 'information' else 'Explore this program'
        title = escape(resource['name'].split(' | ')[0])
        about = escape(recommendation.get('about') or resource['description'])
        why = escape(recommendation['why'])
        action = escape(recommendation['action'])
        missing = card_checks(resource,recommendation)
        if not missing:
            missing = ['The provider still needs to confirm full eligibility and availability.']
        requirements = ''.join(f'<li>{escape(item)}</li>' for item in missing)
        href = resource['apply_url']
        parsed = urlparse(href)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            href = '#'
        cards.append(f'''<article class="bb-card{' bb-saved' if saved else ''}" style="--match-border:{border};--match-footer:{footer}">
<header><div class="bb-card-top"><span class="bb-origin">{category}</span>{saved_badge}</div><h3>{title}</h3><div class="bb-source-note">{source_note}</div></header>
<div class="bb-card-body"><section><h4>About this program</h4><p>{about}</p>
<h4>Why it fits</h4><p>{why}</p></section>
<section class="bb-requirements"><h4>Requirements to confirm</h4><ul>{requirements}</ul>
</section></div>
<div class="bb-action"><strong>Your next step</strong><p>{action}</p></div>
<a class="bb-apply" href="{escape(href, quote=True)}" target="_blank" rel="noopener noreferrer" aria-label="{link_label}: {title}">{link_label} <span class="bb-arrow" aria-hidden="true">↗</span></a>
</article>''')
    return '''<style>
.bb-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:26px;margin:26px 0 32px;font-family:'DM Sans',sans-serif;color:#f0edf3;}
.bb-card{display:flex;flex-direction:column;min-width:0;min-height:470px;border:2px solid #a88dce45;border-radius:24px;overflow:hidden;background:linear-gradient(155deg,#1c1921,#131016 70%);transition:transform .25s,border-color .25s,box-shadow .25s;}
.bb-card.bb-saved{border-color:#75dfab;}
.bb-card:hover{transform:translateY(-5px);border-color:var(--match-border);box-shadow:0 24px 60px #0004;}
.bb-provider,.bb-topic{border:1px solid #ffffff1c;padding:3px 8px;border-radius:6px;letter-spacing:.3px;text-transform:none;}.bb-provider{color:#dac7ff;background:#b794f51a;}.bb-source-note{font-size:12px;color:#b5abc5;line-height:1.7;margin-bottom:4px;}.bb-card header{padding:28px 30px 12px;}
.bb-card-top{align-items:flex-start!important;display:flex;align-items:center;justify-content:space-between;gap:14px;}
.bb-origin{display:flex;flex-wrap:wrap;gap:6px;font-size:11px;font-weight:650;letter-spacing:1.2px;text-transform:uppercase;line-height:1.7;color:#c5bad8;}
.bb-card h3{font-family:'Manrope',sans-serif!important;font-size:25px!important;line-height:1.35;font-weight:700;letter-spacing:-.8px;margin:24px 0 16px;color:#f2f0f5;overflow-wrap:anywhere;min-height:2.7em;}
.bb-saved-badge{font-size:12px;font-weight:650;color:#75dfab;padding:6px 10px;border:1px solid #75dfab45;background:#75dfab10;border-radius:100px;white-space:nowrap;}
.bb-card-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:25px;padding:8px 30px 16px;flex:1;}
.bb-card h4{font-family:'DM Sans',sans-serif!important;font-size:12px!important;font-weight:650;color:#c9c4d0;margin:0 0 12px;}
.bb-card p,.bb-card li{font-size:16px;line-height:1.8;color:#c0b9cc;overflow-wrap:anywhere;}
.bb-card p{margin:0 0 24px;}
.bb-requirements{padding-left:25px;border-left:1px solid #ffffff0c;}
.bb-card ul{padding-left:17px;margin:0;}.bb-card li{margin:0 0 10px;padding-left:2px;}.bb-card li::marker{color:var(--match-border);}
.bb-action{padding:0 30px 24px;}.bb-action strong{font-size:12px;color:#c9c4d0;font-weight:650;}.bb-action p{font-size:15px;margin:8px 0 0;line-height:1.8;}
.bb-apply{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:18px 30px;background:var(--match-footer);border-top:1px solid color-mix(in srgb,var(--match-border) 18%,transparent);color:#f1edf6!important;font-size:14px;font-weight:600;text-decoration:none!important;transition:filter .2s;}
.bb-arrow{display:grid;place-items:center;width:30px;height:30px;border:1px solid #ffffff25;border-radius:50%;font-size:18px;transition:transform .2s;}.bb-apply:hover{filter:brightness(1.18);}.bb-apply:hover .bb-arrow{transform:translate(2px,-2px);}.bb-apply:focus-visible{outline:2px solid #b182f5;outline-offset:-5px;}
@media(max-width:950px){.bb-grid{grid-template-columns:1fr;}}
@media(max-width:700px){.bb-card header{padding:24px 22px 10px;}.bb-card-body{padding:8px 22px 12px;grid-template-columns:1fr;gap:8px;}.bb-requirements{border-left:0;border-top:1px solid #ffffff0c;padding:22px 0 0;}.bb-action{padding:0 22px 22px;}.bb-apply{padding:16px 22px;}.bb-card h3{font-size:23px!important;}.bb-origin{font-size:8px;}}
@media(prefers-reduced-motion:reduce){.bb-card,.bb-apply,.bb-arrow{transition:none!important;transform:none!important;}}
.st-key-program_grid .bb-grid{grid-template-columns:1fr;margin:0;}.st-key-program_grid .bb-card{min-height:0;}
</style><div class="bb-grid" role="region" aria-label="Personalized assistance recommendations">''' + ''.join(cards) + '</div>'
