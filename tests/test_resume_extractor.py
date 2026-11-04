import unittest

from backend.document_converter import normalize_text
from backend.resume_extractor import extract_contact, extract_sections


class ResumeExtractionTests(unittest.TestCase):
    def test_extracts_core_skills_and_additional_resume_sections(self) -> None:
        markdown = """Professional Summary
Summary text
Core Skills
Python, LangChain, FastAPI
Flagship Project
Project details
Additional Projects
More project details
Research Experience
Research details
Achievements
Achievement details"""

        sections = extract_sections(markdown)

        self.assertEqual(sections["summary"], "Summary text")
        self.assertEqual(sections["skills"], "Python, LangChain, FastAPI")
        self.assertEqual(
            sections["projects"], "Project details\nMore project details"
        )
        self.assertNotIn("research", sections)
        self.assertNotIn("achievements", sections)

    def test_extracts_bare_professional_profile_urls_without_email_domains(
        self,
    ) -> None:
        contact = extract_contact(
            "ritik@example.com | linkedin.com/in/ritik | "
            "github.com/Ritik1907 | Next.js | Node.js"
        )

        self.assertEqual(contact.emails, ["ritik@example.com"])
        self.assertEqual(
            contact.urls,
            ["linkedin.com/in/ritik", "github.com/Ritik1907"],
        )

    def test_normalizes_pdf_page_breaks_and_wrapped_words(self) -> None:
        text = normalize_text("in-\n\ncluding content\fNext page")
        self.assertEqual(text, "including content\nNext page")
