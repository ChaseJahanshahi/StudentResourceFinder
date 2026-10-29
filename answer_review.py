"""Readable answer review, with plain labels and safe colored values."""
from html import escape

QUESTIONS = [
    ('age', 'How old are you?'),
    ('california', 'Do you live in California?'), ('college', 'Which college do you attend?'),
    ('location', 'What city or county do you live in?'), ('zip_code', 'What is your ZIP code?'),
    ('college_type', 'What type of college do you attend?'), ('degree', 'What degree are you pursuing?'),
    ('enrollment', 'What is your enrollment level?'),
    ('needs', 'What support would help?'), ('housing', 'What is your housing situation?'),
    ('insurance', 'Do you have health insurance?'), ('dependents', 'Do you support children or other dependents?'),
    ('meal_plan', 'Does a meal plan cover more than half your meals?'),
    ('food_household_size', 'How many people buy and prepare food together?'),
    ('food_with_parents', 'Do you live with a parent?'),
    ('work_hours', 'How many paid hours do you work each week?'),
    ('work_study', 'Are you approved for work-study and expecting to work?'),
    ('student_exemption', 'Has a navigator confirmed another CalFresh student exemption?'),
    ('income', 'What is your monthly income before taxes?'),
    ('aid_application', 'What is your financial-aid application status?'),
]


def answer_review(profile):
    rows = []
    for key, question in QUESTIONS:
        if key not in profile:
            continue
        value = profile[key]
        kind = 'answered'
        if value is None:
            value, kind = 'Not provided / not asked', 'skipped'
        elif value == '' or value == []:
            value, kind = 'Not provided', 'skipped'
        elif isinstance(value, str) and value.lower().strip() in ('not sure', 'unsure', 'unknown'):
            kind = 'unsure'
        elif key == 'income':
            value = f'${value:,.0f} / month'
        values = value if isinstance(value, list) else [value]
        answers = ''.join(f'<span class="sr-answer sr-{kind}">{escape(str(item))}</span>' for item in values)
        rows.append(f'<div class="sr-answer-row"><dt>{escape(question)}</dt><dd>{answers}</dd></div>')
    return '''<style>
.sr-review {max-width:1000px;background:linear-gradient(140deg,#18161c,#120f15);border:1px solid #ffffff12;border-radius:22px;padding:12px 28px;margin:8px 0 24px;}
.sr-answer-row {display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:20px;padding:18px 0;border-bottom:1px solid #8883;align-items:start;}
.sr-answer-row:last-child {border-bottom:0;}
.sr-answer-row dt {font-size:.92rem;line-height:1.6;opacity:.85;}
.sr-answer-row dd {margin:0;display:flex;flex-wrap:wrap;gap:8px;}
.sr-answer {font-size:.95rem;font-weight:650;line-height:1.5;padding:4px 11px;border-radius:8px;overflow-wrap:anywhere;}
.sr-answered {color:#f3b476;background:#e8871a15;}
.sr-unsure {color:#ff7777;background:#e0444420;}
.sr-skipped {color:#9ba3af;background:#8881;font-weight:400;}
@media(max-width:650px){.sr-answer-row{grid-template-columns:1fr;gap:8px;}.sr-review{padding:8px 20px;}}
</style><dl class="sr-review" aria-label="Your questionnaire answers">''' + ''.join(rows) + '</dl>'
