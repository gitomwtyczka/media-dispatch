"""
RadarEnricher v1.0 — Content Radar jako wzmacniacz priorytetu kandydatów.
Opcja 1: filtr/boost priorytetu na podstawie viral_score.
Architektura otwarta per-portal — dodawaj portale w PORTAL_RADAR_CONFIG.
"""
import os, logging
from typing import List

logger = logging.getLogger(__name__)

PORTAL_RADAR_CONFIG = {
    'kurier365': {
        'country': 'PL',
        'platforms': ['twitter', 'facebook', 'tiktok', 'youtube'],
        'viral_weight': 0.3,
        'min_viral_score': 25,
        'boost_max': 2,
        'penalize_threshold': 10,
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
    # Nowy portal: skopiuj _template i zmien klucz
    '_template': {
        'country': 'PL',
        'platforms': ['twitter', 'facebook'],
        'viral_weight': 0.25,
        'min_viral_score': 25,
        'boost_max': 1,
        'penalize_threshold': 10,
    },
}


class RadarEnricher:
    """Wzbogaca kandydatów o viral_score z Content Radaru."""

    def __init__(self, portal: str = 'kurier365'):
        key = portal.lower().replace('.',  '').replace('com', '').replace('pl', '').strip()
        self.config = PORTAL_RADAR_CONFIG.get(key, PORTAL_RADAR_CONFIG['_template'])
        self.radar_url = os.environ.get('CONTENT_RADAR_URL', 'https://radar.impresjapr.pl')
        self._cache: dict = {}

    def enrich(self, candidates: list) -> list:
        """Dodaj viral_score i dostosuj priorytety kandydatów."""
        import requests
        for c in candidates:
            try:
                score = self._get_score(c, requests)
                c.metadata['viral_score'] = score
                self._apply_boost(c, score)
            except Exception as e:
                logger.debug(f'RadarEnricher skip [{c.title[:30]}]: {e}')
        return sorted(candidates, key=lambda x: -x.priority)

    def _get_score(self, candidate, requests_lib) -> float:
        if candidate.id in self._cache:
            return self._cache[candidate.id]
        params = {
            'country': self.config['country'],
            'q': candidate.title[:100],
            'platforms': ','.join(self.config['platforms']),
        }
        # Spróbuj endpoint score, potem trending
        for endpoint in ['/v1/trending/score', '/v1/trending/global']:
            try:
                r = requests_lib.get(
                    self.radar_url + endpoint,
                    params=params, timeout=6
                )
                if r.status_code == 200:
                    data = r.json()
                    score = float(
                        data.get('viral_score') or
                        (data.get('items') or [{}])[0].get('viral_score', 0)
                    )
                    self._cache[candidate.id] = score
                    return score
            except Exception:
                continue
        return 0.0

    def _apply_boost(self, candidate, viral_score: float) -> None:
        cfg = self.config
        if viral_score >= cfg['min_viral_score']:
            boost = min(cfg['boost_max'], int(viral_score * cfg['viral_weight'] / 10))
            candidate.priority = min(10, candidate.priority + boost)
            if boost:
                logger.info(f'Radar +{boost} [{candidate.title[:40]}] score={viral_score}')
        elif 0 < viral_score < cfg['penalize_threshold']:
            candidate.priority = max(1, candidate.priority - 1)
