"""
RadarEnricher v1.0 — Content Radar jako wzmacniacz priorytetu kandydatów

Uzywany jako post-processing step po zebraniu kandydatów.
Skanuje viral_score z Content Radaru i dodaje go do priority kandydata.

Architektura otwarta per-portal: PORTAL_RADAR_CONFIG.
"""
import os
import requests
import logging
from typing import List
from agents.base.worker_base import ContentCandidate

logger = logging.getLogger(__name__)

# Konfiguracja per portal — dodawaj nowe portale tutaj
PORTAL_RADAR_CONFIG = {
    'kurier365': {
        'country': 'PL',
        'platforms': ['twitter', 'facebook', 'tiktok', 'youtube'],
        'viral_weight': 0.3,        # jak mocno viral_score wpływa na priority boost
        'min_viral_score': 25,      # prog do boostowania
        'boost_max': 2,             # max boost priorytetu (+2)
        'penalize_threshold': 10,   # poniżej tego: -1 do priorytetu
    },
    'biznesciti': {
        'country': 'PL',
        'platforms': ['linkedin', 'twitter', 'facebook'],
        'viral_weight': 0.25,
        'min_viral_score': 20,
        'boost_max': 1,
        'penalize_threshold': 8,
    },
    'prawy': {
        'country': 'PL',
        'platforms': ['twitter', 'facebook', 'youtube'],
        'viral_weight': 0.2,
        'min_viral_score': 30,
        'boost_max': 1,
        'penalize_threshold': 10,
    },
    # Nowy portal: skopiuj blok i dostosuj wagi
    '_template': {
        'country': 'PL',
        'platforms': ['twitter', 'facebook'],
        'viral_weight': 0.25,
        'min_viral_score': 25,
        'boost_max': 1,
        'penalize_threshold': 10,
    },
}

RADAR_URL = os.environ.get('CONTENT_RADAR_URL', 'https://radar.impresjapr.pl')


class RadarEnricher:
    """Post-processing: dodaje viral_score do kandydatów."""

    def __init__(self, portal: str = 'kurier365'):
        self.portal = portal.lower().replace('.', '').replace('com', '')
        self.config = PORTAL_RADAR_CONFIG.get(
            self.portal,
            PORTAL_RADAR_CONFIG.get('_template')
        )
        self._cache = {}  # cache viral scores per candidate id/url

    def enrich(self, candidates: List[ContentCandidate]) -> List[ContentCandidate]:
        """Wzbogac kandydatów o viral_score i dostosuj priorytety."""
        if not candidates:
            return candidates

        enriched = []
        for c in candidates:
            try:
                viral_score = self._get_viral_score(c)
                c = self._apply_boost(c, viral_score)
                c.metadata['viral_score'] = viral_score
                c.metadata['radar_config'] = self.portal
            except Exception as e:
                logger.warning(f'RadarEnricher error dla {c.title[:40]}: {e}')
            enriched.append(c)

        return sorted(enriched, key=lambda x: -x.priority)

    def _get_viral_score(self, candidate: ContentCandidate) -> float:
        """Pobierz viral_score z Content Radaru dla tytułu/URL kandydata."""
        # Cache key
        cache_key = candidate.id
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Parametry zapytania
            params = {
                'country': self.config['country'],
                'platforms': ','.join(self.config['platforms']),
            }
            if candidate.content_url:
                params['url'] = candidate.content_url
            else:
                params['q'] = candidate.title[:100]

            headers = {}
            jwt_token = os.environ.get('CONTENT_RADAR_JWT')
            if jwt_token:
                headers['Authorization'] = f'Bearer {jwt_token}'

            # 1. Najpierw spróbuj dedykowany endpoint punktacji (v1 lub api/v1)
            for path in ['/v1/trending/score', '/api/v1/trending/score']:
                try:
                    r = requests.get(
                        f'{RADAR_URL}{path}',
                        params=params,
                        headers=headers,
                        timeout=8
                    )
                    if r.status_code == 200:
                        score = r.json().get('viral_score', 0)
                        self._cache[cache_key] = float(score)
                        return float(score)
                except Exception:
                    pass

            # 2. Fallback: szukaj po tytule w global trending
            for path in ['/v1/trending/global', '/api/v1/trending/global']:
                try:
                    r2 = requests.get(
                        f'{RADAR_URL}{path}',
                        params={**params, 'q': candidate.title[:80]},
                        headers=headers,
                        timeout=8
                    )
                    if r2.status_code == 200:
                        data = r2.json()
                        items = data if isinstance(data, list) else data.get('items', [])
                        if items and isinstance(items, list):
                            score = items[0].get('viral_score', 0)
                            self._cache[cache_key] = float(score)
                            return float(score)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f'RadarEnricher API error: {e}')

        return 0.0

    def _apply_boost(self, candidate: ContentCandidate, viral_score: float) -> ContentCandidate:
        """Zastosuj boost/penalty do priorytetu kandydata."""
        config = self.config
        original_priority = candidate.priority

        if viral_score >= config['min_viral_score']:
            # Boost: im wyzszy score tym wiekszy boost (ale max boost_max)
            boost = min(
                config['boost_max'],
                int(viral_score * config['viral_weight'] / 10)
            )
            candidate.priority = min(10, original_priority + boost)
            if boost > 0:
                logger.info(f'Radar boost +{boost}: {candidate.title[:50]} (viral={viral_score})')
        elif viral_score > 0 and viral_score < config['penalize_threshold']:
            # Penalty za bardzo niski score (temat martwy w social media)
            candidate.priority = max(1, original_priority - 1)

        return candidate
