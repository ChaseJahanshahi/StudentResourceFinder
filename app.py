"""Student Resource Finder: evidence-grounded discovery and a private session plan."""
import copy
from html import escape
import time
import uuid
import streamlit as st

from campuses import CAMPUS_LIST, resolve_campus
from matching import match_programs, validate_profile
from nebius_ai import NebiusError, get_config, generate_plan
from resource_search import SearchError, get_search_key, discover_resources
from evidence import CATEGORIES, deduplicate, source_badges
from profile_state import DEFAULTS, blank_profile, normalized_profile, section_errors, fingerprint
from card_renderer import render_cards
from results_tools import export_html, ordered_recommendations
from usage_control import UsageLimit, reserve_generation, record_metrics, estimate_nebius_cost
from answer_review import answer_review
from design_system import STYLE, nav, journey_intro, form_heading, results_intro, empty_state, footer

st.set_page_config(page_title="Student Resource Finder", layout="wide", initial_sidebar_state="collapsed")
st.html(STYLE)
try:
    server_secrets = dict(st.secrets)
except FileNotFoundError:
    server_secrets = {}

# Optional private test access. Set a fresh code in server secrets, not source control.
access_code = server_secrets.get('DEMO_ACCESS_CODE')
if access_code and not st.session_state.get('demo_access'):
    st.title('Student Resource Finder')
    code = st.text_input('Demo access code', type='password')
    if st.button('Open demo'):
        import hmac
        if hmac.compare_digest(code, str(access_code)):
            st.session_state.demo_access = True
            st.rerun()
        st.error('That code did not match.')
    st.stop()

if st.session_state.get('product_version') != 2:
    for key in list(st.session_state):
        if key not in ('demo_access',): del st.session_state[key]
    st.session_state.update(product_version=2, questionnaire_draft=blank_profile(), questionnaire_step=1,
                            completed_steps=[], saved_programs=[], session_id=uuid.uuid4().hex)
draft = st.session_state.questionnaire_draft

def reset_answers(example=False):
    for key in list(st.session_state):
        if key.startswith('answer_') or key.startswith('follow_answer_') or key in ('nemotron_result','result_profile','result_resources','nemotron_error','resource_profile','discovery_cache','search_notice','last_report','last_metrics','show_answer_review'):
            del st.session_state[key]
    st.session_state.questionnaire_draft = blank_profile(example)
    st.session_state.questionnaire_step = 1
    st.session_state.completed_steps = []
    st.session_state.saved_programs = []
    st.session_state.scroll_page_to_top = True

def field(kind, name, label, *args, **kwargs):
    key = 'answer_'+name
    if key not in st.session_state: st.session_state[key] = draft.get(name)
    kwargs.pop('value', None)
    def remember():
        draft[name] = st.session_state[key]
        st.session_state.completed_steps = [n for n in st.session_state.completed_steps if n != st.session_state.questionnaire_step]
    value = getattr(st, kind)(label, *args, key=key, on_change=remember, **kwargs)
    draft[name] = value
    return value

def go_to(step, complete=False):
    current = st.session_state.questionnaire_step
    if complete:
        errors = section_errors(draft, current)
        if errors:
            st.session_state.navigation_errors = errors
            return
        st.session_state.completed_steps = sorted(set(st.session_state.completed_steps) | {current})
    # Clicking a section alone does not certify it as completed.
    st.session_state.questionnaire_step = step
    st.session_state.scroll_page_to_top = True

def submit_answers():
    errors = [error for n in (1,2,3) for error in section_errors(draft,n)]
    if errors:
        st.session_state.navigation_errors = errors
        return
    st.session_state.resource_profile = normalized_profile(draft)
    st.session_state.completed_steps = [1,2,3]
    go_to(4)

def toggle_saved(program_id):
    saved = set(st.session_state.saved_programs)
    saved.symmetric_difference_update({program_id})
    st.session_state.saved_programs = sorted(saved)

def run_generation(profile, refinement=False):
    start = time.monotonic()
    metrics = dict(success=False, refinement=refinement, search_requests=0, extraction_requests=0, cache_used=False)
    st.session_state.pop('nemotron_error', None)
    try:
        reserve_generation(st.session_state.session_id, server_secrets)
        config = get_config(server_secrets)
        config.validate()
        matches = match_programs(profile)
        report = dict(notices=[], search_requests=0, extraction_requests=0, tavily_credits=0)
        discovered = []
        search_key = get_search_key(server_secrets)
        targets = {k:profile.get(k) for k in ('college','location','zip_code','california','needs')}
        target_key = fingerprint(targets)
        cache = st.session_state.get('discovery_cache', {})
        cached = cache.get(target_key)
        with st.status('Finding relevant programs', expanded=True) as status:
            if search_key and any(profile.get(k) for k in ('college','location','zip_code')):
                if cached and time.time()-cached['created'] < 1800:
                    discovered, report = copy.deepcopy(cached['resources']), copy.deepcopy(cached['report'])
                    metrics['cache_used'] = True
                    st.write('Reusing recently retrieved campus and home-area sources.')
                else:
                    st.write('Searching each selected need for your campus and home area; then reading selected source pages.')
                    try:
                        discovered, report = discover_resources(targets, search_key)
                        if discovered:
                            cache[target_key] = dict(created=time.time(), resources=copy.deepcopy(discovered), report=copy.deepcopy(report))
                        st.session_state.discovery_cache = cache
                        metrics.update({k:v for k,v in report.items() if isinstance(v,(int,float))})
                    except SearchError as error:
                        report['notices'].append(str(error)+' Using curated sources for this request.')
                if not discovered: report['notices'].append('No usable local pages were found. This plan uses curated starting points.')
            else:
                report['notices'].append('Local discovery was not used: add a campus/home location and configure search to broaden the sources.')
            resources = deduplicate(discovered + matches)
            generation_profile = dict(profile)
            if discovered: generation_profile['_search_target'] = {k:profile.get(k,'') for k in ('college','location','zip_code')}
            st.write('NVIDIA Nemotron is comparing the evidence with your answers and prioritizing next steps.')
            result = generate_plan(generation_profile, resources, config)
            st.write('Checking resource IDs, duplicate entries, source conflicts, and response structure.')
            status.update(label='Recommendations ready', state='complete', expanded=False)
        resource_map = {r['id']:r for r in resources}
        metrics.update(success=True, candidate_count=len(resources), recommendations=len(result['plan']['recommendations']),
                       distinct_categories=len({c for r in result['plan']['recommendations'] for c in resource_map[r['program_id']].get('categories',[])}),
                       evidence_pages=sum(r.get('evidence_kind') == 'page_extract' for r in resources),
                       total_tokens=result.get('total_tokens'), prompt_tokens=result.get('prompt_tokens'), completion_tokens=result.get('completion_tokens'))
        metrics['estimated_nebius_usd'] = estimate_nebius_cost(metrics, server_secrets, config.model)
        st.session_state.update(nemotron_result=result, result_profile=copy.deepcopy(profile), result_resources=resource_map,
                                search_notice=list(dict.fromkeys(report['notices'])), last_report=report)
        current_ids = {item['program_id'] for item in result['plan']['recommendations']}
        st.session_state.saved_programs = [pid for pid in st.session_state.saved_programs if pid in current_ids]
    except (NebiusError, SearchError, UsageLimit) as error:
        st.session_state.nemotron_error = str(error)
    metrics['seconds'] = round(time.monotonic()-start, 2)
    st.session_state.last_metrics = metrics
    record_metrics(metrics)

with st.container(key='site_header'):
    brand, how, privacy = st.columns([.64,.18,.18], gap='small', vertical_alignment='center')
    with brand: st.html(nav())
    with how:
        with st.popover('How it works', use_container_width=True):
            st.write('Choose your campus and needs. We retrieve relevant sources, then NVIDIA Nemotron on Nebius compares them with your answers. Providers confirm eligibility and availability.')
    with privacy:
        with st.popover('Your privacy', use_container_width=True):
            st.write('Your answers and saved programs stay in this app session. Find Recommendations sends selected answers to Nebius. Campus, home city/ZIP, and selected needs go to Tavily for discovery. We keep aggregate usage counts, not questionnaire logs. Downloads exclude your questionnaire answers. Closing the session can clear your saved programs.')

step = st.session_state.questionnaire_step
for error in st.session_state.pop('navigation_errors', []): st.error(error)
if step <= 3:
    intro_column, form_column = st.columns([.95,1.05], gap='large')
    with intro_column:
        with st.container(key='journey_intro'):
            st.html(journey_intro(step))
            with st.container(key='step_navigation'):
                for target,label in enumerate(('About you','Support needs','Finances'),1):
                    status = 'active' if target == step else 'done' if target in st.session_state.completed_steps else 'pending'
                    with st.container(key=f'step_item_{target}'):
                        with st.container(key=f'step_{status}_{target}'):
                            st.button(label, key=f'jump_step_{target}', on_click=go_to, args=(target,), use_container_width=True)
            with st.container(key='example_actions'):
                example_column, reset_column = st.columns(2)
                with example_column: st.button('Try an example', on_click=reset_answers, args=(True,), help='Loads a fictional student profile for testing.')
                with reset_column: st.button('Start over', on_click=reset_answers, args=(False,))
    with form_column:
        with st.container(key=f'question_page_{step}'):
            st.html(form_heading(step))
            if step == 1:
                options = ['']+[c['name'] for c in CAMPUS_LIST]+['Other campus / not listed']
                choice = field('selectbox','college_choice','Your campus (optional)',options, format_func=lambda value:(resolve_campus(value)['short']+' · '+value) if resolve_campus(value) else value or 'Choose a campus', help='Type a campus name or acronym to filter. Choose Other for a campus outside this starter list.')
                if choice == 'Other campus / not listed':
                    field('text_input','college','Full college name (optional)',max_chars=120)
                    st.caption('An unrecognized campus needs confirmation. We will not assume an official domain from its name.')
                else:
                    if choice != draft.get('college'):
                        draft['college'] = choice
                        campus = resolve_campus(choice)
                        if campus:
                            draft['college_type'] = campus['college_type']
                            st.session_state['answer_college_type'] = campus['college_type']
                    campus = resolve_campus(choice)
                    if campus: st.caption(f"Campus source: {campus['domain']} · Campus city: {campus['city']}. Home location is entered separately below.")
                left,right = st.columns(2)
                with left: field('number_input','age','Age (optional)',min_value=16,max_value=100,value=None,placeholder='Not provided')
                with right: field('selectbox','california','Do you currently live in California?',['Not sure','Yes','No'])
                left,right = st.columns(2)
                with left: field('selectbox','college_type','College type',['Not sure','California community college','CSU','UC','Private / other'])
                with right: field('selectbox','degree','Program or degree',['Not sure','Associate',"Bachelor's",'Certificate / vocational','Teacher credential','Graduate'])
                field('selectbox','enrollment','Enrollment level',['Not sure','Less than half-time','Half-time','Full-time','Not currently enrolled'])
                left,right = st.columns(2)
                with left: field('text_input','location','Home city or county (optional)',max_chars=100,help='Where you live, which can differ from your campus city. Used for community resources.')
                with right: field('text_input','zip_code','Home ZIP code (optional)',max_chars=5)
            elif step == 2:
                needs = field("multiselect", "needs", "Select all that apply", ["Food", "Healthcare", "Housing", "Financial Aid", "Childcare"])
                housing = field("selectbox", "housing", "Current housing", ["Prefer not to say", "Campus housing", "Renting / own home", "With family", "Temporary / staying with others", "Without stable housing"])
                insurance = "Not sure"
                if "Healthcare" in needs:
                    insurance = field("selectbox", "insurance", "Do you have health insurance?", ["Not sure", "Yes", "No", "Prefer not to say"])
                dependents = "Prefer not to say"
                if "Childcare" in needs:
                    dependents = field("selectbox", "dependents", "Do you support children or other dependents?", ["Prefer not to say", "Yes", "No"])
            
                # Defaults describe skipped answers, rather than reusing hidden widget values.
                meal_plan = "Not sure"
                food_household_size = None
                food_with_parents = "Not sure"
                work_hours = None
                work_study = "Not sure"
                student_exemption = "Not sure"
                if "Food" in needs:
                    st.markdown("**Food assistance details**")
                    meal_plan = field("selectbox", "meal_plan", "Does a college meal plan provide more than half your meals?", ["Not sure", "Yes", "No"])
                    campus_meals = housing == "Campus housing" and meal_plan == "Yes"
                    if campus_meals:
                        st.caption("You can skip the food-household and student-exemption questions. Your results will explain the campus meal-plan rule and other food resources.")
                    else:
                        food_household_size = field("number_input", "food_household_size", "How many people usually buy and prepare food together, including you?", min_value=1, max_value=30, value=1, help="A starting estimate only. CalFresh has special household rules, including for some students living with parents.")
                        if housing != "Campus housing":
                            food_with_parents = field("selectbox", "food_with_parents", "Do you live with a parent?", ["Not sure", "Yes", "No"])
                        public_degree = draft["college_type"] in ("California community college", "CSU", "UC") and draft["degree"] in ("Associate", "Bachelor's")
                        if draft.get("age") is not None and 18 <= draft["age"] <= 49 and draft["enrollment"] in ("Half-time", "Full-time") and not public_degree:
                            work_hours = field("number_input", "work_hours", "Average paid work hours per week", min_value=0, max_value=100, value=0)
                            if (work_hours or 0) < 20:
                                work_study = field("selectbox", "work_study", "Are you approved for work-study and expecting to work?", ["Not sure", "Yes", "No"])
                                if work_study != "Yes":
                                    student_exemption = field("selectbox", "student_exemption", "Has a navigator confirmed another CalFresh student exemption for you?", ["Not sure", "Yes", "No"], help="Examples may include an approved training program, certain caregiving circumstances, or inability to work. You do not need to disclose medical details.")
            elif step == 3:
                income_known = field("checkbox", "income_known", "I can estimate my personal gross monthly income")
                income = None
                if income_known:
                    with st.container(border=True):
                        st.markdown("**Monthly income**")
                        st.markdown("Your monthly income before taxes (optional)")
                        currency, amount = st.columns([1, 18], vertical_alignment="center")
                        with currency:
                            st.markdown("**$**")
                        with amount:
                            income = field("number_input", "income", "Your monthly income before taxes ($; optional)", min_value=0, value=0, step=50, label_visibility="collapsed", help="Used only as context. Program household income can differ from personal income.")
            
                aid_application = "Not sure"
                if "Financial Aid" in draft["needs"]:
                    st.markdown("**Student financial aid**")
                    aid_application = field("selectbox", "aid_application", "FAFSA / California Dream Act application status", ["Not sure", "Not started", "FAFSA started / submitted", "California Dream Act started / submitted"])
        back,forward = st.columns(2)
        with back: st.button('Back', disabled=step==1, on_click=go_to, args=(step-1,), use_container_width=True)
        with forward:
            if step < 3: st.button('Next', type='primary', on_click=go_to, args=(step+1,True), use_container_width=True)
            else: st.button('Review answers', type='primary', on_click=submit_answers, use_container_width=True)
elif 'resource_profile' in st.session_state:
    profile = st.session_state.resource_profile
    result = st.session_state.get('nemotron_result')
    stale = bool(result and fingerprint(profile) != fingerprint(st.session_state.result_profile))
    st.html(results_intro(profile))
    with st.popover('Edit answers'):
        for target,label in zip((1,2,3),('Edit campus / location','Edit support needs','Edit finances')):
            st.button(label,on_click=go_to,args=(target,),use_container_width=True)
    st.caption('Potential matches; providers confirm eligibility and availability.')
    if profile.get('california') == 'No':
        st.info('This app focuses on California campuses and programs. California-specific options need location review; federal aid and home-area sources are considered separately.')
    if stale: st.info('Your answers changed. The programs below still use your previous answers until you refresh recommendations.')
    with st.container(key='review_action'):
        if st.button('Review the answers used',use_container_width=True):
            st.session_state.show_answer_review = not st.session_state.get('show_answer_review',False)
    if st.session_state.get('show_answer_review'):
        st.html(answer_review(st.session_state.result_profile if result else profile))
        if stale:
            with st.expander('Current edited answers'): st.html(answer_review(profile))
    config = get_config(server_secrets)
    try: config.validate(); ai_ready=True
    except NebiusError: ai_ready=False
    if not ai_ready: st.info('AI recommendations need server setup. See README.md for Nebius configuration.')
    with st.container(key='find_action'):
        label = 'Refresh recommendations' if result else 'Find Recommendations'
        if st.button(label,type='secondary' if result else 'primary',disabled=not ai_ready,use_container_width=True):
            run_generation(profile)
            st.rerun()
    st.caption('Generating or updating a plan sends selected answers to Nebius and campus/home searches to Tavily. Browsing, saving, filtering, and downloads make no AI request.')
    if st.session_state.get('nemotron_error'):
        st.warning(st.session_state.nemotron_error)
        if result: st.caption('Your last successful plan is retained below.')
    for notice in st.session_state.get('search_notice',[]): st.info(notice)
    if result:
        plan = result['plan']
        resources = st.session_state.result_resources
        if result.get('validation_repairs'):
            st.caption('Some AI wording was replaced with source-based guidance. Program selection and ordering still come from Nemotron.')
        items = ordered_recommendations(plan,resources)
        st.html(f'<div class="sr-section-title"><h2>Matching programs</h2><span>{len(items)} options</span></div>')
        if len(items)<6: st.caption('Fewer than six options were supported by the available evidence. We have not added weak matches to fill the list.')
        category = st.radio('Filter by support category',['All']+CATEGORIES,horizontal=True,key='category_filter')
        saved_only = st.checkbox('Show saved programs only',key='saved_only')
        visible = [r for r in items if (category=='All' or category in source_badges(resources[r['program_id']])[1]) and (not saved_only or r['program_id'] in st.session_state.saved_programs)]
        st.caption(f'{len(visible)} shown · {len(st.session_state.saved_programs)} saved. Saved programs stay in this session; download your plan to keep it.')
        if not visible: st.info('No programs match this filter. Try All or turn off saved-only.')
        with st.container(key='program_grid'):
            for start in range(0,len(visible),2):
                columns = st.columns(2,gap='large')
                for column,item in zip(columns,visible[start:start+2]):
                    resource=resources[item['program_id']]
                    with column:
                        with st.container(key='program_'+item['program_id']):
                            saved=item['program_id'] in st.session_state.saved_programs
                            with st.container(key=('card_save_saved_' if saved else 'card_save_idle_')+item['program_id']):
                                st.button('Saved ✓' if saved else 'Save',key='save_'+item['program_id'],on_click=toggle_saved,args=(item['program_id'],),help='Remove from saved programs' if saved else 'Save this program',use_container_width=False)
                            st.html(render_cards(dict(recommendations=[item]),resources,st.session_state.saved_programs))
        st.subheader('Keep your plan')
        st.caption('Download saved includes your shortlist. Download all includes every recommendation, regardless of the current filter.')
        saved_dl,all_dl=st.columns(2)
        with saved_dl: st.download_button('Download saved',export_html(plan,resources,st.session_state.saved_programs),file_name='student-resource-saved.html',mime='text/html',on_click='ignore',disabled=not st.session_state.saved_programs,use_container_width=True)
        with all_dl: st.download_button('Download all',export_html(plan,resources),file_name='student-resource-all.html',mime='text/html',on_click='ignore',use_container_width=True)
        st.caption('Open the printable file and choose Print / save as PDF. No account is required.')
    elif not st.session_state.get('nemotron_error'):
        st.html(empty_state())
    else:
        st.caption('Your answers are still available. Try Find Recommendations again; recently retrieved sources will be reused when available.')

st.html(footer())
if st.session_state.pop('scroll_page_to_top',False):
    st.html("<script>requestAnimationFrame(()=>document.querySelector('[data-testid=stMain]')?.scrollTo({top:0,behavior:'instant'}));</script>",unsafe_allow_javascript=True)
