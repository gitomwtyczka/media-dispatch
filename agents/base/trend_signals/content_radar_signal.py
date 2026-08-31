"""agents/base/trend_signals/content_radar_signal.py

Content Radar Signal — integracja z produkcyjnym API radar.impresjapr.pl
media-dispatch | media-dev-architect | 31.08.2026

Content Radar (repo: gitomwtyczka/content-radar) — system monitorowania trendów:
  - Google Trends (pytrends, geo=PL, 7d)
  - Twitter/X (Apify)
  - TikTok (Apify)
  - Instagram, YouTube, Reddit, Facebook, LinkedIn, RSS

Viral Score formula (zaimplementowana w Content Radar):
  views * 0.1 + likes * 1.0 + shares * 3.0 + comments * 2.0
  + Google Trends boost (+10 jeśli interest > 70)

Endpoint: GET /api/v1/trending/global?limit=50&category={category}
Auth: JWT Bearer token (user JWT z Content Radar)
"""
from agents.base.worker_base import TrendSignal, ContentCandidate
from typing import List, Optional
import logging


class ContentRadarSignal(TrendSignal):
    """Content Radar Trend Signal — agreguje trendy z wielu platform.

    Odpytuje produkcyjne API radar.impresjapr.pl które co 15 min
    odswierza dane z: Google Trends, Twitter/X, TikTok, Instagram,
    YouTube, Reddit, Facebook, LinkedIn, RSS.

    Auth:
        JWT Bearer token (nie X-API-Key — endpoint /api/v1/trending/global
        wymaga zalogowanego użytkownika z planem pro lub enterprise).

    Konfiguracja w worker.py:
        ContentRadarSignal(
            api_url='https://radar.impresjapr.pl',
            jwt_token='eyJ...',  # JWT z konta Content Radar
        )
    """
    name = 'content_radar'

    CONTENT_RADAR_URL = 'https://radar.impresjapr.pl'

    def __init__(
        self,
        api_url: str = CONTENT_RADAR_URL,
        jwt_token: Optional[str] = None,
    ):
        """
        Args:
            api_url:   URL Content Radar API (produkcja: https://radar.impresjapr.pl)
            jwt_token: JWT Bearer token z Content Radar.
                       Uzyskaj przez POST /api/v1/auth/login
                       lub skonfiguruj przez zmienną środowiskową CONTENT_RADAR_JWT.
        """
        self.api_url = api_url
        self.jwt_token = jwt_token
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_trending_topics(self, category: Optional[str] = None, geo: str = 'PL') -> List[dict]:
        """Pobierz trending topics z Content Radar API.

        Endpoint: GET /api/v1/trending/global?limit=50&category={category}
        Wymaga planu pro lub enterprise.

        Args:
            category: kategoria filtrowania (np. 'biznes', 'polityka', 'nauka')
                      lub None dla wszystkich kategorii
            geo:      ignorowane (Content Radar obsługuje PL by default)

        Returns:
            Lista dictów:
            [{
                'topic': str,        # tytuł posta/tematu
                'score': float,      # 0-1, znormalizowany viral_score
                'source': str,       # platforma (twitter, tiktok, etc.)
                'viral_score': float # surowy viral_score z Content Radar
            }]

        Raises:
            RuntimeError: jeśli brak JWT tokena lub błąd API.
        """
        if not self.jwt_token:
            self.logger.warning(
                "ContentRadarSignal: brak jwt_token — ustaw CONTENT_RADAR_JWT lub przekaż w konstruktorze. "
                "Returning empty trends."
            )
            return []

        try:
            import requests
        except ImportError:
            self.logger.error("ContentRadarSignal: requests not installed. pip install requests")
            return []

        try:
            params = {'limit': 50}
            if category:
                params['category'] = category

            resp = requests.get(
                f"{self.api_url}/api/v1/trending/global",
                headers={'Authorization': f'Bearer {self.jwt_token}'},
                params=params,
                timeout=10
            )

            if resp.status_code == 401:
                self.logger.error("ContentRadarSignal: JWT token invalid or expired.")
                return []

            if resp.status_code == 403:
                self.logger.error(
                    "ContentRadarSignal: Brak dostępu do /api/v1/trending/global — "
                    "wymagany plan Pro lub Enterprise w Content Radar."
                )
                return []

            resp.raise_for_status()
            posts = resp.json()

            if not posts:
                return []

            # Normalizuj viral_score do 0-1
            max_viral = max((p.get('viral_score', 0) for p in posts), default=1)
            if max_viral == 0:
                max_viral = 1

            topics = []
            for post in posts:
                viral_raw = post.get('viral_score', 0) or 0
                normalized = viral_raw / max_viral

                # Użyj tytułu lub summary jako topic
                topic_text = post.get('title') or post.get('summary', '')
                if not topic_text:
                    continue

                topics.append({
                    'topic': topic_text,
                    'score': round(normalized, 4),
                    'source': post.get('source_platform', 'content_radar'),
                    'viral_score': viral_raw,
                    'url': post.get('url'),
                    'category': post.get('category'),
                })

            self.logger.info(
                "ContentRadarSignal: got %d trending topics (category=%s)",
                len(topics), category
            )
            return topics

        except Exception as e:
            self.logger.error("ContentRadarSignal: API call failed: %s", e, exc_info=True)
            return []

    def enrich_candidate(self, candidate: ContentCandidate, topics: List[dict]) -> ContentCandidate:
        """Wzbogac kandydata o trend_score z Content Radar.

        Rozszerza domyślną implementację (bag-of-words) o scoring na summary.
        """
        if not topics:
            return candidate

        title_lower = candidate.title.lower()
        summary_lower = candidate.summary.lower()
        max_score = candidate.trend_score

        for topic in topics:
            topic_words = topic.get('topic', '').lower().split()
            if not topic_words:
                continue

            # Dopasowanie w tytule (waga 1.0) i summary (waga 0.5)
            title_matches = sum(1 for w in topic_words if w in title_lower)
            summary_matches = sum(1 for w in topic_words if w in summary_lower)

            topic_score = topic.get('score', 0.5)
            title_contribution = (title_matches / len(topic_words)) * topic_score
            summary_contribution = (summary_matches / len(topic_words)) * topic_score * 0.5

            combined = min(title_contribution + summary_contribution, 1.0)
            max_score = max(max_score, combined)

        candidate.trend_score = round(max_score, 4)
        return candidate
