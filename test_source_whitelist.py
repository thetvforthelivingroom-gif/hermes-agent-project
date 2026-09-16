import unittest
import os
import json
from source_whitelist import is_trusted, log_decision, LOG_PATH

class TestSourceWhitelist(unittest.TestCase):
    def setUp(self):
        # Ensure log file starts empty for each test
        if os.path.exists(LOG_PATH):
            os.remove(LOG_PATH)

    def test_whitelisted_domains(self):
        whitelist = [
            "https://www.reuters.com/article/example",
            "http://apnews.com/some-article",
            "https://bbc.com/news",
            "https://techcrunch.com/startup",
            # subdomains should also pass
            "https://news.reuters.com/world",
            "https://regional.bbc.com/local",
        ]
        for url in whitelist:
            self.assertTrue(is_trusted(url), f"{url} should be trusted")
            # log and verify entry
            log_decision(url, True)
        # Verify log file contains correct number of entries
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), len(whitelist))
        for line in lines:
            entry = json.loads(line)
            self.assertTrue(entry['allowed'])
            self.assertIn('timestamp', entry)
            self.assertIn('url', entry)

    def test_non_whitelisted_domains(self):
        non_whitelist = [
            "https://example.com/article",
            "http://malicious.org/phish",
            "https://news.google.com",
        ]
        for url in non_whitelist:
            self.assertFalse(is_trusted(url), f"{url} should be rejected")
            log_decision(url, False)
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), len(non_whitelist))
        for line in lines:
            entry = json.loads(line)
            self.assertFalse(entry['allowed'])

if __name__ == '__main__':
    unittest.main()
