import unittest
from backend.jd_parser import RequirementWeights, parse_job_description, append_explicit_skills
from backend.matching_engine import CandidateScore, RequirementScore, ScoringConfiguration
from backend.scoring_report import build_scoring_report, render_scoring_report


class SkillsWeightingAndReportingTests(unittest.TestCase):
    def test_explicit_skills_priority_and_weights(self):
        jd_text = "Looking for a Software Engineer to develop high-performance APIs."
        must_have = "Python, FastAPI, SQL"
        good_to_have = "Docker, AWS"

        weights = RequirementWeights(mandatory=3.0, preferred=1.0, unspecified=2.0)
        jd = parse_job_description(
            jd_text,
            weights=weights,
            must_have_skills=must_have,
            good_to_have_skills=good_to_have,
        )

        req_map = {r.text.casefold(): r for r in jd.requirements}

        self.assertIn("python", req_map)
        self.assertEqual(req_map["python"].priority, "mandatory")
        self.assertEqual(req_map["python"].weight, 3.0)

        self.assertIn("fastapi", req_map)
        self.assertEqual(req_map["fastapi"].priority, "mandatory")
        self.assertEqual(req_map["fastapi"].weight, 3.0)

        self.assertIn("docker", req_map)
        self.assertEqual(req_map["docker"].priority, "preferred")
        self.assertEqual(req_map["docker"].weight, 1.0)

        self.assertIn("aws", req_map)
        self.assertEqual(req_map["aws"].priority, "preferred")
        self.assertEqual(req_map["aws"].weight, 1.0)

        # Confirm 3x weight difference
        self.assertEqual(req_map["python"].weight / req_map["docker"].weight, 3.0)

    def test_scoring_report_table_columns_and_extreme_right_overall(self):
        jd_text = "Senior Python Developer. Experience: 3+ years."
        must_have = "Python, Pytest"
        good_to_have = "Kubernetes"

        weights = RequirementWeights(mandatory=3.0, preferred=1.0, unspecified=2.0)
        jd = parse_job_description(
            jd_text,
            weights=weights,
            must_have_skills=must_have,
            good_to_have_skills=good_to_have,
        )

        config = ScoringConfiguration()

        # Mock candidate score
        candidate = CandidateScore(
            source_filename="Alice_Resume.pdf",
            overall_score=86.5,
            total_experience_years=4.2,
            requirement_scores=[
                RequirementScore(
                    requirement_id="req-1",
                    requirement="Python",
                    category="skills",
                    weight=3.0,
                    priority="mandatory",
                    minimum_years=None,
                    candidate_experience_years=4.2,
                    relevant_experience_years=4.2,
                    match_score=90.0,
                    match_status="strong evidence",
                    supporting_evidence=[],
                    source_sections=["skills", "experience"],
                    missing_gaps=[],
                    uncertainties=[],
                    explanation="Direct match",
                ),
                RequirementScore(
                    requirement_id="req-2",
                    requirement="Kubernetes",
                    category="skills",
                    weight=1.0,
                    priority="preferred",
                    minimum_years=None,
                    candidate_experience_years=None,
                    relevant_experience_years=None,
                    match_score=70.0,
                    match_status="strong evidence",
                    supporting_evidence=[],
                    source_sections=["skills"],
                    missing_gaps=[],
                    uncertainties=[],
                    explanation="Direct match",
                ),
            ],
            matched_requirements=["Python", "Kubernetes"],
            partial_or_uncertain_requirements=[],
            no_evidence_requirements=[],
            extraction_warnings=[],
        )

        report = build_scoring_report(jd, [candidate], config)
        rendered = render_scoring_report(report)

        # Verify table header has Overall Score at extreme right and Total Experience in years
        expected_header = "| Rank | Candidate | Must-Have Skills (%) | Good-to-Have Skills (%) | Total Experience | Overall Score (%) |"
        self.assertIn(expected_header, rendered)

        # Verify Alice's row has total experience in years (no %) and overall score on right
        self.assertIn("Alice_Resume.pdf", rendered)
        self.assertIn("4.2 Years", rendered)
        self.assertIn("**86.5%**", rendered)


if __name__ == "__main__":
    unittest.main()
