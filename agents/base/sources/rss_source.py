"""
RSSSource v1.0 — RSS feed source plugin
Wspiera: standardowe RSS 2.0, Atom, ogłoszenia UOKiK, PAP, ISBNews
"""
import hashlib
import feedparser
from datetime import datetime, timezone
from typing import List
from agents.base.worker_base import SourcePlugin, ContentCandidate

class RSSSource(SourcePlugin):
    name = 'rss'
    
    def __init__(self, feeds: list, portal: str, state_file: str = None):
        """
        feeds: lista dict {url, category, priority, name}
        portal: nazwa portalu (kurier365, biznesciti)
        state_file: JSON z widzianymi ID (dedup)
        """
        self.feeds = feeds
        self.portal = portal
        self.state_file = state_file or f'/tmp/rss_state_{portal}.json'
        self._seen = self._load_seen()
    
    def _load_seen(self) -> set:
        import json, os
        if os.path.exists(self.state_file):
            try:
                return set(json.load(open(self.state_file)))
            except: pass
        return set()
    
    def _save_seen(self):
        import json
        json.dump(list(self._seen), open(self.state_file, 'w'))
    
    def _entry_id(self, entry) -> str:
        return hashlib.md5((entry.get('link', '') + entry.get('title', '')).encode()).hexdigest()
    
    def fetch(self) -> List[ContentCandidate]:
        candidates = []
        for feed_cfg in self.feeds:
            try:
                feed = feedparser.parse(feed_cfg['url'])
                for entry in feed.entries[:20]:  # max 20 per feed
                    eid = self._entry_id(entry)
                    if eid in self._seen:
                        continue
                    self._seen.add(eid)
                    
                    # Parse timestamp
                    pub = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                    
                    # Summary
                    summary = ''
                    if hasattr(entry, 'summary'):
                        summary = entry.summary[:500]
                    elif hasattr(entry, 'description'):
                        summary = entry.description[:500]
                    
                    candidates.append(ContentCandidate(
                        id=eid,
                        source=f"rss:{feed_cfg.get('name', 'unknown')}",
                        portal=self.portal,
                        title=entry.get('title', ''),
                        summary=summary,
                        content_url=entry.get('link', ''),
                        metadata={
                            'category': feed_cfg.get('category', ''),
                            'published_at': pub,
                            'feed_name': feed_cfg.get('name', ''),
                            'feed_url': feed_cfg['url']
                        },
                        priority=feed_cfg.get('priority', 5)
                    ))
            except Exception as e:
                print(f"RSS fetch error {feed_cfg.get('url')}: {e}")
        
        self._save_seen()
        return candidates
