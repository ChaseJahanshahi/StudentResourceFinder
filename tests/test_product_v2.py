import json
from pathlib import Path
import tempfile
import unittest
from profile_state import blank_profile, normalized_profile, section_errors, follow_up_candidates
from results_tools import contact_draft, export_html, export_text, mandatory_checks
from usage_control import reserve_generation, UsageLimit, record_metrics
from nebius_ai import parse_plan, plan_schema
from nebius_ai import NebiusError

class ProductTests(unittest.TestCase):
    def test_blank_defaults_do_not_inherit_personal_information(self):
        profile=blank_profile()
        self.assertEqual(profile['needs'],[]); self.assertIsNone(profile['income']); self.assertIsNone(profile['age'])
        self.assertNotIn('name',profile); self.assertNotIn('first_generation',profile)
        self.assertNotEqual(blank_profile(True)['needs'],[])

    def test_income_and_zip_completion_validation(self):
        p=blank_profile(); p.update(zip_code='abc',income_known=True,income=None)
        self.assertTrue(section_errors(p,1)); self.assertTrue(section_errors(p,2)); self.assertTrue(section_errors(p,3))
        p.update(zip_code='90024',income=0,needs=['Food'])
        self.assertFalse(section_errors(p,1)+section_errors(p,2)+section_errors(p,3))

    def test_hidden_answers_normalized_and_followup_is_relevant(self):
        p=blank_profile(True);p.update(housing='Campus housing',meal_plan='Yes',food_household_size=4)
        n=normalized_profile(p); self.assertIsNone(n['food_household_size'])
        fields=[c['field'] for c in follow_up_candidates(n)]
        self.assertIn('insurance',fields);self.assertNotIn('meal_plan',fields)

    def test_export_escaping_and_email_has_no_private_profile(self):
        r=dict(id='one',name='<script>alert(1)</script>',description='Support',source_url='https://ucla.edu/',apply_url='https://ucla.edu/',categories=['Food'],checks=['Must be enrolled.'])
        item=dict(program_id='one',why='<img src=x>',action='Contact the campus office.',missing_requirements=['Confirm enrollment'])
        plan=dict(recommendations=[item])
        html=export_html(plan,{'one':r})
        self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
        self.assertIn('Must be enrolled.',export_text(plan,{'one':r}))
        self.assertIn('[Your name]',contact_draft(r,item))

    def test_saved_and_all_exports_have_separate_scopes(self):
        records={key:dict(id=key,name=name,description='Support',source_url='https://ucla.edu/',apply_url='https://ucla.edu/',checks=[],categories=[]) for key,name in [('one','First program'),('two','Second program')]}
        plan=dict(recommendations=[dict(program_id=key,why='Relevant support.',action='Contact the provider.') for key in records])
        saved=export_html(plan,records,['one'])
        self.assertIn('First program',saved);self.assertNotIn('Second program',saved)
        all_programs=export_html(plan,records)
        self.assertIn('First program',all_programs);self.assertIn('Second program',all_programs)

    def test_durable_global_limit_and_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'usage.db'; settings={'SRF_GLOBAL_DAILY_LIMIT':2,'SRF_COOLDOWN_SECONDS':20}
            reserve_generation('a',settings,db,100)
            with self.assertRaises(UsageLimit): reserve_generation('a',settings,db,105)
            reserve_generation('a',settings,db,121)
            with self.assertRaises(UsageLimit): reserve_generation('new-session',settings,db,145)

    def test_metrics_allowlist_drops_sensitive_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'metrics.jsonl'
            record_metrics(dict(seconds=2,name='PRIVATE',income=200,query='PRIVATE',total_tokens=123),path)
            text=path.read_text();self.assertNotIn('PRIVATE',text);self.assertNotIn('income',text)

    def test_eight_cards_and_conflict_downgrade(self):
        records=[dict(id=str(n),status='Potential match') for n in range(9)]
        plan=dict(summary='Explore these programs.',follow_up_question='',recommendations=[dict(program_id=str(n),why='Relevant.',action='Contact provider.',match_level='strong') for n in range(8)])
        records[0].update(evidence_kind='search_excerpt')
        result=parse_plan(json.dumps(plan),records)
        self.assertEqual(len(result['recommendations']),8)
        self.assertEqual(result['recommendations'][0]['match_level'],'possible')
        self.assertEqual(plan_schema(records)['properties']['recommendations']['maxItems'],8)

    def test_rejects_financial_amounts_and_inferred_living_alone(self):
        for why in ('You may get $291 monthly.', 'You live alone and need groceries.', 'You are a California resident.'):
            plan=dict(summary='Explore support.',follow_up_question='',recommendations=[dict(program_id='one',why=why,action='Contact provider.')])
            result=parse_plan(json.dumps(plan),[dict(id='one')])
            self.assertNotEqual(result['recommendations'][0]['why'],why)
            self.assertNotIn('$291',result['recommendations'][0]['why'])
            self.assertNotIn('live alone',result['recommendations'][0]['why'])
