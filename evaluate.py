"""Synthetic scenario evaluation. Offline by default; --live makes bounded paid calls."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
import tomllib

from evidence import deduplicate, source_badges, campus_scope
from matching import match_programs
from nebius_ai import get_config, generate_plan
from profile_state import blank_profile, normalized_profile
from resource_search import discover_resources, get_search_key
from usage_control import estimate_nebius_cost

def scenarios():
    base=blank_profile(True)
    cases=[]
    for label,changes in [
        ('ucla_unstable_housing',{}),
        ('uci_on_campus_meals',dict(college='University of California, Irvine',college_choice='University of California, Irvine',location='Irvine',zip_code='92697',housing='Campus housing',meal_plan='Yes')),
        ('private_student_unknown_exemption',dict(college='',college_choice='',college_type='Private / other',work_hours=5,work_study='Not sure',student_exemption='Not sure')),
        ('graduate_financial_aid',dict(degree='Graduate',needs=['Financial Aid'])),
        ('out_of_state_unknowns',dict(college='',college_choice='',california='No',location='',zip_code='',age=None,enrollment='Not sure',housing='Prefer not to say',income_known=False)),
        ('community_college_student_parent',dict(college='',college_choice='',college_type='California community college',needs=['Food','Childcare','Financial Aid'],dependents='Yes')),
    ]:
        draft=deepcopy(base);draft.update(changes)
        cases.append((label,normalized_profile(draft)))
    return cases

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='Uses credits: at most ten searches, one extraction, and two Nemotron calls with fictional answers.')
    parser.add_argument('--secrets',type=Path,default=Path(__file__).parent/'.streamlit'/'secrets.toml')
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'verification'/'evaluation.json')
    args=parser.parse_args()
    report={'mode':'live' if args.live else 'offline','cases':[], 'limitations':['Structural checks do not establish eligibility or prove every generated statement. Source review remains necessary.']}
    for label,profile in scenarios():
        matches=match_programs(profile)
        ids=[r['id'] for r in matches]
        report['cases'].append(dict(case=label,candidates=len(ids),candidate_ids=ids,
                                   needs=profile['needs'],conflicts=[r['id'] for r in matches if 'needs review' in r['status'].lower()],
                                   unknown_fields=sum(v is None or v=='Not sure' for v in profile.values())))
    assert 'promise_grant' not in report['cases'][0]['candidate_ids']
    assert 'promise_grant' in report['cases'][-1]['candidate_ids']
    assert 'calfresh' in report['cases'][1]['conflicts']
    assert 'pell_grant' in report['cases'][3]['conflicts']
    if args.live:
        settings=tomllib.loads(args.secrets.read_text(encoding='utf-8'))
        config=get_config(settings)
        profile=scenarios()[0][1]
        started=time.monotonic()
        print('Retrieving sources for the fictional UCLA example...',flush=True)
        resources,search=discover_resources(profile,get_search_key(settings))
        all_resources=deduplicate(resources+match_programs(profile))
        generation_profile=dict(profile,_search_target={k:profile[k] for k in ('college','location','zip_code')})
        print('Generating a source-grounded plan with Nemotron...',flush=True)
        result=generate_plan(generation_profile,all_resources,config)
        resource_map={r['id']:r for r in all_resources}
        selected=result['plan']['recommendations']
        report['live']=dict(seconds=round(time.monotonic()-started,2),search_requests=search['search_requests'],
                            extraction_requests=search['extraction_requests'],tavily_credits=search['tavily_credits'],
                            extracted_pages=search['extracted_pages'],failed_pages=search['failed_pages'],
                            rejected_campus=search['rejected_campus'],duplicate_pages=search['duplicate_pages'],
                            recommendations=len(selected),unknown_program_ids=0,
                            wrong_campus=sum(campus_scope(resource_map[r['program_id']],profile)=='different_campus' for r in selected),
                            categories=sorted({c for r in selected for c in source_badges(resource_map[r['program_id']])[1]}),
                            total_tokens=result.get('total_tokens'),estimated_nebius_usd=estimate_nebius_cost(result,settings),
                            notices=search['notices'])
        # Preserve only synthetic test artifacts, not any real user's questionnaire.
        args.output.parent.mkdir(parents=True,exist_ok=True)
        (args.output.parent/'synthetic_plan.json').write_text(json.dumps(dict(result=result,resources=resource_map),indent=2),encoding='utf-8')
        changed=dict(profile,insurance='No')
        print('Updating the fictional insurance answer, reusing sources...',flush=True)
        updated=generate_plan(dict(changed,_search_target=generation_profile['_search_target']),deduplicate(resources+match_programs(changed)),config)
        report['live']['refinement']=dict(total_tokens=updated.get('total_tokens'),new_search_requests=0,
                                        estimated_nebius_usd=estimate_nebius_cost(updated,settings),
                                        recommendations=len(updated['plan']['recommendations']),
                                        output_changed=updated['plan']!=result['plan'])
        print('Live source discovery and refinement completed.',flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
