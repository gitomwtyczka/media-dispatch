"""
FeedCrawlerSource v1.0 — Feed Crawler API Source Plugin
Integracja z feed-crawler (13k+ RSS feedów, 5.9M+ artykułów)
media-dispatch | media-dev-24 | 01.09.2026
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import urllib.request
import urllib.parse
import urllib.error

from agents.base.worker_base import SourcePlugin, ContentCandidate


class FeedCrawlerSource(SourcePlugin):
    """Źródło integrujące się z API feed-crawler (crawler.impresjapr.pl)."""
    name = 'feed_crawler'

    def __init__(
        self,
        api_url: str = 'https://crawler.impresjapr.pl',
        portal: str = 'kurier365',
        categories: Optional[List[str]] = None,
        departments: Optional[List[str]] = None,
        hours_back: int = 24,
        limit: int = 50,
        state_file: Optional[str] = None,
    ):
        """
        Args:
            api_url: Base URL do API feed-crawler (np. https://crawler.impresjapr.pl lub http://localhost:8002)
            portal: Nazwa docelowego portalu (np. kurier365, prawy)
            categories: Opcjonalne słowa kluczowe lub kategorie
            departments: Opcjonalne działy w feed-crawler (np. ['konkurencja-biznes', 'nauka'])
            hours_back: Ile godzin wstecz uwzględniać
            limit: Maksymalna liczba artykułów do pobrania
            state_file: Ścieżka do pliku JSON ze stanem (deduplikacja)
        """
        self.api_url = api_url.rstrip('/')
        self.portal = portal
        self.categories = [c.lower() for c in (categories or [])]
        self.departments = departments or []
        self.hours_back = hours_back
        self.limit = limit
        self.state_file = state_file or f'/tmp/feed_crawler_state_{portal}.json'
        self.logger = logging.getLogger(self.__class__.__name__)
        self._seen = self._load_seen()

    def _load_seen(self) -> set:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except Exception as e:
                self.logger.warning(f"Nie udało się załadować stanu z {self.state_file}: {e}")
        return set()

    def _save_seen(self) -> None:
        try:
            # Zachowaj max 5000 ostatnich ID aby plik stanu nie rósł w nieskończoność
            seen_list = list(self._seen)
            if len(seen_list) > 5000:
                seen_list = seen_list[-5000:]
                self._seen = set(seen_list)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(seen_list, f, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"Nie udało się zapisać stanu do {self.state_file}: {e}")

    def _entry_id(self, item: dict) -> str:
        raw_id = str(item.get('id', ''))
        url = item.get('url', '')
        title = item.get('title', '')
        unique_key = f"{raw_id}:{url}:{title}"
        return hashlib.md5(unique_key.encode('utf-8')).hexdigest()

    def _calc_priority(self, item: dict) -> int:
        title = (item.get('title') or '').lower()
        summary = (item.get('summary') or '').lower()
        full_text = f"{title} {summary}"

        # Priorytetyzacja wg tematów
        if any(k in full_text for k in ['uokik', 'konsument', 'prawo konsumenta', 'kara', 'decyzja']):
            return 9
        if any(k in full_text for k in ['pap', 'rpp', 'inflacja', 'stopy procentowe', 'podatk', 'ustawa', 'sejm']):
            return 8
        if any(k in full_text for k in ['nauka', 'badania', 'odkrycie', 'technolog', 'ai', 'sztuczna inteligencja']):
            return 7
        if any(k in full_text for k in ['gospodark', 'biznes', 'firma', 'rynek', 'giełda', 'inwestycj']):
            return 6
        return 5

    def _http_get_json(self, url: str) -> Optional[dict]:
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'media-dispatch/1.0 (FeedCrawlerSource)'}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    data = resp.read().decode('utf-8')
                    return json.loads(data)
        except Exception as e:
            self.logger.error(f"Błąd zapytania HTTP do {url}: {e}")
        return None

    def fetch(self) -> List[ContentCandidate]:
        candidates: List[ContentCandidate] = []
        raw_articles: List[dict] = []

        # 1. Jeśli zdefiniowano konkretne działy, pobieraj przez /api/export?department=...
        if self.departments:
            for dep in self.departments:
                url = f"{self.api_url}/api/export?format=json&department={urllib.parse.quote(dep)}&limit={self.limit}"
                data = self._http_get_json(url)
                if data and 'articles' in data:
                    raw_articles.extend(data['articles'])
        else:
            # Domyślnie pobierz z /api/articles lub /api/export
            url = f"{self.api_url}/api/articles?page=1&per_page={self.limit}"
            data = self._http_get_json(url)
            if data and 'articles' in data:
                raw_articles.extend(data['articles'])
            elif isinstance(data, list):
                raw_articles.extend(data)

        # 2. Przetwórz i zmapuj na ContentCandidate
        for art in raw_articles:
            eid = self._entry_id(art)
            if eid in self._seen:
                continue

            title = art.get('title') or ''
            summary = art.get('summary') or ''
            content = art.get('content') or ''
            feed_name = art.get('feed_name') or 'unknown'
            url = art.get('url') or ''
            pub_date = art.get('published_at') or art.get('fetched_at')

            # Filtrowanie kategorii / słów kluczowych jeśli podano
            if self.categories:
                text_to_match = f"{title} {summary}".lower()
                if not any(cat in text_to_match for cat in self.categories):
                    continue

            self._seen.add(eid)

            priority = self._calc_priority(art)

            candidate = ContentCandidate(
                id=eid,
                source=f"feed_crawler:{feed_name}",
                portal=self.portal,
                title=title,
                summary=summary[:500] if summary else (content[:500] if content else ''),
                content_url=url,
                raw_content=content or summary,
                metadata={
                    'feed_name': feed_name,
                    'feed_crawler_id': art.get('id'),
                    'author': art.get('author'),
                    'published_at': pub_date,
                    'departments': art.get('departments', []),
                },
                priority=priority
            )
            candidates.append(candidate)

        self._save_seen()
        self.logger.info(f"FeedCrawlerSource pobrał {len(candidates)} nowych kandydatów.")
        return candidates

    def health_check(self) -> bool:
        """Sprawdź czy feed-crawler API odpowiada."""
        stats = self._http_get_json(f"{self.api_url}/api/stats")
        return bool(stats and 'total_articles' in stats)
