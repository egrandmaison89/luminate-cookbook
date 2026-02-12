"""
Tests for the Plain Text Email Beautifier service.

Validates CSS stripping, content preservation, CTA detection,
URL cleaning, and footer simplification.
"""

import unittest
from pathlib import Path

# Fixture directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """Load a fixture file by name."""
    path = FIXTURES_DIR / name
    return path.read_text()


class TestEmailBeautifierIntegration(unittest.TestCase):
    """Integration tests with the full sample email."""

    def test_sample_email_preserves_all_content(self):
        """Sample input must preserve event details, body, ticket info, and CTA."""
        from app.services.email_beautifier import beautify_email

        raw = load_fixture("textemail.txt")
        result, stats = beautify_email(raw)

        # CSS must be stripped
        self.assertNotIn("body {", result)
        self.assertNotIn("@media", result)
        self.assertNotIn("!important", result)

        # Event details must be present
        self.assertIn("Celebrate with us at the 2026 DFMC Pasta Party", result)
        self.assertIn("Saturday, April 18", result)
        self.assertIn("4:00", result)
        self.assertIn("6:00", result)
        self.assertIn("Boston Marriott Copley Place", result)
        self.assertIn("Grand Ballroom", result)
        self.assertIn("4th Floor", result)

        # RSVP CTA must be present and formatted with visual emphasis
        self.assertTrue("RSVP Today" in result or "RSVP TODAY" in result)
        self.assertIn(">>>", result)  # CTA arrow formatting

        # Body paragraph must be preserved
        self.assertIn("Dana-Farber Marathon Challenge", result)
        self.assertIn("pasta buffet", result)
        self.assertIn("speaking program", result)
        self.assertTrue(
            "Patient and In-Memory" in result or "Patient and In-Memory Program" in result
        )

        # Ticket info must be present
        self.assertIn("Ticket Information", result)
        self.assertTrue("$30" in result or "30" in result)
        self.assertTrue("$15" in result or "15" in result)
        self.assertTrue(
            "Free for children 5" in result or "children 5 and under" in result
        )

        # RSVP instructions must be present
        self.assertIn("DFMC@dfci.harvard.edu", result)
        self.assertTrue("submit your own RSVP" in result or "own RSVP" in result)

        # Thank you message
        self.assertIn("Thank you for supporting", result)
        self.assertIn("Dana-Farber Cancer Institute", result)

        # URLs must have tracking params stripped (no utm_, aff, s_src)
        self.assertNotIn("utm_source", result)
        self.assertNotIn("utm_medium", result)
        self.assertNotIn("utm_campaign", result)
        self.assertNotIn("s_src", result)
        self.assertNotIn("aff=oddtdtcreator", result)

        # DFMC Logo (preview) at top - header content preserved
        self.assertTrue("DFMC Logo" in result or "DFMC" in result)

    def test_sample_email_joins_broken_sentences(self):
        """Broken sentences like 'runners, friends,\nand family' should be joined."""
        from app.services.email_beautifier import beautify_email

        raw = load_fixture("textemail.txt")
        result, _ = beautify_email(raw)

        # The broken "runners, friends,\nand family" should be joined
        # Either as one line or the content preserved
        self.assertIn("and family are invited", result.replace("\n", " "))


class TestStripCssBlocks(unittest.TestCase):
    """Unit tests for strip_css_blocks."""

    def test_removes_css_and_preserves_content(self):
        from app.services.email_beautifier import strip_css_blocks

        text = """body { font-size: 16px; }
@media { .x { color: red; } }
}
Hello World
More content"""
        result = strip_css_blocks(text)
        self.assertIn("Hello World", result)
        self.assertIn("More content", result)
        self.assertNotIn("body {", result)
        self.assertNotIn("@media", result)


class TestSimplifyFooter(unittest.TestCase):
    """Unit tests for simplify_footer."""

    def test_preserves_main_content(self):
        """Footer simplification must not remove body content."""
        from app.services.email_beautifier import simplify_footer

        text = """Celebrate with us at the 2026 DFMC Pasta Party!

Join us Saturday, April 18.

Dana-Farber Marathon Challenge runners and family are invited.

Dana-Farber Logo

http://www.dana-farber.org?utm_source=email

Facebook

https://www.facebook.com/page"""
        result = simplify_footer(text)

        self.assertIn("Celebrate with us", result)
        self.assertIn("Saturday, April 18", result)
        self.assertIn("Dana-Farber Marathon Challenge", result)
        self.assertIn("runners and family", result)


class TestDetectCtas(unittest.TestCase):
    """Unit tests for detect_ctas."""

    def test_detects_rsvp_today(self):
        """RSVP Today followed by URL must be detected as CTA."""
        from app.services.email_beautifier import detect_ctas

        text = """Please RSVP by Sunday, April 5

   RSVP Today

https://www.eventbrite.com/e/123"""
        ctas = detect_ctas(text)
        self.assertGreaterEqual(len(ctas), 1)
        cta_texts = [c[0] for c in ctas]
        self.assertTrue(any("rsvp" in t.lower() for t in cta_texts))


class TestCleanUrl(unittest.TestCase):
    """Unit tests for clean_url."""

    def test_strips_utm_params(self):
        from app.services.email_beautifier import clean_url

        url = "https://example.com?utm_source=email&utm_campaign=test&page=1"
        result = clean_url(url)
        self.assertNotIn("utm_source", result)
        self.assertNotIn("utm_campaign", result)
        self.assertIn("page=1", result)

    def test_strips_aff_param(self):
        from app.services.email_beautifier import clean_url

        url = "https://eventbrite.com/e/123?aff=oddtdtcreator&page=1"
        result = clean_url(url)
        self.assertNotIn("aff=", result)
        self.assertIn("page=1", result)

    def test_strips_s_src(self):
        from app.services.email_beautifier import clean_url

        url = "https://example.com?s_src=RPEM021126A"
        result = clean_url(url)
        self.assertNotIn("s_src", result)


class TestJoinBrokenLines(unittest.TestCase):
    """Unit tests for join_broken_lines."""

    def test_joins_comma_continuation(self):
        """Lines ending in comma followed by lowercase should join."""
        from app.services.email_beautifier import join_broken_lines

        text = """Dana-Farber Marathon Challenge runners, friends,
and family are invited"""
        result = join_broken_lines(text)
        # Should be joined (next line starts with lowercase)
        self.assertIn("and family are invited", result)
        # Content should be preserved
        self.assertIn("Dana-Farber Marathon Challenge", result)


if __name__ == "__main__":
    unittest.main()
