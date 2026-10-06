"""Local sitemap checks; no network, dates and new investors may change."""
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9',
      'x': 'http://www.w3.org/1999/xhtml'}


class SitemapTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
        self.entries = ET.fromstring(self.text).findall('s:url', NS)
        investors = json.loads((ROOT / 'data/titans/investors.json').read_text(encoding='utf-8'))['investors']
        self.paths = ['/', '/timing/', '/samuel/', '/titans/', '/titans/13f/'] + [f"/titans/{i['slug']}/" for i in investors]

    def test_every_screen_has_default_and_both_language_urls_without_duplicates(self):
        expected = {f'https://itpaidoff.com{p}{q}' for p in self.paths for q in ['', '?lang=en', '?lang=ko']}
        urls = [e.findtext('s:loc', namespaces=NS) for e in self.entries]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(set(urls), expected)

    def test_each_cluster_repeats_reciprocal_alternates_including_itself(self):
        for entry in self.entries:
            loc = entry.findtext('s:loc', namespaces=NS)
            base = loc.split('?')[0]
            links = entry.findall('x:link', NS)
            self.assertEqual(len(links), 3, loc)
            self.assertEqual({e.get('hreflang'): e.get('href') for e in links},
                             {'en': base+'?lang=en', 'ko': base+'?lang=ko', 'x-default': base}, loc)
            for link in links:
                self.assertEqual(link.get('rel'), 'alternate', loc)

    def test_original_html_and_sitemap_advertise_the_same_language_urls(self):
        for path in self.paths:
            html = (ROOT / path.lstrip('/') / 'index.html').read_text(encoding='utf-8')
            links = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', html))
            base = 'https://itpaidoff.com'+path
            self.assertEqual(links, {'en': base+'?lang=en', 'ko': base+'?lang=ko', 'x-default': base}, path)
            # The server serves one HTML file for both queries. Do not override a
            # different canonical in that file when Google renders the language.
            self.assertNotRegex(html, r'<link\s+rel="canonical"')

    def test_language_variants_share_dates_and_correct_update_markers(self):
        clusters = {}
        for block in re.findall(r'<url>[\s\S]*?</url>', self.text):
            base = re.search(r'<loc>([^<]+)</loc>', block)[1].split('?')[0]
            date = re.search(r'<lastmod>([^<]+)</lastmod><!-- ([\w-]+) -->', block)
            self.assertIsNotNone(date, base)
            self.assertRegex(date[1], r'^\d{4}-\d{2}-\d{2}$')
            marker = ('root' if base == 'https://itpaidoff.com/' else 'timing' if base.endswith('/timing/')
                      else 'samuel' if base.endswith('/samuel/')
                      else 'titans-13f' if base.endswith('/titans/13f/') else 'titans')
            self.assertEqual(date[2], marker, base)
            clusters.setdefault(base, set()).add(date.groups())
        self.assertTrue(all(len(dates) == 1 for dates in clusters.values()))

    def test_workflow_replacements_reach_every_variant_and_preserve_other_screens(self):
        for file, markers in [('update-data.yml', ['root', 'timing']), ('update-13f.yml', ['titans']), ('update-long.yml', ['samuel'])]:
            workflow = (ROOT / '.github/workflows' / file).read_text(encoding='utf-8')
            for marker in markers:
                target = f'<lastmod>[^<]*</lastmod><!-- {marker} -->'
                self.assertIn(target, workflow)
                changed, count = re.subn(target, f'<lastmod>2099-01-01</lastmod><!-- {marker} -->', self.text)
                wanted = 3 if marker != 'titans' else 3 * sum(p.startswith('/titans/') and p != '/titans/13f/' for p in self.paths)
                self.assertEqual(count, wanted)
                # No other marker's lastmod changes during this scoped replacement.
                for other in {'root', 'timing', 'samuel', 'titans', 'titans-13f'} - {marker}:
                    pattern = rf'<lastmod>([^<]+)</lastmod><!-- {other} -->'
                    self.assertEqual(re.findall(pattern, self.text), re.findall(pattern, changed))


if __name__ == '__main__':
    unittest.main()
