"""Answer normalization and section completion, separate from UI widgets."""
from copy import deepcopy
import hashlib
import json
import re
from campuses import resolve_campus

DEFAULTS = dict(age=None, california='Not sure', college='', college_choice='', location='', zip_code='',
                college_type='Not sure', degree='Not sure', enrollment='Not sure', needs=[],
                housing='Prefer not to say', insurance='Not sure', dependents='Prefer not to say',
                meal_plan='Not sure', food_household_size=None, food_with_parents='Not sure',
                work_hours=None, work_study='Not sure', student_exemption='Not sure',
                income_known=False, income=None, aid_application='Not sure')
EXAMPLE = dict(DEFAULTS, age=21, california='Yes', college='University of California, Los Angeles',
               college_choice='University of California, Los Angeles', location='Los Angeles', zip_code='90024',
               college_type='UC', degree="Bachelor's", enrollment='Full-time', needs=['Food','Housing','Financial Aid','Healthcare'],
               housing='Temporary / staying with others', meal_plan='No', food_household_size=1,
               food_with_parents='No', income_known=True, income=350, aid_application='Not started')

def blank_profile(example=False):
    return deepcopy(EXAMPLE if example else DEFAULTS)

def section_errors(draft, step):
    errors = []
    if step == 1:
        zipcode = draft.get('zip_code','').strip()
        if zipcode and not re.fullmatch(r'[0-9]{5}', zipcode):
            errors.append('Enter a five-digit home ZIP code, or leave it blank.')
        if draft.get('age') is not None and not 16 <= draft['age'] <= 100:
            errors.append('Enter an age between 16 and 100, or leave it blank.')
    if step == 2 and not draft.get('needs'):
        errors.append('Select at least one kind of support.')
    if step == 3 and draft.get('income_known') and draft.get('income') is None:
        errors.append('Enter your monthly income, including 0, or uncheck the estimate box.')
    return errors

def student_work_needed(draft):
    age = draft.get('age')
    public_degree = draft.get('college_type') in ('California community college','CSU','UC') and draft.get('degree') in ('Associate',"Bachelor's")
    return ('Food' in draft.get('needs',[]) and not (draft.get('housing') == 'Campus housing' and draft.get('meal_plan') == 'Yes')
            and age is not None and 18 <= age <= 49 and draft.get('enrollment') in ('Half-time','Full-time') and not public_degree)

def normalized_profile(draft):
    profile = {key: deepcopy(draft.get(key, default)) for key, default in DEFAULTS.items() if key not in ('income_known','college_choice')}
    for key in ('college','zip_code','location'):
        profile[key] = str(profile.get(key) or '').strip()
    campus = resolve_campus(profile['college'])
    if campus:
        profile['college'] = campus['name']
    if not draft.get('income_known'):
        profile['income'] = None
    if 'Healthcare' not in profile['needs']: profile['insurance'] = 'Not sure'
    if not {'Childcare','Housing'} & set(profile['needs']): profile['dependents'] = 'Prefer not to say'
    if 'Financial Aid' not in profile['needs']: profile['aid_application'] = 'Not sure'
    food = 'Food' in profile['needs']
    campus_meals = profile['housing'] == 'Campus housing' and profile['meal_plan'] == 'Yes'
    if not food or campus_meals: profile['food_household_size'] = None
    if not food or campus_meals or profile['housing'] == 'Campus housing': profile['food_with_parents'] = 'Not sure'
    if not student_work_needed(profile):
        profile.update(work_hours=None, work_study='Not sure', student_exemption='Not sure')
    elif (profile.get('work_hours') or 0) >= 20:
        profile.update(work_study='Not sure', student_exemption='Not sure')
    elif profile['work_study'] == 'Yes': profile['student_exemption'] = 'Not sure'
    if not food: profile['meal_plan'] = 'Not sure'
    return profile

def fingerprint(profile):
    return hashlib.sha256(json.dumps(profile, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

FOLLOW_UPS = {
    'enrollment': ('What is your enrollment level?', ['Not sure','Less than half-time','Half-time','Full-time','Not currently enrolled']),
    'meal_plan': ('Does a college meal plan cover more than half your meals?', ['Not sure','Yes','No']),
    'insurance': ('Do you currently have health insurance?', ['Not sure','Yes','No','Prefer not to say']),
    'dependents': ('Do you support children or other dependents?', ['Prefer not to say','Yes','No']),
    'work_study': ('Are you approved for work-study and expecting to work?', ['Not sure','Yes','No']),
    'aid_application': ('What is your financial aid application status?', ['Not sure','Not started','FAFSA started / submitted','California Dream Act started / submitted']),
}

def follow_up_candidates(profile):
    keys = ['enrollment']
    if 'Food' in profile.get('needs',[]): keys += ['meal_plan']
    if 'Healthcare' in profile.get('needs',[]): keys += ['insurance']
    if {'Childcare','Housing'} & set(profile.get('needs',[])): keys += ['dependents']
    if student_work_needed(profile) and (profile.get('work_hours') or 0) < 20: keys += ['work_study']
    if 'Financial Aid' in profile.get('needs',[]): keys += ['aid_application']
    return [dict(field=key, question=FOLLOW_UPS[key][0]) for key in keys if profile.get(key) in (None,'Not sure','Prefer not to say','')]

def choose_follow_up(plan, profile):
    candidates = follow_up_candidates(profile)
    if not candidates: return None
    chosen = next((c for c in candidates if c['field'] == plan.get('follow_up_field')), candidates[0])
    return chosen
