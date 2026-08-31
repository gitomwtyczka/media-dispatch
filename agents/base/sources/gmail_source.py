"""agents/base/sources/gmail_source.py

Gmail i RSS source plugins.
media-dispatch | media-dev-architect | 31.08.2026

GmailSource:
  Współpracuje z PressAI Gmail API (press.impresjapr.pl/api/gmail/).
  Placeholder — fetch() zwraca [] dopóki PressAI Gmail endpoint nie będzie gotowy.

RSSSource:
  Placeholder — integracja z feed-crawler-worker (Faza 2).
"""
from agents.base.worker_base import SourcePlugin, ContentCandidate
from typing import List, Optional
import hashlib
import logging
import re


class GmailSource(SourcePlugin):
    """Gmail źródło — monitoruje skrzynkę i wyciąga kandydatów.

    Współpracuje z PressAI Gmail API:
        GET  {pressai_url}/api/gmail/list?label={label}
        POST {pressai_url}/api/gmail/prepare-article  {message_id: ...}

    Biała lista nadawców (allowed_senders):
        Tylko emaile pasujące do wzorca są przetwarzane.
        Wzorce obsługują wildcard '*' (np. '*@wei.org.pl', '*rudzinski*').

    Przykład konfiguracji:
        GmailSource(
            portal='kurier365.pl',
            pressai_url='https://press.impresjapr.pl',
            token='JWT...',
            allowed_senders=[
                {'email': '*rudzinski*', 'name': 'Rudzinski', 'requires_review': True},
                {'email': '*@wei.org.pl',  'name': 'WEI',      'requires_review': False},
            ]
        )
    """
    name = 'gmail'

    def __init__(
        self,
        portal: str,
        pressai_url: str,
        token: Optional[str],
        allowed_senders: Optional[List[dict]] = None,
        label: str = 'INBOX',
    ):
        """
        Args:
            portal:          docelowy portal (np. 'kurier365.pl')
            pressai_url:     URL serwisu PressAI
            token:           JWT token PressAI (może być None w placeholder mode)
            allowed_senders: lista dopuszczonych nadawców z polami:
                             {'email': str (wildcard), 'name': str, 'requires_review': bool}
            label:           etykieta Gmail do monitorowania (domyślnie INBOX)
        """
        self.portal = portal
        self.pressai_url = pressai_url
        self.token = token
        self.allowed_senders = allowed_senders or []
        self.label = label
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch(self) -> List[ContentCandidate]:
        """Pobierz nowe emaile z Gmaila przez PressAI API.

        TODO: Implementacja gdy PressAI Gmail API gotowe:
            1. GET {pressai_url}/api/gmail/list?label={label}
            2. Filtruj przez _match_sender()
            3. POST {pressai_url}/api/gmail/prepare-article
            4. Zbuduj ContentCandidate z odpowiedzi

        Returns:
            [] (placeholder) lub lista ContentCandidate.
        """
        if not self.token or not self.pressai_url:
            self.logger.debug("GmailSource: no token/pressai_url configured, returning []")
            return []

        # TODO: Faza 2 — implementacja HTTP calls do PressAI Gmail API
        # import requests
        # headers = {'Authorization': f'Bearer {self.token}'}
        #
        # # 1. Pobierz listę nowych wiadomości
        # resp = requests.get(
        #     f"{self.pressai_url}/api/gmail/list",
        #     params={'label': self.label},
        #     headers=headers,
        #     timeout=30
        # )
        # resp.raise_for_status()
        # messages = resp.json().get('messages', [])
        #
        # candidates = []
        # for msg in messages:
        #     sender_info = self._match_sender(msg['from'])
        #     if not sender_info:
        #         continue  # nie na białej liście
        #
        #     # 2. Przygotuj artykuł przez PressAI
        #     prep_resp = requests.post(
        #         f"{self.pressai_url}/api/gmail/prepare-article",
        #         json={'message_id': msg['id']},
        #         headers=headers,
        #         timeout=60
        #     )
        #     prep_resp.raise_for_status()
        #     article = prep_resp.json()
        #
        #     cid = hashlib.sha256(msg['id'].encode()).hexdigest()[:16]
        #     candidates.append(ContentCandidate(
        #         id=f"gmail_{cid}",
        #         source='gmail',
        #         portal=self.portal,
        #         title=article.get('title', msg.get('subject', '(bez tytułu)')),
        #         summary=article.get('summary', '')[:300],
        #         content_url=None,
        #         raw_content=article.get('content'),
        #         priority=6 if sender_info.get('requires_review') else 8,
        #         metadata={
        #             'sender': sender_info['name'],
        #             'message_id': msg['id'],
        #             'requires_review': sender_info.get('requires_review', True),
        #         }
        #     ))
        # return candidates

        self.logger.info("GmailSource: placeholder mode, returning []")
        return []

    def _match_sender(self, email: str) -> Optional[dict]:
        """Sprawdź czy nadawca jest na białej liście.

        Args:
            email: adres email nadawcy

        Returns:
            Dict nadawcy ze słownika allowed_senders lub None jeśli brak dopasowania.
        """
        for sender in self.allowed_senders:
            pattern = sender['email'].replace('*', '.*')
            if re.match(pattern, email, re.IGNORECASE):
                return sender
        return None

    def health_check(self) -> bool:
        """Sprawdź połączenie z PressAI Gmail API."""
        if not self.token or not self.pressai_url:
            return False  # nie skonfigurowany
        # TODO: GET {pressai_url}/api/gmail/status
        return True


class RSSSource(SourcePlugin):
    """RSS/Atom feed źródło.

    Agreguje wiele feedów RSS. Każdy feed może mieć swoją kategorię i priorytet.

    Integracja z feed-crawler-worker (Faza 2):
        Docelowo feed-crawler-worker (osobny serwis) obsługuje pooling i deduplikację.
        RSSSource będzie odpytywać jego endpoint zamiast bezpośrednio parsić XML.

    Przykład feeds:
        [
            {'url': 'https://uokik.gov.pl/rss.xml', 'category': 'prawo', 'priority': 9},
            {'url': 'https://naukawpolsce.pl/rss',   'category': 'nauka', 'priority': 7},
            {'url': 'https://pap.pl/rss.xml',        'category': 'kraj',  'priority': 8},
        ]
    """
    name = 'rss'

    def __init__(
        self,
        portal: str,
        feeds: List[dict],
        pressai_url: str,
        token: Optional[str],
    ):
        """
        Args:
            portal:      docelowy portal
            feeds:       lista feedów: [{'url': str, 'category': str, 'priority': int}]
            pressai_url: URL serwisu PressAI (do generowania draftu artykułu)
            token:       JWT token PressAI
        """
        self.portal = portal
        self.feeds = feeds
        self.pressai_url = pressai_url
        self.token = token
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch(self) -> List[ContentCandidate]:
        """Pobierz nowe wpisy z RSS feedów.

        TODO: Faza 2 — integracja z feed-crawler-worker:
            GET {feed_crawler_url}/api/latest?portal={portal}&since={timestamp}
            Response: [{id, url, title, summary, category, published_at}]

        Alternatywnie: bezpośrenie parsowanie feedxml przez feedparser.

        Returns:
            [] (placeholder) lub lista ContentCandidate.
        """
        # TODO: Faza 2
        # import feedparser
        # candidates = []
        # for feed_cfg in self.feeds:
        #     try:
        #         d = feedparser.parse(feed_cfg['url'])
        #         for entry in d.entries[:10]:  # max 10 najnowszych
        #             cid = hashlib.sha256(entry.link.encode()).hexdigest()[:16]
        #             candidates.append(ContentCandidate(
        #                 id=f"rss_{cid}",
        #                 source='rss',
        #                 portal=self.portal,
        #                 title=entry.title,
        #                 summary=entry.get('summary', '')[:300],
        #                 content_url=entry.link,
        #                 priority=feed_cfg.get('priority', 5),
        #                 metadata={'category': feed_cfg.get('category'), 'feed_url': feed_cfg['url']}
        #             ))
        #     except Exception as e:
        #         self.logger.error("RSS feed %s error: %s", feed_cfg['url'], e)
        # return candidates

        self.logger.info("RSSSource: placeholder mode (%d feeds configured), returning []", len(self.feeds))
        return []

    def health_check(self) -> bool:
        """Sprawdź czy feedsy są osiągalne (HEAD request)."""
        # TODO: HEAD request do pierwszego feedu
        return len(self.feeds) > 0
