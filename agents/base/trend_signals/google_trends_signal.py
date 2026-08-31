"""agents/base/trend_signals/google_trends_signal.py

Google Trends + Social Trends signal plugins.
media-dispatch | media-dev-architect | 31.08.2026

Arhitektura: Placeholder pattern
  Obecnie zwracają puste listy (brak API content-radar).
  Gdy content-radar (Faza 3) będzie gotowy:
    1. Ustaw CONTENT_RADAR_URL w config workera
    2. Odkomentuj logikę HTTP w get_trending_topics()
  WorkerBase działa bez sygnałów (graceful degradation).
"""
from agents.base.worker_base import TrendSignal, ContentCandidate
from typing import List, Optional
import logging


class GoogleTrendsSignal(TrendSignal):
    """Google Trends sygnał trendów.

    Placeholder — gdy aplikacja content-radar (Faza 3) będzie gotowa,
    podmień get_trending_topics() na wywołanie jej API:

        GET {api_url}/trending?geo=PL&category=biznes
        Response: [{"topic": str, "score": float, "source": "google_trends"}]

    żeby włączyć: przekaż api_url w konfiguracji workera:
        GoogleTrendsSignal(api_url='https://content-radar.impresjapr.pl')
    """
    name = 'google_trends'

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Args:
            api_url: URL aplikacji content-radar. None = tryb placeholder (zwraca []).
            api_key: opcjonalny klucz API jeśli content-radar wymaga auth.
        """
        self.api_url = api_url  # None = placeholder mode
        self.api_key = api_key
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_trending_topics(self, category: Optional[str] = None, geo: str = 'PL') -> List[dict]:
        """Pobierz trendujące tematy z Google Trends przez content-radar API.

        Args:
            category: kategoria tematyczna (np. 'biznes', 'polityka', 'nauka')
            geo:      kod ISO kraju (domyślnie 'PL')

        Returns:
            Lista dicts [{"topic": str, "score": float 0-1, "source": "google_trends"}]
            lub [] jeśli API niedostępne (placeholder mode).
        """
        if self.api_url:
            # TODO: Faza 3 — odkomentuj gdy content-radar gotowy
            # import requests
            # params = {'geo': geo}
            # if category:
            #     params['category'] = category
            # headers = {'Authorization': f'Bearer {self.api_key}'} if self.api_key else {}
            # resp = requests.get(
            #     f"{self.api_url}/trending",
            #     params=params,
            #     headers=headers,
            #     timeout=10
            # )
            # resp.raise_for_status()
            # return resp.json()  # [{"topic": ..., "score": ..., "source": "google_trends"}]
            self.logger.warning(
                "GoogleTrendsSignal: api_url set but integration not implemented yet. "
                "Uncomment HTTP logic when content-radar API is ready."
            )

        self.logger.debug("GoogleTrendsSignal: placeholder mode, returning empty trends.")
        return []

    def enrich_candidate(self, candidate: ContentCandidate, topics: List[dict]) -> ContentCandidate:
        """Ustaw trend_score na podstawie dopasowania słów kluczowych z tytułu.

        Dziedziczy domyślną implementację z TrendSignal (bag-of-words matching).
        Override tu gdy potrzebujesz zaawansowanego scoringu (embedding similarity, etc.).
        """
        return super().enrich_candidate(candidate, topics)


class SocialTrendsSignal(TrendSignal):
    """Social media trends (TikTok, Twitter/X, Facebook).

    Placeholder — podmień na API content-radar gdy Faza 3 gotowa.
    Docelowo: agregacja trendów z wielu platform społecznościowych.

    Priorytet dla rynku PL:
      1. Twitter/X (debata publiczna, politycy)
      2. TikTok (tematy viralne, młoda publiczność)
      3. Facebook (zasig masowy, udostępnienia)
    """
    name = 'social_trends'

    def __init__(self, api_url: Optional[str] = None):
        """
        Args:
            api_url: URL content-radar API. None = placeholder mode.
        """
        self.api_url = api_url
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_trending_topics(self, category: Optional[str] = None, geo: str = 'PL') -> List[dict]:
        """Pobierz trendy social media przez content-radar API.

        Returns:
            Lista dicts [{"topic": str, "score": float 0-1, "source": str}]
            lub [] w placeholder mode.
        """
        if self.api_url:
            # TODO: Faza 3 — odkomentuj gdy content-radar gotowy
            # import requests
            # resp = requests.get(
            #     f"{self.api_url}/social-trending",
            #     params={'geo': geo, 'category': category},
            #     timeout=10
            # )
            # resp.raise_for_status()
            # return resp.json()
            self.logger.warning(
                "SocialTrendsSignal: api_url set but integration not implemented yet."
            )

        self.logger.debug("SocialTrendsSignal: placeholder mode, returning empty trends.")
        return []

    def enrich_candidate(self, candidate: ContentCandidate, topics: List[dict]) -> ContentCandidate:
        """Domyślny enrich (bag-of-words). Override jeśli potrzebujesz platform-specific scoring."""
        return super().enrich_candidate(candidate, topics)
