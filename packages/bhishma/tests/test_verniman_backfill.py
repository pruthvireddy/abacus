"""Chronology/ledger tests with synthetic pages, never network requests."""

import unittest
from datetime import date

from abacus_bhishma.verniman_backfill import _coverage, canonical_url, infer_date, page_identity


class BackfillChronologyTests(unittest.TestCase):
    def test_navigation_uses_explicit_older_link_and_body_date(self):
        html = """<a name='123'></a><div class='post-body entry-content'>
        <p>Outlook 01/02: example</p><img src='2025-12-01.png'></div>
        <a href='https://verniman.blogspot.com/2009/12/prior.html?m=0'
        id='Blog1_blog-pager-older-link'>Older Post</a>"""
        identity, older, images, month_day = page_identity(html)
        self.assertEqual(identity, "123")
        self.assertEqual(older, "https://verniman.blogspot.com/2009/12/prior.html")
        self.assertEqual(month_day, (1, 2))

    def test_year_rollover_only_at_clear_year_boundary(self):
        assigned, warnings = infer_date((12, 31), date(2026, 1, 2))
        self.assertEqual(assigned, date(2025, 12, 31))
        self.assertEqual(warnings, [])
        assigned, warnings = infer_date((10, 8), date(2026, 10, 7))
        self.assertEqual(assigned, date(2026, 10, 8))
        self.assertIn("nonmonotonic_body_outlook_date_preserved", warnings)

    def test_duplicate_and_undated_posts_are_never_silently_repaired(self):
        assigned, warnings = infer_date((10, 7), date(2026, 10, 7))
        self.assertEqual(assigned, date(2026, 10, 7))
        self.assertIn("duplicate_body_outlook_date_preserved", warnings)
        self.assertEqual(infer_date(None, date(2026, 1, 2)),
                         (None, ["no_unambiguous_outlook_month_day"]))

    def test_coverage_distinguishes_untraversed_from_no_dated_post(self):
        posts = [{"session_date": "2026-01-02", "url": "example"}]
        complete = _coverage(date(2026, 1, 1), date(2026, 1, 4), posts, True)
        self.assertEqual([row["status"] for row in complete],
                         ["weekday_no_dated_post", "post_captured", "weekend_no_dated_post", "weekend_no_dated_post"])
        partial = _coverage(date(2026, 1, 1), date(2026, 1, 4), posts, False)
        self.assertEqual(partial[0]["status"], "not_fully_traversed")
        self.assertEqual(partial[1]["post_urls"], ["example"])

    def test_unexpected_navigation_destination_is_rejected(self):
        for url in ("http://verniman.blogspot.com/2009/10/a.html",
                    "https://example.org/2009/10/a.html",
                    "https://verniman.blogspot.com/search"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                canonical_url(url)


if __name__ == "__main__":
    unittest.main()
