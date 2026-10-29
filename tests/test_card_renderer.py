import importlib
import unittest
from unittest.mock import patch

import card_renderer


class RendererTests(unittest.TestCase):
    def test_reload_legacy_two_argument_renderer_before_passing_saved_state(self):
        resources={'one':dict(id='one',name='Food support',description='Food support.',categories=['Food'],
                              source_url='https://ucla.edu/',apply_url='https://ucla.edu/',checks=[])}
        plan=dict(recommendations=[dict(program_id='one',why='Food help.',action='Contact the provider.')])
        legacy=lambda plan, resources: 'old renderer'
        with patch.object(card_renderer._cards,'recommendation_grid',legacy), patch('card_renderer.importlib.reload',wraps=importlib.reload) as reload:
            html=card_renderer.render_cards(plan,resources,['one'])
            reload.assert_called_once_with(card_renderer._cards)
            self.assertIn('class="bb-card bb-saved"',html)
            self.assertIn('> Saved</span>',html)

    def test_current_renderer_does_not_reload_on_normal_reruns(self):
        with patch('card_renderer.importlib.reload') as reload:
            card_renderer.render_cards(dict(recommendations=[]),{})
            reload.assert_not_called()
