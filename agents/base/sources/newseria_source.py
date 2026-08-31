"""agents/base/sources/newseria_source.py

Newseria connector z filtrem Eco-Bias Gate.
media-dispatch | media-dev-architect | 31.08.2026

Newseria.pl — polska agencja depeszowa B2B.
Wymąga logowania (sesja HTTP) lub API key.

Eco-Bias Gate:
  Filtr neutralności edytorskiej dla BiznesCiti — blokuje treści
  z silnym politycznym biasęm ekologicznym (np. “Green Deal = jedyne wyjście”).
  Kurier365.pl stosuje łagodniejszy wariant (tylko blokada skrajności).
"""
from agents.base.worker_base import SourcePlugin, ContentCandidate
from typing import List, Optional
import hashlib
import logging


class NewseriaSource(SourcePlugin):
    """Newseria connector z filtrem Eco-Bias Gate.

    TODO: Faza 2 — implementacja:
        Opcja A: Scraping sesyjny (login + requests.Session)
        Opcja B: Newseria API (jeśli dostępne dla konta)

    Eco-Bias Gate:
        Lista słów kluczowych definiuje co jest “skrajnie polityczna ekologia”.
        Można rozszerzyć przez podanie eco_bias_keywords w konstruktorze.
        Domyślna lista — zachowawcza (tylko skrajne przypadki).
    """
    name = 'newseria'

    # Domyślne słowa kluczowe blokujące skrajnie polityczne treści ekologiczne
    # Logika: blokuj treści z jednoznacznym ideologicznym biasęm eko,
    # NIE blokuj neutralnych artykułów o ekologii, klimacie, OZE.
    DEFAULT_ECO_BIAS_KEYWORDS = [
        'zielony ład rozwiazuje',
        'ekologia = ratunek',
        'odnawialne zrodla jedynym',
        'klimat najwazniejszy problem',
        'esg obowiazkowy dla wszystkich',
        'tylko zielona energia',
        'wegiel musi zniknąc natychmiast',
    ]

    def __init__(
        self,
        portal: str,
        username: Optional[str],
        password: Optional[str],
        categories: Optional[List[str]] = None,
        eco_bias_keywords: Optional[List[str]] = None,
    ):
        """
        Args:
            portal:             docelowy portal ('kurier365.pl' lub 'biznesciti.com')
            username:           login Newseria
            password:           hasło Newseria
            categories:         lista kategorii Newseria (domyślnie: gospodarka, biznes, finanse)
            eco_bias_keywords:  opcjonalna lista dodatkowych KW dla Eco-Bias Gate
        """
        self.portal = portal
        self.username = username
        self.password = password
        self.categories = categories or ['gospodarka', 'biznes', 'finanse']
        # Połącz domyślne z dodatkowymi
        self.eco_bias_keywords = self.DEFAULT_ECO_BIAS_KEYWORDS + (eco_bias_keywords or [])
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch(self) -> List[ContentCandidate]:
        """Pobierz depesze z Newseria z filtrem Eco-Bias Gate.

        TODO: Faza 2 — implementacja scraping/API:
            1. Zaloguj się do newseria.pl (session cookie)
            2. Pobierz listę depesz z wybranych kategorii
            3. Odfiltruj przez eco_bias_gate()
            4. Zbuduj ContentCandidate dla każdej depeszy

        Returns:
            [] (placeholder) lub lista ContentCandidate.
        """
        if not self.username or not self.password:
            self.logger.debug("NewseriaSource: no credentials configured, returning []")
            return []

        # TODO: Faza 2
        # import requests
        # session = requests.Session()
        #
        # # Logowanie
        # login_resp = session.post(
        #     'https://newseria.pl/login',
        #     data={'username': self.username, 'password': self.password},
        #     timeout=30
        # )
        # if login_resp.status_code != 200:
        #     raise RuntimeError(f"Newseria login failed: HTTP {login_resp.status_code}")
        #
        # candidates = []
        # for category in self.categories:
        #     resp = session.get(
        #         f'https://newseria.pl/depesze/{category}',
        #         timeout=30
        #     )
        #     # parsuj HTML — beautifulsoup4
        #     # for item in parsed_items:
        #     #     if self._eco_bias_gate(item['title'] + ' ' + item['summary']):
        #     #         self.logger.info("Eco-Bias Gate: blocked '%s'", item['title'][:60])
        #     #         continue
        #     #     cid = hashlib.sha256(item['url'].encode()).hexdigest()[:16]
        #     #     candidates.append(ContentCandidate(
        #     #         id=f"newseria_{cid}",
        #     #         source='newseria',
        #     #         portal=self.portal,
        #     #         title=item['title'],
        #     #         summary=item['summary'][:300],
        #     #         content_url=item['url'],
        #     #         priority=7,
        #     #         metadata={'category': category, 'agency': 'newseria'}
        #     #     ))
        # return candidates

        self.logger.info(
            "NewseriaSource: placeholder mode (%d categories configured), returning []",
            len(self.categories)
        )
        return []

    def _eco_bias_gate(self, text: str) -> bool:
        """Eco-Bias Gate: sprawdź czy tekst zawiera skrajnie polityczne eko-frazy.

        Filtr neutralności edytorskiej — chroni portale przed jednostronnym
        przekazem ideologicznym w treściach ze zewnętrznych agencji.

        Args:
            text: tytuł + summary depeszy

        Returns:
            True = ODRZUC (sygnał skrajnego biasów), False = OK do publikacji.
        """
        text_normalized = (
            text.lower()
            .replace('ą', 'a').replace('ć', 'c').replace('ę', 'e')
            .replace('ł', 'l').replace('ó', 'o').replace('ś', 's')
            .replace('ź', 'z').replace('ż', 'z').replace('ń', 'n')
        )
        return any(
            kw.lower()
            .replace('ą', 'a').replace('ć', 'c').replace('ę', 'e')
            .replace('ł', 'l').replace('ó', 'o').replace('ś', 's')
            .replace('ź', 'z').replace('ż', 'z').replace('ń', 'n')
            in text_normalized
            for kw in self.eco_bias_keywords
        )

    def health_check(self) -> bool:
        """Sprawdź czy Newseria jest osiągalne."""
        if not self.username:
            return False
        # TODO: HEAD request do newseria.pl
        return True
