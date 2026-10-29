"""Full app regression with mocked transports; never spends provider credits."""
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from streamlit.testing.v1 import AppTest
from nebius_ai import NebiusError

SEARCH=[dict(url='https://basicneeds.ucla.edu/pantry',title='UCLA Food Pantry',content='Food and groceries for enrolled UCLA students.'),
        dict(url='https://basicneeds.ucla.edu/emergency-housing',title='UCLA Emergency Housing Program',content='Housing help for enrolled students with unstable housing.')]
EXTRACT=dict(results=[dict(url=r['url'],raw_content=r['content']+'\nEligibility: currently enrolled students.\nContact the campus office to confirm current availability.') for r in SEARCH])

def model_response(config,path,payload=None):
    context=json.loads(payload['messages'][1]['content'])
    records=context['resources'][:8]
    field='insurance' if any(c['field']=='insurance' for c in context['clarification_candidates']) else (context['clarification_candidates'][0]['field'] if context['clarification_candidates'] else '')
    plan=dict(summary='Campus and community programs.',follow_up_field=field,
              follow_up_question='Knowing whether you already have insurance can improve healthcare recommendations.' if field else '',
              recommendations=[dict(program_id=r['id'],about='Student support to explore.',why='Matches your selected support needs.',
                                    action='Contact the listed office.',match_level='possible',missing_requirements=['Confirm current enrollment and availability.']) for r in records])
    return dict(id='mock',model=config.model,choices=[dict(finish_reason='stop',message=dict(content=json.dumps(plan)))],usage=dict(total_tokens=500,prompt_tokens=350,completion_tokens=150))

with patch.dict(os.environ,{'NEBIUS_API_KEY':'fake-key','TAVILY_API_KEY':'fake-search'}), \
     patch('nebius_ai._request',side_effect=model_response) as request, \
     patch('resource_search._search',return_value=SEARCH) as search, \
     patch('resource_search._extract',return_value=EXTRACT) as extract, \
     patch('usage_control.reserve_generation') as reserve, patch('usage_control.record_metrics'):
    at=AppTest.from_file(str(root/'app.py'),default_timeout=15).run()
    def clean():
        assert not at.exception,at.exception
    def click(label):
        next(b for b in at.button if b.label==label).click().run();clean()
    clean()
    assert at.session_state['questionnaire_draft']['age'] is None
    assert not any('first-generation' in w.label.lower() for w in at.selectbox)
    at.button(key='jump_step_3').click().run();clean()
    assert at.session_state['completed_steps']==[]
    at.button(key='jump_step_1').click().run();clean()
    click('Try an example')
    assert at.session_state['questionnaire_draft']['college'].endswith('Los Angeles')
    click('Next');assert at.session_state['completed_steps']==[1]
    click('Next');click('Review answers')
    request.assert_not_called();search.assert_not_called();extract.assert_not_called()
    click('Find Recommendations')
    assert request.call_count==1 and search.call_count==8 and extract.call_count==1
    assert len(at.session_state['nemotron_result']['plan']['recommendations'])>=6
    html=''.join(e.proto.body for e in at.get('html'))
    assert 'Start here' not in html
    assert not any(h.value=='One answer could improve your plan' for h in at.subheader)
    assert not any(b.label=='Update my recommendations' for b in at.button)
    assert 'Requirements to confirm' in html and 'Curated source' in html
    assert 'Possible match' not in html and 'Strong match' not in html and 'Limited match' not in html
    assert not any(p.proto.popover.label=='Source details & contact draft' for p in at.get('popover'))
    assert [b.proto.label for b in at.get('download_button')]==['Download saved','Download all']
    assert at.get('download_button')[0].proto.disabled
    count=request.call_count
    at.radio(key='category_filter').set_value('Food').run();clean()
    save=next(b for b in at.button if b.label=='Save')
    save.click().run();clean()
    assert len(at.session_state['saved_programs'])==1
    html=''.join(e.proto.body for e in at.get('html'))
    assert 'class="bb-card bb-saved"' in html and '> Saved</span>' in html
    assert not at.get('download_button')[0].proto.disabled
    saved_id=at.session_state['saved_programs'][0]
    at.button(key='save_'+saved_id).click().run();clean()
    assert not at.session_state['saved_programs']
    assert 'class="bb-card bb-saved"' not in ''.join(e.proto.body for e in at.get('html'))
    at.button(key='save_'+saved_id).click().run();clean()
    at.checkbox(key='saved_only').check().run();clean()
    assert request.call_count==count
    assert len(at.get('download_button'))==2
    old=at.session_state['nemotron_result']
    request.side_effect=NebiusError('Simulated timeout')
    click('Refresh recommendations')
    assert at.session_state['nemotron_result']==old
    assert at.session_state['nemotron_error']=='Simulated timeout'
    click('Edit finances')
    at.number_input(key='answer_income').set_value(700).run();clean()
    click('Review answers')
    assert any('previous answers' in info.value for info in at.info)
    assert at.session_state['result_profile']['income']==350
    assert at.session_state['resource_profile']['income']==700
    assert reserve.call_count==2
print('PASS: blank defaults, example profile, accurate completion, direct recommendation cards, filters, saving, downloads, failure recovery, and stale-plan editing. No live API calls.')
