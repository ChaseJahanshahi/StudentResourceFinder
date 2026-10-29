"""Explicit live smoke test with synthetic answers, not real student information."""
from pathlib import Path
import tomllib

from matching import match_programs
from nebius_ai import NebiusError, get_config, check_model_access, generate_plan


def main():
    secrets_path = Path(__file__).with_name('.streamlit') / 'secrets.toml'
    secrets = tomllib.loads(secrets_path.read_text(encoding='utf-8')) if secrets_path.exists() else {}
    config = get_config(secrets)
    # Synthetic example only. Running this script uses your Nebius credits.
    profile = dict(age=20, california='Yes', needs=['Food'], food_household_size=1,
                   food_with_parents='No', housing='Renting / own home', meal_plan='No',
                   enrollment='Full-time', college_type='UC', degree="Bachelor's",
                   work_hours=None, work_study='Not sure', student_exemption='Not sure',
                   insurance='Not sure', aid_application='Not sure', income=None)
    try:
        check_model_access(config)
        result = generate_plan(profile, match_programs(profile), config)
    except NebiusError as error:
        print('NOT VERIFIED: ' + str(error))
        return 1
    print('Live Nemotron inference verified through Nebius Token Factory.')
    print('Model: ' + result['model'])
    print('Completion ID: ' + result['completion_id'])
    print('Recommendations: ' + str(len(result['plan']['recommendations'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
