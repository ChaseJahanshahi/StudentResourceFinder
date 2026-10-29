"""Explainable resource discovery. This is not an eligibility determination."""

import json
import re
from pathlib import Path
from campuses import resolve_campus


def load_programs():
    with Path(__file__).with_name("programs.json").open(encoding="utf-8") as file:
        return json.load(file)


def validate_profile(profile):
    errors = []
    if not profile["needs"]:
        errors.append("Select at least one kind of assistance.")
    if profile["zip_code"] and not re.fullmatch(r"[0-9]{5}", profile["zip_code"]):
        errors.append("Enter a five-digit ZIP code, or leave it blank.")
    return errors


def match_programs(profile, programs=None):
    """Return relevant resources with reasons, unresolved checks, and priority.

    No income thresholds are hard-coded: program households, deductions, assets,
    immigration rules, and academic-year limits need an official assessment.
    Unknown answers never imply that a student is ineligible.
    """
    programs = load_programs() if programs is None else programs
    results = []
    for program in programs:
        overlap = set(profile["needs"]) & set(program["categories"])
        if not overlap:
            continue
        reasons = ["You requested help with " + ", ".join(sorted(overlap)) + "."]
        checks = []
        status = "Potential match"
        priority = 1
        pid = program['id']
        if profile["california"] == "No" and pid != 'pell_grant':
            status = "California location needs review"
            checks.append("This directory covers California. Ask the provider whether your residence or campus qualifies; consider your home state's resources too.")
            priority = 3
        elif profile["california"] == "Not sure" and pid != 'pell_grant':
            checks.append("Confirm California residence or attendance requirements with the provider.")

        if pid == "calfresh":
            checks.append("The county must review current income limits, deductions, household composition, and citizenship or eligible immigration status. This app does not assess those rules.")
            if profile["food_household_size"] is not None:
                reasons.append(f"You reported {profile['food_household_size']} people in your food household.")
            if profile["food_with_parents"] == "Yes" and profile.get("age") is not None and profile["age"] < 22:
                checks.append("Living with a parent while under 22 can require including parents in the CalFresh household, even if food is bought separately.")
            if profile["meal_plan"] == "Yes" and profile["housing"] == "Campus housing":
                status = "Meal-plan rule needs review"
                priority = 2
                checks.append("An on-campus meal plan supplying more than half your meals can prevent CalFresh eligibility. Ask the county to review your plan.")
            elif profile["meal_plan"] == "Not sure":
                checks.append("Ask your campus how many meals your meal plan covers.")
            student_rule = profile.get("age") is not None and 18 <= profile["age"] <= 49 and profile["enrollment"] in ("Half-time", "Full-time")
            campus_meals = profile["meal_plan"] == "Yes" and profile["housing"] == "Campus housing"
            if student_rule and not campus_meals:
                public_degree = profile["college_type"] in ("California community college", "CSU", "UC") and profile["degree"] in ("Associate", "Bachelor's")
                if public_degree:
                    reasons.append("Your reported public associate/bachelor's program fits the LPIE student-exemption pathway in the reviewed June 2026 guidance.")
                elif (profile["work_hours"] or 0) >= 20:
                    reasons.append("Your reported work hours suggest a student-exemption pathway for the county to verify.")
                elif profile["work_study"] == "Yes" or profile["student_exemption"] == "Yes":
                    reasons.append("You reported a possible student exemption; a navigator should verify it.")
                else:
                    checks.append("At least half-time students ages 18–49 generally need a student exemption. Ask a navigator about approved programs, work-study, work, caregiving, or other exemptions.")
                    if priority < 2:
                        priority = 2
                        status = "Student exemption needs review"
            elif profile["enrollment"] == "Not sure" or profile.get("age") is None:
                checks.append("Confirm age and enrollment level to determine whether the special student rules apply.")
        elif pid == "medi_cal":
            checks.append("DHCS or your county must assess your coverage household, income, age, immigration rules, and current enrollment restrictions.")
            if profile["insurance"] == "No":
                reasons.append("You reported having no health insurance.")
            elif profile["insurance"] == "Yes":
                checks.append("Existing coverage does not by itself establish eligibility or ineligibility; ask about coordination of coverage.")
        elif pid == "cal_grant":
            checks.append("Confirm California residency or qualifying exemption, eligible program, GPA, financial need, application deadlines, and remaining eligibility.")
            if profile["degree"] == "Graduate":
                status = "Degree eligibility needs review"
                priority = max(priority, 2)
                checks.append("General graduate study is usually outside Cal Grant coverage; certain teacher credential pathways have separate rules.")
        elif pid == "promise_grant":
            if profile["college_type"] not in ("California community college", "Not sure"):
                continue
            reasons.append("You selected a California community college or are still confirming your college type.")
            checks.append("Your college must verify enrollment, California residency or qualifying exemption, financial eligibility, and academic requirements.")
        elif pid == "pell_grant":
            checks.append("Confirm federal student-aid eligibility, financial need, degree history, satisfactory academic progress, and lifetime grant usage.")
            if profile["degree"] in ("Graduate", "Teacher credential"):
                status = "Degree eligibility needs review"
                priority = max(priority, 2)
                checks.append("Graduate students generally do not receive Pell Grants. Some postbaccalaureate teacher certification programs have an exception.")
        elif pid == "campus_basic_needs":
            campus = resolve_campus(profile.get('college', ''))
            if campus:
                program = {**program, 'name': campus['short']+' student-support referral',
                           'description': 'Contact your campus student services to ask which basic-needs programs are available.',
                           'source_url': 'https://'+campus['domain']+'/', 'apply_url': 'https://'+campus['domain']+'/',
                           'reviewed_on': None, 'resource_kind':'referral', 'provider_label':campus['short']}
            if profile["college_type"] == "Private / other":
                checks.append("The source covers California public colleges. Ask your own campus whether equivalent services exist.")
            if profile["housing"] in ("Temporary / staying with others", "Without stable housing"):
                reasons.append("You reported housing instability; contact student support promptly for available referrals.")
                if profile["california"] != "No":
                    priority = 0
            checks.append("This is a campus referral, not a guaranteed grant or housing placement. Confirm local services, funding, and enrollment requirements.")

        if pid in ("cal_grant", "promise_grant", "pell_grant"):
            if profile["aid_application"] in ("Not started", "Not sure"):
                checks.append("Ask financial aid which application to complete: FAFSA or California Dream Act. They are different eligibility pathways.")
            else:
                reasons.append("You have started or completed a student-aid application; check its status with financial aid.")
        if pid in ("calfresh", "medi_cal", "cal_grant", "promise_grant", "pell_grant"):
            checks.append("Reported income is context only. This app does not calculate financial eligibility or benefit amounts.")
        results.append({**program, "resource_kind":program.get('resource_kind', 'referral' if pid == 'campus_basic_needs' else 'program'),
                        "source_kind":"curated_record", "status": status, "reasons": reasons, "checks": checks, "priority": priority})
    return sorted(results, key=lambda item: (item["priority"], item["name"]))
