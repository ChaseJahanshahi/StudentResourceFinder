import unittest
from unittest.mock import patch
from resource_search import build_queries, discover_resources, official_url, SearchError
from evidence import source_badges, topics_in, deduplicate, campus_scope
from campuses import resolve_campus

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.profile=dict(college='UCLA',location='Irvine',zip_code='92606',california='Yes',needs=['Food','Housing'],name='PRIVATE',income=123456)

    def test_campus_resolution_and_separate_home_queries(self):
        queries=build_queries(self.profile)
        self.assertEqual(len(queries),4)
        self.assertIn('site:ucla.edu',queries[0]); self.assertIn('Los Angeles',queries[0])
        self.assertIn('Irvine 92606',queries[1]); self.assertNotIn('Irvine',queries[0])
        self.assertTrue(all('123456' not in q and 'PRIVATE' not in q for q in queries))
        self.assertEqual(resolve_campus('uci')['domain'],'uci.edu')

    def test_no_queries_without_target_and_bounded_budget(self):
        self.assertEqual(build_queries(dict(needs=['Food'])),[])
        self.assertLessEqual(len(build_queries(dict(self.profile,needs=['Food','Housing','Financial Aid','Childcare','Healthcare']))),10)

    def test_allowlist_is_bounded(self):
        for url in ('https://basicneeds.ucla.edu/','https://www.cdss.ca.gov/','https://211.org/','https://www.feedingamerica.org/'):
            self.assertTrue(official_url(url))
        for url in ('https://random.org/','https://211.org.evil.com/','http://ucla.edu/','https://u:p@ucla.edu/','https://127.0.0.1/','https://ucla.edu:8080/'):
            self.assertFalse(official_url(url))

    def test_word_boundaries_and_separate_badges(self):
        self.assertNotIn('Housing',topics_in('Resources for student parents'))
        self.assertEqual(source_badges(dict(source_url='https://basicneeds.ucla.edu/food',source_kind='search_result',name='Food pantry',description='Free groceries',categories=['Housing'])),('UCLA',['Food']))

    def test_program_dedup_preserves_curated_checks(self):
        curated=dict(id='calfresh',name='CalFresh',source_url='https://cdss.ca.gov/calfresh',checks=['Meal restriction'],source_kind='curated_record')
        web=dict(id='web',name='CalFresh eligibility',source_url='https://ucla.edu/calfresh',source_kind='search_result')
        result=deduplicate([web,curated])
        self.assertEqual(len(result),1); self.assertEqual(result[0]['checks'],['Meal restriction'])
        applying=dict(id='apply',name='Applying | Basic Needs',description='CalFresh student application instructions',source_url='https://basicneeds.ucla.edu/applying',source_kind='search_result')
        self.assertEqual(len(deduplicate([curated,applying])),1)

    @patch('resource_search._extract')
    @patch('resource_search._search')
    def test_campus_rejection_extract_failure_and_honest_dates(self,search,extract):
        search.return_value={'results':[
            dict(url='https://basicneeds.uci.edu/food',title='Food pantry',content='Food for UCI.'),
            dict(url='https://basicneeds.ucla.edu/food',title='Food pantry',content='Food support for UCLA students.'),
            dict(url='https://basicneeds.ucla.edu/housing',title='Housing program',content='Housing help for students.'),
        ],'usage':{'credits':1}}
        extract.return_value={'results':[dict(url='https://basicneeds.ucla.edu/food',raw_content='Food pantry\nEligibility: currently enrolled UCLA students.\nApply through the campus office.')], 'failed_results':[dict(url='https://basicneeds.ucla.edu/housing')],'usage':{'credits':1}}
        resources,report=discover_resources(self.profile,'fake')
        self.assertEqual(search.call_count,4); extract.assert_called_once()
        self.assertEqual(len(resources),2); self.assertGreater(report['rejected_campus'],0)
        self.assertEqual(report['extracted_pages'],1); self.assertEqual(report['failed_pages'],1)
        self.assertTrue(all(r['verified_at'] is None and r['reviewed_on'] is None for r in resources))
        self.assertIn('currently enrolled',resources[0]['description'])

    @patch('resource_search._extract',side_effect=SearchError('offline'))
    @patch('resource_search._search',return_value=[dict(url='https://ucla.edu/food',title='Food pantry',content='Food support')])
    def test_partial_evidence_survives_extraction_failure(self,search,extract):
        resources,report=discover_resources(self.profile,'fake')
        self.assertEqual(resources[0]['evidence_kind'],'search_excerpt')
        self.assertTrue(report['notices'])

    def test_missing_key_never_calls_search(self):
        with patch('resource_search._search') as search:
            with self.assertRaises(SearchError): discover_resources(self.profile,'')
            search.assert_not_called()
