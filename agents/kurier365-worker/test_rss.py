import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.base.sources.rss_source import RSSSource

rss = RSSSource(
    feeds=[
        {'url': 'https://uokik.gov.pl/rss.xml', 'name': 'UOKiK', 'category': 'Prawo', 'priority': 9},
        {'url': 'https://www.pap.pl/rss.xml', 'name': 'PAP', 'category': 'Kraj', 'priority': 7},
    ],
    portal='test'
)
candidates = rss.fetch()
print(f'Znaleziono {len(candidates)} kandydatow:')
for c in candidates[:5]:
    print(f'  [{c.priority}] {c.title[:80]}')
