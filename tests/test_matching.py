import unittest

from matching import load_programs, match_programs, validate_profile


def student(**changes):
    profile = dict(age=20, california="Yes", needs=["Food", "Financial Aid"],
                   zip_code="", food_household_size=1, food_with_parents="No",
                   housing="Renting / own home", meal_plan="No",
                   enrollment="Full-time", college_type="UC", degree="Bachelor's",
                   work_hours=0, work_study="No", student_exemption="No",
                   insurance="No", aid_application="Not started")
    profile.update(changes)
    return profile


class MatchingTests(unittest.TestCase):
    def result(self, profile, program="calfresh"):
        return next(item for item in match_programs(profile) if item["id"] == program)

    def test_public_degree_student_pathway(self):
        result = self.result(student())
        self.assertEqual(result["status"], "Potential match")
        self.assertTrue(any("LPIE" in reason for reason in result["reasons"]))

    def test_private_student_work_boundary(self):
        for hours, expected in [(19, "Student exemption needs review"), (20, "Potential match")]:
            with self.subTest(hours=hours):
                result = self.result(student(college_type="Private / other", work_hours=hours))
                self.assertEqual(result["status"], expected)

    def test_student_age_and_enrollment_boundaries(self):
        for age, enrollment in [(17, "Full-time"), (50, "Full-time"), (20, "Less than half-time")]:
            with self.subTest(age=age, enrollment=enrollment):
                result = self.result(student(age=age, enrollment=enrollment, college_type="Private / other"))
                self.assertEqual(result["status"], "Potential match")

    def test_on_campus_meals_need_review(self):
        result = self.result(student(housing="Campus housing", meal_plan="Yes"))
        self.assertEqual(result["status"], "Meal-plan rule needs review")
        result = self.result(student(housing="Renting / own home", meal_plan="Yes"))
        self.assertNotEqual(result["status"], "Meal-plan rule needs review")

    def test_under_22_parent_household_flag(self):
        result = self.result(student(food_with_parents="Yes"))
        self.assertTrue(any("parents" in check for check in result["checks"]))

    def test_promise_only_community_college_or_unknown(self):
        self.assertNotIn("promise_grant", [r["id"] for r in match_programs(student())])
        self.assertIn("promise_grant", [r["id"] for r in match_programs(student(college_type="California community college"))])

    def test_unknown_answers_preserve_resources(self):
        results = match_programs(student(california="Not sure", college_type="Not sure", degree="Not sure", enrollment="Not sure"))
        self.assertIn("calfresh", [r["id"] for r in results])

    def test_out_of_state_is_never_positive_match(self):
        results=match_programs(student(california='No'))
        self.assertTrue(all(r['status'] != 'Potential match' for r in results if r['id'] != 'pell_grant'))
        self.assertEqual(next(r['status'] for r in results if r['id']=='pell_grant'),'Potential match')

    def test_housing_instability_prioritizes_support(self):
        results = match_programs(student(housing="Without stable housing"))
        self.assertEqual(results[0]["id"], "campus_basic_needs")

    def test_graduate_aid_needs_review(self):
        for pid in ("cal_grant", "pell_grant"):
            self.assertEqual(self.result(student(degree="Graduate"), pid)["status"], "Degree eligibility needs review")

    def test_needs_filter_and_validation(self):
        results = match_programs(student(needs=["Housing"]))
        self.assertEqual([r["id"] for r in results], ["campus_basic_needs"])
        self.assertEqual(len(validate_profile(student(needs=[], zip_code="abc"))), 2)
        self.assertEqual(validate_profile(student(zip_code="90001")), [])

    def test_directory_integrity(self):
        programs = load_programs()
        self.assertEqual(len({p["id"] for p in programs}), len(programs))
        for program in programs:
            self.assertTrue(program["source_url"].startswith("https://"))
            self.assertTrue(program["apply_url"].startswith("https://"))
            self.assertEqual(program["reviewed_on"], "2026-10-28")


if __name__ == "__main__":
    unittest.main()
