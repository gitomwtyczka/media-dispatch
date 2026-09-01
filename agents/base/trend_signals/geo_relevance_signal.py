"""
GeoRelevanceSignal v1.1

Waży atrakcyjność kandydata dla polskiego/europejskiego czytelnika.
Nie filtruje języka — PressAI tłumaczy. Ocenia relevancję geograficzną i tematyczną.

Skala: 0.0 - 2.0 (mnożnik priority)
  > 1.5  = wysoce relevantny dla PL
  1.0-1.5 = relevantny dla Europy / globalnie ważny
  0.5-1.0 = międzynarodowy, nisko PL-relevantny
  < 0.5   = mało istotny (US entertainment, lokalne newsy spoza regionu)
"""
from agents.base.worker_base import TrendSignal, ContentCandidate
from typing import List
import re


class GeoRelevanceSignal(TrendSignal):
    name = 'geo_relevance'

    # Słowa kluczowe zwiększające relevancję
    PL_HIGH = [
        'polska', 'polish', 'poland', 'warszawa', 'warsaw', 'kraków',
        'pln', 'złoty', 'nfz', 'zus', 'sejm', 'rząd', 'premier', 'president',
        'nbu', 'nbp', 'pkb', 'gus', 'uokik', 'krs', 'pis', 'ko', 'td',
        'inflacja', 'inflation', 'stopy procentowe', 'rpp', 'kredyt',
        'vat', 'podatek', 'budget', 'budżet', 'emerytury', 'pension',
        'pap', 'tvp', 'polsat', 'tvn'
    ]

    EU_HIGH = [
        'europa', 'europe', 'european', 'ue', 'eu ', 'euro ', 'eurozona',
        'komisja europejska', 'european commission', 'ecb', 'ebc',
        'niemcy', 'germany', 'francja', 'france', 'bruksela', 'brussels',
        'scholz', 'macron', 'von der leyen', 'nato', 'ukraina', 'ukraine',
        'csrd', 'csddd', 'ai act', 'gdpr', 'rodo', 'esg'
    ]

    GLOBAL_IMPORTANT = [
        'war', 'wojna', 'konflikt', 'conflict', 'sankcje', 'sanctions',
        'oil', 'ropa', 'gas', 'gaz', 'recession', 'recesja', 'kryzys',
        'fed', 'dollar', 'dolar', 'bitcoin', 'crypto', 'ai ', 'artificial intelligence',
        'china', 'chiny', 'russia', 'rosja', 'usa', 'trump', 'biden', 'harris',
        'federal reserve', 'wall street', 'silicon valley', 'nasdaq', 'dow jones',
        's&p', 'tech layoffs', 'startup', 'vc funding', 'ipo', 'merger', 'acquisition',
        'fed rate', 'supply chain', 'łańcuchy dostaw', 'trade war', 'taryfy'
    ]

    LOW_RELEVANCE = [
        # US entertainment / local
        'nfl', 'nba', 'mlb', 'nhl', 'super bowl',
        'oscars', 'grammy', 'emmy', 'golden globe',
        'kardashian', 'celebrity gossip', 'taylor swift concert',
        'local election', 'city council', 'county sheriff',
        'high school', 'college football',
        # Bardzo lokalne newsy bez globalnego wpływu
        'local restaurant', 'traffic accident',
    ]

    # Nauka polska — priorytet dla kuriera365 dział Nauka
    PL_SCIENCE = [
        'polska nauka', 'polscy naukowcy', 'polskie odkrycie', 'polskie badanie',
        'pan ', 'polska akademia nauk', 'agh ', 'politechnika', 'uw ', 'put ',
        'ncn ', 'ncbr ', 'narodowe centrum', 'grant naukowy',
        'naukowcy z polski', 'badacze z polsk', 'polish scientists', 'polish research',
        'odkrycie', 'przełom naukowy', 'badanie kliniczne', 'wynalazek',
        # Popularnonaukowe globalne (zawsze interesujące)
        'space', 'kosmos', 'nasa', 'esa', 'mars', 'exoplanet', 'black hole', 'czarna dziura',
        'ai badania', 'quantum', 'kwantowy', 'climate science', 'nauki o klimacie',
        'cancer research', 'alzheimer', 'dna', 'crispr', 'gene therapy',
    ]

    # Chiny/Indie/Rosja — monitoring geostrategiczny (periodicznie ważne)
    GEO_PERIODIC = [
        # Chiny
        'china', 'chiny', 'chiński', 'chinese', 'beijing', 'pekin', 'xi jinping',
        'pla ', 'taiwan', 'tajwan', 'south china sea', 'morze południowochińskie',
        'belt and road', 'nowy jedwabny szlak', 'huawei', 'tiktok ban',
        # Indie
        'india', 'indie', 'hindi', 'new delhi', 'modi', 'isro',
        'india economy', 'gospodarka indii', 'india china',
        # Rosja
        'russia', 'rosja', 'rosyjski', 'russian', 'moskwa', 'moscow', 'putin',
        'kreml', 'kremlin', 'kacapy', 'oligarch', 'gazprom', 'rosneft',
        'prigozhin', 'wagner', 'siloviki',
        # Klęski/wydarzenia losowe w tych krajach
        'trzesienie ziemi', 'earthquake', 'powodź', 'flood', 'tajfun', 'typhoon',
        'katastrofa', 'disaster', 'wybuch wulkanu', 'volcano',
        # Relacje z PL/EU
        'china eu', 'chiny ue', 'china poland', 'indie polska',
        'russian threat', 'zagrożenie rosyjskie'
    ]

    def _score(self, text: str) -> float:
        text_lower = text.lower()
        score = 1.0  # bazowy

        # Polskie sygnaly
        pl_hits = sum(1 for kw in self.PL_HIGH if kw in text_lower)
        if pl_hits >= 2:
            score *= 1.8
        elif pl_hits == 1:
            score *= 1.4

        # Europejskie sygnaly
        eu_hits = sum(1 for kw in self.EU_HIGH if kw in text_lower)
        if eu_hits >= 2:
            score *= 1.3
        elif eu_hits == 1:
            score *= 1.15

        # Globalnie ważne
        global_hits = sum(1 for kw in self.GLOBAL_IMPORTANT if kw in text_lower)
        if global_hits >= 2:
            score *= 1.1
        elif global_hits == 1:
            score *= 1.05

        # Niska relevancja
        low_hits = sum(1 for kw in self.LOW_RELEVANCE if kw in text_lower)
        if low_hits >= 2:
            score *= 0.3
        elif low_hits == 1:
            score *= 0.6

        # Nauka polska (boost dla działu Nauka kuriera)
        science_hits = sum(1 for kw in self.PL_SCIENCE if kw in text_lower)
        if science_hits >= 2:
            score *= 1.6
        elif science_hits == 1:
            score *= 1.3

        # Geostrategia periodyczna (Chiny/Indie/Rosja)
        geo_hits = sum(1 for kw in self.GEO_PERIODIC if kw in text_lower)
        if geo_hits >= 3:
            score *= 1.25  # dużo sygnali = ważny artykuł
        elif geo_hits >= 1:
            score *= 1.1  # pojedynczy wzmianka = lekki boost

        return min(round(score, 2), 2.0)  # max 2.0

    def get_trending_topics(self, category=None, geo='PL') -> List[dict]:
        return []  # nie używane, to signal nie source

    def enrich_candidate(self, candidate: ContentCandidate, topics: List[dict]) -> ContentCandidate:
        text = f"{candidate.title} {candidate.summary}"
        text_lower = text.lower()
        multiplier = self._score(text)
        science_hits = sum(1 for kw in self.PL_SCIENCE if kw in text_lower)
        candidate.priority = round(candidate.priority * multiplier)
        candidate.metadata['geo_relevance_score'] = multiplier
        candidate.metadata['geo_relevance'] = (
            'PL-nauka' if science_hits >= 1 and multiplier >= 1.3
            else 'PL-high' if multiplier >= 1.5
            else 'EU' if multiplier >= 1.0
            else 'global' if multiplier >= 0.7
            else 'low'
        )
        return candidate
