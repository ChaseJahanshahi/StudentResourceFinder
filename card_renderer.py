"""Keep saved-card rendering compatible with a long-running Streamlit process."""
import importlib
import inspect
import recommendation_cards as _cards


def render_cards(plan, resources, saved_ids=()):
    # Streamlit may rerun app.py while another session still has the old module
    # cached. Reload only that obsolete renderer, not the app or its session.
    if 'saved_ids' not in inspect.signature(_cards.recommendation_grid).parameters:
        importlib.reload(_cards)
    return _cards.recommendation_grid(plan, resources, saved_ids=saved_ids)
