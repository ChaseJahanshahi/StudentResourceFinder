"""Student Resource Finder's original visual system: quiet surfaces, bright intent."""
from html import escape

STYLE = '''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;650;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root {--sr-bg:#0a090c;--sr-panel:#131116;--sr-line:#ffffff14;--sr-text:#f4f2f6;--sr-muted:#9e99a5;--sr-accent:#b182f5;}
html {scroll-behavior:smooth;}
body,.stApp,[data-testid="stAppViewContainer"] {background:#0a090c!important;color:var(--sr-text)!important;font-family:'DM Sans',-apple-system,BlinkMacSystemFont,sans-serif!important;}
[data-testid="stAppViewContainer"] {background:radial-gradient(ellipse at 6% 16%,#5c3d8820,transparent 33%),radial-gradient(ellipse at 94% 2%,#644f8214,transparent 29%),#0a090c!important;}
[data-testid="stHeader"] {display:none!important;}
[data-testid="stToolbar"] {visibility:hidden;}
.block-container {max-width:1440px!important;padding:28px 64px 48px!important;}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {gap:20px;}
h1,h2,h3,h4,.sr-display {font-family:'Manrope',-apple-system,BlinkMacSystemFont,sans-serif!important;}
a {color:var(--sr-accent);}
[data-testid="stHeadingWithActionElements"] a {display:none;}
.st-key-site_header {border-bottom:1px solid #ffffff14;padding-bottom:24px!important;margin-bottom:30px!important;}
.st-key-site_header [data-testid="stPopover"] button {border:0!important;background:transparent!important;min-height:36px!important;color:#a39ea9!important;padding:6px 8px!important;}
.st-key-site_header [data-testid="stPopover"] button p {font-size:12px!important;font-weight:400!important;}
.st-key-site_header [data-testid="stPopover"] button:hover {color:#e6dff1!important;transform:none!important;}

[data-testid="stVerticalBlockBorderWrapper"],[data-testid="stMain"] {overflow-anchor:none;}
.sr-nav {display:flex;justify-content:space-between;align-items:center;padding:4px 0 24px;border-bottom:1px solid var(--sr-line);margin-bottom:44px;gap:20px;}
.sr-brand {display:flex;align-items:center;gap:13px;font-weight:650;font-size:15px;letter-spacing:-.3px;color:var(--sr-text);text-decoration:none;}
.sr-mark {display:grid;place-items:center;width:35px;height:35px;border-radius:10px;background:var(--sr-accent);color:#0e0a13;font-size:22px;font-weight:800;line-height:1;}
.sr-nav-right {display:flex;gap:28px;align-items:center;font-size:13px;}
.sr-nav-right a {color:#a9a5af;text-decoration:none;transition:color .2s;}
.sr-nav-right a:hover {color:#fff;}
.sr-nav-tag {border:1px solid #b182f525;padding:7px 12px;border-radius:100px;color:#c4b7d6;font-size:11px;letter-spacing:1.3px;text-transform:uppercase;}
.sr-kicker {color:var(--sr-accent);font-size:11px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;margin:16px 0 22px;display:flex;gap:10px;align-items:center;}
.sr-kicker:before {content:'';width:6px;height:6px;background:var(--sr-accent);border-radius:50%;box-shadow:0 0 16px #b182f577;}
.sr-hero h1 {font-size:clamp(48px,5vw,76px);font-weight:800;line-height:1.08;letter-spacing:-4px;margin:0 0 26px;padding:0;max-width:610px;color:#f5f3f8;}
.sr-hero h1 em {font-style:normal;background:linear-gradient(110deg,#d3b9f9,#9774c8);background-clip:text;-webkit-background-clip:text;color:transparent;}
.sr-hero-copy {color:#a39ea9;font-size:17px;line-height:1.8;max-width:370px;margin:0 0 32px;}
.sr-mini-proof {display:flex;gap:12px;align-items:center;font-size:12px;color:#ada8b4;margin:25px 0 40px;}
.sr-mini-proof span:first-child {display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#ac80ec12;color:#b182f5;}
.sr-steps {display:flex;flex-direction:column;gap:0;max-width:330px;margin:28px 0 38px;}
.sr-step {display:flex;gap:17px;align-items:center;padding:15px 0;position:relative;color:#76717d;}
.sr-step-dot {height:32px;width:32px;flex-shrink:0;border:1px solid #ffffff19;border-radius:50%;display:grid;place-items:center;font-size:11px;font-weight:650;background:#0e0c10;}
.sr-step.active {color:#f1eff4;}.sr-step.active .sr-step-dot {background:#b182f5;color:#140c20;border-color:#b182f5;box-shadow:0 0 28px #b182f515;}
.sr-step.done .sr-step-dot {border-color:#8469ac55;color:#b182f5;}.sr-step.done{color:#a4a0a9;}
.sr-step-label {font-size:14px;font-weight:600;}.sr-step-note{font-size:12px;font-weight:400;margin-top:4px;color:#7e7886;}
.sr-orbit {position:relative;width:280px;height:120px;overflow:hidden;margin:12px 0 24px;opacity:.8;}
.sr-orbit i {position:absolute;width:235px;height:235px;border:1px solid #b182f519;border-radius:50%;left:0;top:12px;}.sr-orbit i:nth-child(2){left:22px;top:28px;}.sr-orbit i:nth-child(3){left:44px;top:44px;}.sr-orbit:after{content:'';position:absolute;top:36px;left:209px;width:9px;height:9px;background:#b182f5;border-radius:50%;box-shadow:0 0 24px #a36cf377;}
.sr-form-head {margin:0 0 24px;}.sr-form-head .sr-overline{font-size:11px;letter-spacing:1.8px;color:#aea7b8;text-transform:uppercase;margin-bottom:12px;}.sr-form-head h2{font-size:30px;font-weight:700;letter-spacing:-1.1px;margin:0 0 9px;line-height:1.25;}.sr-form-head p{color:#958f9d;font-size:14px;line-height:1.7;margin:0;}
[class*="st-key-question_page_"] {background:linear-gradient(140deg,#18161b,#121014);border:1px solid #ffffff12;border-radius:26px;padding:34px!important;box-shadow:0 24px 70px #0003;}
[data-testid="stWidgetLabel"] p {color:#cfccd4!important;font-size:13px!important;font-weight:500!important;line-height:1.6!important;}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input {background:#0d0b10!important;color:#efedf2!important;min-height:44px!important;caret-color:#b182f5;}
[data-baseweb="input"],[data-baseweb="select"] > div {background:#0d0b10!important;border-color:#ffffff13!important;border-radius:11px!important;}
[data-baseweb="input"]:focus-within,[data-baseweb="select"]:focus-within > div {border-color:#b182f577!important;box-shadow:0 0 0 3px #b182f509;}
[data-baseweb="select"] {font-size:14px!important;}
[data-baseweb="tag"] {background:#b182f518!important;color:#d3bdf2!important;border:1px solid #b182f522!important;border-radius:7px!important;}
[data-testid="stMultiSelect"] [data-tag] {background:#b182f518!important;color:#d3bdf2!important;border:1px solid #b182f522!important;border-radius:7px!important;}
[data-testid="stMultiSelect"] [data-tag] span,[data-testid="stMultiSelect"] [data-tag] button {color:#d3bdf2!important;}
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {padding:7px!important;}
[data-testid="stCaptionContainer"] p {color:#888390!important;font-size:12px!important;line-height:1.8!important;}
[data-testid="stButton"] button {min-height:48px;border-radius:12px!important;border:1px solid #ffffff20;transition:transform .18s,background .18s,box-shadow .18s;}
[data-testid="stButton"] button p {font-size:14px!important;font-weight:600!important;}
[data-testid="stButton"] button:hover {transform:translateY(-2px);border-color:#b182f555;}
button[kind="primary"] {background:#b182f5!important;border:1px solid #b182f5!important;color:#150f20!important;box-shadow:0 5px 22px #8954d614;}
button[kind="primary"] p {color:#150f20!important;}
button[kind="primary"]:hover {background:#c4a1f7!important;box-shadow:0 8px 28px #9762e224;}
button:focus-visible {outline:2px solid #b182f5!important;outline-offset:4px!important;}
button:disabled {opacity:.35!important;transform:none!important;}
.st-key-review_action,.st-key-find_action {width:400px!important;max-width:100%!important;margin-left:0!important;margin-right:auto!important;align-self:flex-start!important;}
.st-key-review_action [data-testid="stButton"],.st-key-find_action [data-testid="stButton"] {width:100%!important;}
.st-key-review_action button,.st-key-find_action button {width:100%!important;min-height:64px!important;border-radius:14px!important;}
.st-key-review_action button {background:#18161b!important;border-color:#ffffff1a!important;color:#cac7cf!important;}
.st-key-results_actions {margin:12px 0 20px;}
.sr-results-hero {padding:10px 0 22px;max-width:900px;}
.sr-results-hero h1 {font-size:clamp(44px,5vw,68px);letter-spacing:-3px;font-weight:800;line-height:1.12;margin:0 0 20px;}
.sr-results-hero h1 em {color:#b182f5;font-style:normal;}
.sr-results-hero p {color:#9a94a3;font-size:17px;line-height:1.7;max-width:590px;}
.sr-context {display:flex;gap:8px;flex-wrap:wrap;margin:20px 0 10px;}.sr-context span{color:#bab4c2;border:1px solid #ffffff14;border-radius:100px;font-size:12px;padding:8px 14px;background:#ffffff03;}
.sr-section-title {display:flex;justify-content:space-between;align-items:end;margin:42px 0 0;gap:16px;}.sr-section-title h2{font-family:'Manrope',sans-serif;font-size:30px;letter-spacing:-1px;margin:0;}.sr-section-title span{font-size:12px;color:#97919f;}
.sr-empty {padding:60px 32px;text-align:center;border:1px dashed #b182f528;border-radius:24px;margin:28px 0;background:radial-gradient(ellipse at center,#7a52b308,transparent);}
.sr-empty .sr-empty-mark{font-size:34px;color:#b182f5;margin-bottom:16px;}.sr-empty h3{font-family:'Manrope',sans-serif;font-size:24px;letter-spacing:-.6px;margin:0 0 12px;}.sr-empty p{color:#97929f;font-size:14px;max-width:420px;margin:auto;line-height:1.8;}
.sr-footer {display:flex;justify-content:space-between;border-top:1px solid #ffffff12;margin-top:56px;padding-top:25px;gap:24px;color:#797282;font-size:11px;letter-spacing:.2px;line-height:1.9;}
.sr-footer a {color:#bbb4c5;text-decoration:none;}.sr-footer .sr-footer-brand{color:#b7b2bf;font-weight:600;}
.sr-about {margin-top:48px;border-top:1px solid #ffffff0e;padding-top:24px;}.sr-about summary{color:#9a94a3;cursor:pointer;font-size:12px;}.sr-about-content{display:grid;grid-template-columns:1fr 1fr;gap:36px;margin-top:24px;}.sr-about-content h4{font-size:14px;margin-bottom:10px;color:#d7d2de;}.sr-about-content p{font-size:12px;line-height:1.9;color:#8c8695;}
[data-testid="stAlert"] {border-radius:14px!important;background:#1d1823!important;border:1px solid #61547444;}
@media(min-width:1100px){.st-key-journey_intro{position:sticky;top:45px;}}
@media(max-width:1000px){[data-testid="stHorizontalBlock"]:has(.st-key-journey_intro){flex-direction:column!important;}[data-testid="stHorizontalBlock"]:has(.st-key-journey_intro)>[data-testid="stColumn"]{width:100%!important;flex:1 1 100%!important;}}
@media(max-width:900px){.block-container{padding:22px 26px 36px!important;}.sr-nav{margin-bottom:28px;}.sr-nav-right a{display:none;}.sr-hero h1{font-size:52px;letter-spacing:-2.7px;}.sr-hero-copy{max-width:550px;}.sr-steps{flex-direction:row;max-width:none;gap:20px;margin:20px 0;}.sr-step-note{display:none;}.sr-step{gap:9px;}.sr-mini-proof,.sr-orbit{display:none;}.sr-nav-tag{font-size:9px;}.sr-footer{flex-direction:column;gap:12px;}}
@media(max-width:600px){[data-testid="stHorizontalBlock"]:has(>.stColumn){flex-wrap:wrap;}[class*="st-key-question_page_"]{padding:24px!important;}.sr-brand{font-size:12px;}.sr-nav-tag{display:none;}.sr-hero h1{font-size:44px;}.sr-step-label{font-size:11px;}.sr-steps{gap:14px;}.sr-step-dot{width:26px;height:26px;}.sr-about-content{grid-template-columns:1fr;}.sr-results-hero h1{font-size:44px;letter-spacing:-2px;}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important;animation:none!important;}}

.block-container:has(.sr-results-hero) {max-width:none!important;width:100%!important;padding-left:3.5vw!important;padding-right:3.5vw!important;}
[data-testid="stNumberInput"] button {display:none!important;}
input[type="number"] {-moz-appearance:textfield;appearance:textfield;}
input[type="number"]::-webkit-inner-spin-button,input[type="number"]::-webkit-outer-spin-button {-webkit-appearance:none;margin:0;}
.st-key-step_navigation {max-width:330px;margin-top:22px;gap:6px!important;}
.st-key-step_navigation button {background:transparent!important;border:0!important;box-shadow:none!important;min-height:48px!important;padding:7px 0!important;justify-content:flex-start!important;gap:16px!important;color:#9e97ad!important;}
.st-key-step_navigation button p {font-size:14px!important;font-weight:600!important;color:inherit!important;}
.st-key-step_navigation button > div {flex:0 1 auto!important;width:auto!important;}
.st-key-step_navigation button [data-testid="stMarkdownContainer"] {text-align:left!important;}
.st-key-step_navigation button:hover {transform:none!important;color:#eee8fa!important;}
.st-key-step_navigation button::before {content:'';display:grid;place-items:center;flex-shrink:0;width:32px;height:32px;border:1px solid #ffffff24;border-radius:50%;font-size:11px;background:#100d16;color:#9e97ad;}
.st-key-step_item_1 button::before {content:"01";}
.st-key-step_item_2 button::before {content:"02";}
.st-key-step_item_3 button::before {content:"03";}

.st-key-step_navigation [class*="st-key-step_done_"] button::before {content:"✓";border-color:#c5a9f66b;color:#ceb5ff;}
.st-key-step_navigation [class*="st-key-step_active_"] button {color:#f3edff!important;}
.st-key-step_navigation [class*="st-key-step_active_"] button::before {background:#ceb5ff;border-color:#ceb5ff;color:#221730;box-shadow:0 0 25px #ceb5ff15;}
.sr-results-hero h1 {font-size:clamp(32px,3.5vw,44px);letter-spacing:-1.8px;}

.sr-results-hero {padding:0 0 4px!important;}
.sr-results-hero h1 {margin-bottom:10px!important;}
.sr-results-hero p {font-size:16px!important;margin:0!important;}
.sr-context {margin:12px 0 0!important;}
.st-key-site_header {margin-bottom:12px!important;}
.st-key-review_action button,.st-key-find_action button {min-height:52px!important;}
.sr-action-plan {border:1px solid #cdb5ff30;background:linear-gradient(120deg,#21182d,#151119);padding:24px 28px;border-radius:20px;margin:12px 0 8px;}
.sr-action-plan h2 {font-size:24px;letter-spacing:-.6px;margin:0 0 12px;}
.sr-action-plan ol {margin:0;padding-left:24px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:32px;}
.sr-action-plan li {padding-left:5px;color:#ceb5ff;font-size:16px;}
.sr-action-plan strong {display:block;color:#f3edff;font-size:16px;line-height:1.5;margin-bottom:8px;}
.sr-action-plan span {display:block;color:#c6bed3;font-size:15px;line-height:1.7;}
.st-key-clarification {padding:24px;border-radius:18px;border:1px solid #ffffff18;background:#17121f;}
.st-key-clarification h3 {font-size:22px!important;}
.st-key-program_grid [data-testid="stHorizontalBlock"] {align-items:stretch;}
.st-key-program_grid [data-testid="stColumn"] {display:flex;flex-direction:column;}
.st-key-program_grid [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {flex:1;}
.st-key-program_grid [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] {flex:1;}
.st-key-program_grid [data-testid="stElementContainer"]:has(> [data-testid="stHtml"]) {display:flex;flex:1;min-width:0;}
.st-key-program_grid [data-testid="stHtml"] {display:flex;flex:1;min-width:0;}
.st-key-program_grid .bb-grid {flex:1;min-width:0;}
.st-key-program_grid .bb-apply {margin-top:auto;}
.st-key-program_grid [class*="st-key-program_"]:not(.st-key-program_grid) {position:relative;}
.st-key-program_grid [data-testid="stLayoutWrapper"]:has(> [class*="st-key-card_save_"]) {position:absolute;top:28px;right:30px;width:max-content!important;max-width:110px;z-index:3;}
.st-key-program_grid [class*="st-key-card_save_"] button {min-height:34px!important;padding:5px 13px!important;border-radius:100px!important;border:1px solid #b794f560!important;background:#b794f514!important;color:#dac7ff!important;transform:none!important;}
.st-key-program_grid [class*="st-key-card_save_"] button p {font-size:12px!important;font-weight:650!important;white-space:nowrap;}
.st-key-program_grid [class*="st-key-card_save_saved_"] button {color:#75dfab!important;border-color:#75dfab60!important;background:#75dfab10!important;}
.st-key-program_grid [class*="st-key-card_save_"] button:hover {filter:brightness(1.25);transform:none!important;}
.st-key-program_grid .bb-card-top {min-height:34px;padding-right:110px;}
.st-key-program_grid .bb-saved-badge {display:none!important;}
.st-key-program_grid .bb-card:hover {transform:none!important;}
@media(max-width:700px){.st-key-program_grid [data-testid="stLayoutWrapper"]:has(> [class*="st-key-card_save_"]){top:24px;right:22px;}}

.st-key-program_grid [data-testid="stColumn"] {min-width:0;}
.bb-card-body {grid-template-columns:minmax(0,1.15fr) minmax(0,1fr)!important;}
.bb-card li {font-size:14px!important;line-height:1.75!important;}
[data-testid="stCaptionContainer"] p {color:#b7adc6!important;}
.sr-form-head p,.sr-footer,.sr-about-content p {color:#b4a9c3!important;}
[data-testid="stDownloadButton"] button {min-height:48px;border-radius:12px;}
@media(max-width:1000px){.st-key-program_grid [data-testid="stHorizontalBlock"]{flex-direction:column!important;}.st-key-program_grid [data-testid="stColumn"]{width:100%!important;flex:1 1 100%!important;}}
@media(max-width:700px){.sr-action-plan ol{grid-template-columns:1fr;gap:20px;}.bb-card-body{grid-template-columns:1fr!important;}.st-key-site_header [data-testid="stHorizontalBlock"]{flex-wrap:wrap;}.st-key-site_header [data-testid="stColumn"]:first-child{min-width:100%!important;}.st-key-step_navigation button{min-height:48px!important;}}
@media(max-width:700px){
.block-container{padding:16px 20px 28px!important;}
.st-key-site_header{padding-bottom:12px!important;margin-bottom:4px!important;}
.st-key-site_header [data-testid="stHorizontalBlock"]{flex-direction:row!important;gap:4px!important;}
.st-key-site_header [data-testid="stColumn"]:not(:first-child){width:48%!important;flex:1 1 48%!important;min-width:0!important;}
.sr-kicker{font-size:10px;letter-spacing:1.5px;margin:4px 0 14px;}
.sr-hero h1{font-size:36px!important;letter-spacing:-1.8px!important;margin-bottom:14px!important;}
.sr-hero-copy{font-size:14px;line-height:1.65;margin-bottom:8px;}
.st-key-step_navigation{flex-direction:row!important;max-width:none;margin-top:6px!important;gap:8px!important;}
.st-key-step_navigation [class*="st-key-step_item_"]{width:31%!important;flex:1 1 31%!important;min-width:0;}
.st-key-step_navigation button{flex-direction:column!important;gap:6px!important;padding:6px 0!important;min-height:66px!important;align-items:center!important;}
.st-key-step_navigation button p{font-size:11px!important;white-space:nowrap;}
.st-key-step_navigation button::before{width:28px;height:28px;}
.st-key-example_actions [data-testid="stHorizontalBlock"]{flex-direction:row!important;gap:8px!important;}
.st-key-example_actions [data-testid="stColumn"]{width:48%!important;flex:1 1 48%!important;min-width:0!important;}
.st-key-example_actions button{min-height:40px!important;padding:6px 10px!important;}
.st-key-example_actions button p{font-size:12px!important;}
[class*="st-key-question_page_"]{padding:22px!important;}
.sr-form-head{margin-bottom:10px;}.sr-form-head h2{font-size:26px;}
}
/* Hide external exception-help links in already-connected clients too. */
[data-testid="stException"] a[href^="https://chatgpt.com/"],
[data-testid="stException"] a[href^="https://www.google.com/search"] {display:none!important;}
</style>'''


def nav():
    return '<div class="sr-brand"><span class="sr-mark" aria-hidden="true">↗</span>Student Resource Finder</div>'



def journey_intro(step):
    return '<section class="sr-hero"><div class="sr-kicker">California student support</div><h1>More support.<br><em>Less searching.</em></h1><p class="sr-hero-copy">Find food, housing, healthcare, childcare, and financial aid programs for your campus and location.</p></section>'


def form_heading(step):
    headings = {
        1: ('STEP 1', 'About you', 'Your college, enrollment, and location.'),
        2: ('STEP 2', 'Support needs', 'Select the help you need and describe your living situation.'),
        3: ('STEP 3', 'Finances', 'Your monthly income and financial aid application status.'),
    }
    overline, title, subtitle = headings[step]
    return f'<div class="sr-form-head"><div class="sr-overline">{overline} · {step:02} / 03</div><h2>{title}</h2><p>{subtitle}</p></div>'


def results_intro(profile):
    campus = profile.get('college', '').strip()
    if campus.lower() == 'ucla':
        campus = 'UCLA'
    chips = [campus] if campus else []
    chips += list(profile.get('needs', []))
    context = ''.join(f'<span>{escape(item)}</span>' for item in chips)
    return f'<section class="sr-results-hero"><h1>Your recommendations</h1><p>Programs for your selected needs, campus, and home area.</p><div class="sr-context">{context}</div></section>'



def empty_state():
    return '''<section class="sr-empty"><div class="sr-empty-mark" aria-hidden="true">↗</div><h3>Ready to find programs</h3><p>Click Find Recommendations to search campus and local resources and compare relevant programs.</p></section>'''


def footer():
    return '''<section class="sr-about"><div class="sr-about-content"><section id="how-it-works"><h4>How recommendations work</h4><p>Your answers help NVIDIA Nemotron compare relevant programs and explain your next steps. When available, Tavily finds school and local resources. Recommendations are starting points; providers confirm eligibility and availability.</p></section><section id="your-privacy"><h4>How your answers are used</h4><p>Answers and saved programs stay in this app session. Generating or updating a plan sends selected answers to Nebius and campus/home searches to Tavily. We retain anonymous usage counts, not answer logs. Avoid identity documents or sensitive identifiers.</p></section></div></section><footer class="sr-footer"><span class="sr-footer-brand">Student Resource Finder</span><span>Campus, local, and statewide programs</span><span>California student support · NVIDIA Nemotron + Nebius</span></footer>'''
