import json
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

from matching import match_programs
from nebius_ai import (NebiusConfig, NebiusError, build_messages, build_payload, generate_plan,
                       parse_plan, _request, check_model_access)


def example():
    return dict(name='PRIVATE_NAME', college='PRIVATE_COLLEGE', zip_code='99999',
                age=20, california='Yes', needs=['Food'], food_household_size=1,
                food_with_parents='No', housing='Campus housing', meal_plan='Yes',
                enrollment='Full-time', college_type='UC', degree="Bachelor's",
                work_hours=None, work_study='Not sure', student_exemption='Not sure',
                insurance='Not sure', aid_application='Not sure', income=100)


def answer():
    return {'summary': 'Explore campus food support and confirm current rules.',
            'recommendations': [{'program_id': 'campus_basic_needs',
                                 'why': 'You requested food support.',
                                 'action': 'Contact your campus basic-needs office.'}],
            'follow_up_question': ''}


class NebiusTests(unittest.TestCase):
    def setUp(self):
        self.profile = example()
        self.matches = match_programs(self.profile)
        self.config = NebiusConfig('test-secret-do-not-print')

    def test_context_excludes_identifiers_and_preserves_restrictions(self):
        payload = json.dumps(build_messages(self.profile, self.matches))
        for private in ('PRIVATE_NAME', 'PRIVATE_COLLEGE', '99999'):
            self.assertNotIn(private, payload)
        context = json.loads(build_messages(self.profile, self.matches)[1]['content'])
        calfresh = next(item for item in context['resources'] if item['id'] == 'calfresh')
        self.assertEqual(calfresh['status'], 'Meal-plan rule needs review')
        self.assertEqual(calfresh['checks'], next(item for item in self.matches if item['id'] == 'calfresh')['checks'])

    def test_valid_plan(self):
        self.assertEqual(parse_plan(json.dumps(answer()), self.matches), answer())

    def test_summary_income_and_bad_followup_do_not_discard_valid_cards(self):
        for summary, question, field in (
            ('You reported $200 monthly income.', None, None),
            ('', '', ''),
            ('<script>unsafe</script>', 'Visit https://bad.example', 'unsupported_field'),
            ('x'*1600, None, 'insurance'),
        ):
            plan=answer()
            plan.update(summary=summary,follow_up_question=question,follow_up_field=field)
            result=parse_plan(json.dumps(plan),self.matches)
            self.assertEqual(result['recommendations'],answer()['recommendations'])
            self.assertEqual(result['summary'],'')
            self.assertEqual(result['follow_up_question'],'')

    @patch('nebius_ai._request')
    def test_auxiliary_text_recovery_never_makes_a_paid_retry(self,request):
        plan=answer();plan.update(summary='Income: $200 per month.',follow_up_question=None)
        request.return_value={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(plan)}}]}
        result=generate_plan(self.profile,self.matches,self.config)
        self.assertTrue(result['plan']['recommendations'])
        request.assert_called_once()

    @patch('nebius_ai._request')
    def test_unsafe_or_overlong_card_prose_uses_source_guidance_without_retry(self,request):
        plan=answer();plan['recommendations'][0].update(why='You may receive $291.',action='x'*300,about='<script>bad</script>',missing_requirements=None)
        request.return_value={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(plan)}}]}
        result=generate_plan(self.profile,self.matches,self.config)
        item=result['plan']['recommendations'][0]
        self.assertNotIn('$291',item['why'])
        self.assertLessEqual(len(item['action']),200)
        self.assertNotIn('<script>',item['about'])
        self.assertEqual(result['validation_repairs'],4)
        request.assert_called_once()

    def test_request_enforces_card_schema_and_disables_unbounded_thinking(self):
        payload = build_payload(self.profile, self.matches, self.config)
        self.assertIs(payload['chat_template_kwargs']['enable_thinking'], False)
        response_format = payload['response_format']
        self.assertEqual(response_format['type'], 'json_schema')
        schema = response_format['json_schema']['schema']
        card = schema['properties']['recommendations']['items']
        self.assertEqual(set(card['properties']['program_id']['enum']), {r['id'] for r in self.matches})
        self.assertEqual(card['properties']['match_level']['enum'], ['strong', 'possible', 'limited'])
        self.assertIn('missing_requirements', card['required'])

    def test_card_fields_validate_without_relaxing_resource_checks(self):
        plan = answer()
        plan['recommendations'][0].update(about='Campus assistance.', match_level='possible', missing_requirements=['Confirm availability.'])
        self.assertEqual(parse_plan(json.dumps(plan), self.matches), plan)
        plan['recommendations'][0]['match_level'] = 'guaranteed'
        self.assertEqual(parse_plan(json.dumps(plan),self.matches)['recommendations'][0]['match_level'],'possible')

    def test_reject_unknown_program_duplicate_links_and_invalid_structure(self):
        invalid = []
        unknown = answer()
        unknown['recommendations'][0]['program_id'] = 'invented-grant'
        invalid.append(unknown)
        duplicate = answer()
        duplicate['recommendations'] *= 2
        invalid.append(duplicate)
        links = answer()
        links['recommendations'][0]['action'] = 'Visit https://bad.example'
        safe=parse_plan(json.dumps(links),self.matches)
        self.assertNotIn('https://bad.example',safe['recommendations'][0]['action'])
        invalid.extend([[], {'summary': 'incomplete'}])
        for plan in invalid:
            with self.subTest(plan=plan), self.assertRaises(NebiusError):
                parse_plan(json.dumps(plan), self.matches)

    def test_configuration_rejects_non_nebius_hosts_and_non_nvidia_models(self):
        for config in (NebiusConfig(''), NebiusConfig('key', model='other/model'),
                       NebiusConfig('key', base_url='https://evil.example/v1'),
                       NebiusConfig('key', base_url='https://api.tokenfactory.nebius.com.evil.example/v1')):
            with self.subTest(config=config.model), self.assertRaises(NebiusError):
                config.validate()

    @patch('nebius_ai.build_opener')
    def test_real_transport_contract_and_no_auto_retries(self, opener):
        response = MagicMock()
        response.read.return_value = b'{"data": []}'
        opener.return_value.open.return_value.__enter__.return_value = response
        _request(self.config, '/chat/completions', {'model': self.config.model})
        opener.return_value.open.assert_called_once()
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, self.config.base_url + '/chat/completions')
        self.assertEqual(request.get_header('Authorization'), 'Bearer ' + self.config.api_key)
        self.assertEqual(request.get_method(), 'POST')

    @patch('nebius_ai.build_opener')
    def test_provider_errors_do_not_expose_keys_or_response_bodies(self, opener):
        for code in (400, 401, 402, 403, 404, 429, 500):
            opener.return_value.open.side_effect = HTTPError('private', code, 'secret body', {}, None)
            with self.subTest(code=code), self.assertRaises(NebiusError) as raised:
                _request(self.config, '/models')
            self.assertNotIn(self.config.api_key, str(raised.exception))
            self.assertNotIn('secret body', str(raised.exception))
        opener.return_value.open.side_effect = URLError('secret body')
        with self.assertRaises(NebiusError):
            _request(self.config, '/models')

    @patch('nebius_ai._request')
    def test_live_result_metadata_and_bounded_request(self, request):
        request.return_value = {'id': 'completion-example', 'model': self.config.model,
                                'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(answer())}}],
                                'usage': {'total_tokens': 300}}
        result = generate_plan(self.profile, self.matches, self.config)
        self.assertEqual(result['completion_id'], 'completion-example')
        self.assertEqual(result['plan'], answer())
        request.assert_called_once()
        payload = request.call_args.args[2]
        self.assertEqual(payload['model'], self.config.model)
        self.assertEqual(payload['max_tokens'], 4096)
        self.assertIs(payload['stream'], False)

    @patch('nebius_ai._request')
    def test_truncated_output_not_presented_as_success(self, request):
        for reason in ('length', 'content_filter'):
            request.return_value = {'choices': [{'finish_reason': reason, 'message': {'content': json.dumps(answer())}}]}
            with self.subTest(reason=reason), self.assertRaises(NebiusError):
                generate_plan(self.profile, self.matches, self.config)

    @patch('nebius_ai._request')
    def test_model_access_requires_exact_id(self, request):
        request.return_value = {'data': [{'id': self.config.model}]}
        self.assertTrue(check_model_access(self.config))
        request.return_value = {'data': [{'id': 'other/model'}]}
        with self.assertRaises(NebiusError):
            check_model_access(self.config)


if __name__ == '__main__':
    unittest.main()
