"""
GmailSource v1.0 — Gmail source via PressAI API
Monitoruje skrzynkę tobroz@gmail.com przez PressAI backend (https://press.impresjapr.pl/api/gmail).
Priorytetowi nadawcy: WEI, Cezary Rudiński, Arkadiusz Bińczyk, Biały Kruk, Juchniewicz, Bolek, Zabka, Maxmedia, Gryżewski, Kalinowska, Art-Media, Fundacja XBW.
media-dispatch | media-dev-39 | 01.09.2026
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional, Union
import requests

from agents.base.worker_base import SourcePlugin, ContentCandidate

logger = logging.getLogger("GmailSource")


class GmailSource(SourcePlugin):
    """Gmail źródło — monitoruje skrzynkę przez PressAI Gmail API."""
    name = 'gmail'

    # PRIORITY_SENDERS — dopasowanie po fragmencie adresu email LUB nazwy nadawcy (case-insensitive)
    # Wartości priority: 9-10 = P0 (złoty w Sheets, #editorial-priority Discord)
    #                    7-8  = P0/P1 (złoty w Sheets)
    # Dodawaj fragm. domeny (@art-media.pl) lub imienia/nazwiska (rudzinski)
    # TODO: Uzupełnić o dokładne adresy email współpracowników gdy znane
    PRIORITY_SENDERS = {
        # === JUŻ ISTNIEJĄCE ===
        'wei.org.pl': {'name': 'WEI', 'priority': 9, 'portal': 'kurier365'},
        'bialykruk.pl': {'name': 'Biały Kruk', 'priority': 8, 'portal': 'kurier365'},
        'rudinski': {'name': 'Cezary Rudiński', 'priority': 9, 'portal': 'kurier365'},
        'rudzinski': {'name': 'Cezary Rudiński', 'priority': 9, 'portal': 'kurier365'},
        'pluzanski': {'name': 'T. Płużański', 'priority': 9, 'portal': 'kurier365'},
        't_pluzanski': {'name': 'T. Płużański', 'priority': 9, 'portal': 'kurier365'},
        'tomasz.pluzanski': {'name': 'T. Płużański', 'priority': 9, 'portal': 'kurier365'},
        'binczyk': {'name': 'Arkadiusz Bińczyk', 'priority': 8, 'portal': 'kurier365'},
        'arkadiusz.binczyk': {'name': 'Arkadiusz Bińczyk', 'priority': 8, 'portal': 'kurier365'},

        # === NOWI WSPÓŁPRACOWNICY (P0) ===
        # Nowi współpracownicy (01.09.2026)
        'juchniewicz': {'name': 'Juchniewicz', 'priority': 9, 'portal': 'kurier365'},
        'bolek': {'name': 'Bolek', 'priority': 9, 'portal': 'kurier365'},
        'zabka': {'name': 'Zabka Biuro Prasowe', 'priority': 9, 'portal': 'kurier365'},
        'żabka': {'name': 'Zabka Biuro Prasowe', 'priority': 9, 'portal': 'kurier365'},
        'maxmedia': {'name': 'Maxmedia', 'priority': 8, 'portal': 'kurier365'},
        'max-media': {'name': 'Maxmedia', 'priority': 8, 'portal': 'kurier365'},
        'gryzewski': {'name': 'Gryżewski', 'priority': 9, 'portal': 'kurier365'},
        'gryżewski': {'name': 'Gryżewski', 'priority': 9, 'portal': 'kurier365'},
        'kalinowska': {'name': 'Beata Kalinowska', 'priority': 8, 'portal': 'kurier365'},
        'beata.kalinowska': {'name': 'Beata Kalinowska', 'priority': 8, 'portal': 'kurier365'},
        'art-media': {'name': 'Art-Media', 'priority': 9, 'portal': 'kurier365'},
        'artmedia': {'name': 'Art-Media', 'priority': 9, 'portal': 'kurier365'},
        'art_media': {'name': 'Art-Media', 'priority': 9, 'portal': 'kurier365'},
        'fundacja': {'name': 'Fundacja XBW', 'priority': 8, 'portal': 'kurier365'},
        'xbw': {'name': 'Fundacja XBW', 'priority': 9, 'portal': 'kurier365'},
    }

    def __init__(
        self,
        pressai_url: str = 'https://press.impresjapr.pl',
        portal: str = 'kurier365',
        token: Optional[str] = None,
        hours_back: int = 24,
        state_file: Optional[str] = None,
        account_id: Optional[int] = None,
        account_email: str = 'tobroz@gmail.com',
        allowed_senders: Optional[Union[dict, list]] = None,
        max_results: int = 50,
    ):
        """
        Args:
            pressai_url:      Base URL serwisu PressAI (np. 'https://press.impresjapr.pl')
            portal:           docelowy portal (np. 'kurier365' lub 'kurier365.pl')
            token:            JWT token PressAI (jeśli None, czyta z env PRESSAI_JWT_USER / PRESSAI_JWT)
            hours_back:       ile godzin wstecz sprawdzać maile (domyślnie 24)
            state_file:       ścieżka do pliku JSON ze stanem przetworzonych ID
            account_id:       ID konta Gmail w bazie PressAI (jeśli None, automatycznie wykrywane)
            account_email:    adres email konta w PressAI (domyślnie 'tobroz@gmail.com')
            allowed_senders:  opcjonalna lista/słownik nadawców do nadpisania PRIORITY_SENDERS
            max_results:      maksymalna liczba wiadomości do pobrania (max 50)
        """
        self.pressai_url = pressai_url.rstrip('/')
        self.portal = portal
        self.token = token
        self.hours_back = hours_back
        self.state_file = state_file or f'/tmp/gmail_state_{portal.replace(".", "_")}.json'
        self.account_id = account_id
        self.account_email = account_email
        self.allowed_senders = allowed_senders
        self.max_results = min(max_results, 50)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._seen = self._load_seen()

    def _get_token(self) -> Optional[str]:
        """Pobierz token JWT z konfiguracji lub zmiennych środowiskowych."""
        return self.token or os.environ.get('PRESSAI_JWT_USER') or os.environ.get('PRESSAI_JWT') or os.environ.get('PRESSAI_TOKEN')

    def _load_seen(self) -> set:
        """Wczytaj identyfikatory już przetworzonych wiadomości."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except Exception as e:
                self.logger.warning(f"Nie udało się załadować stanu z {self.state_file}: {e}")
        return set()

    def _save_seen(self) -> None:
        """Zapisz przetworzone identyfikatory do pliku JSON."""
        try:
            seen_list = list(self._seen)
            if len(seen_list) > 5000:
                seen_list = seen_list[-5000:]
                self._seen = set(seen_list)
            dir_name = os.path.dirname(os.path.abspath(self.state_file))
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(seen_list, f, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"Nie udało się zapisać stanu do {self.state_file}: {e}")

    def _detect_sender(self, from_addr: str) -> Optional[dict]:
        """Identyfikuj priorytetowego nadawcę."""
        if not from_addr:
            return None
        from_lower = from_addr.lower()

        # Sprawdź niestandardową listę/słownik jeśli przekazano
        if isinstance(self.allowed_senders, dict):
            for key, info in self.allowed_senders.items():
                if key.lower() in from_lower:
                    return info
        elif isinstance(self.allowed_senders, list):
            for item in self.allowed_senders:
                pattern = item.get('email', '').lower().replace('*', '')
                if pattern and pattern in from_lower:
                    return {
                        'name': item.get('name', pattern),
                        'priority': item.get('priority', 8 if not item.get('requires_review') else 9),
                        'portal': item.get('portal', self.portal),
                        'requires_review': item.get('requires_review', True)
                    }

        # Domyślna lista PRIORITY_SENDERS
        for key, info in self.PRIORITY_SENDERS.items():
            if key in from_lower:
                return info
        return None

    def fetch(self) -> List[ContentCandidate]:
        """Pobierz nowe maile przez PressAI Gmail API."""
        candidates = []
        token = self._get_token()
        if not token:
            logger.warning('GmailSource: brak PRESSAI_JWT_USER')
            return []

        headers = {'Authorization': f'Bearer {token}'}
        pressai_url = self.pressai_url

        # Pobierz account_id dla tobroz@gmail.com
        try:
            r = requests.get(f'{pressai_url}/api/gmail/accounts', headers=headers, timeout=10)
            if r.status_code != 200:
                logger.warning(f'GmailSource: accounts {r.status_code}')
                return []
            accounts = r.json().get('accounts', [])
            if not accounts:
                logger.warning('GmailSource: brak kont Gmail')
                return []
            account_id = self.account_id or accounts[0]['id']
        except Exception as e:
            logger.error(f'GmailSource accounts error: {e}')
            return []

        # Pobierz wiadomosci z ostatnich hours_back godzin
        days = max(1, self.hours_back // 24)
        try:
            r2 = requests.get(
                f'{pressai_url}/api/gmail/messages',
                headers=headers,
                params={'account_id': account_id, 'q': f'newer_than:{days}d', 'max_results': self.max_results},
                timeout=15
            )
            if r2.status_code != 200:
                logger.warning(f'GmailSource: messages {r2.status_code} - {r2.text[:100]}')
                return []
            messages = r2.json().get('messages', [])
        except Exception as e:
            logger.error(f'GmailSource messages error: {e}')
            return []

        for msg in messages:
            sender = msg.get('from', '').lower()
            msg_id = msg.get('id', '')

            # Filtruj po priorytetowych nadawcach
            sender_info = self._detect_sender(sender)
            if not sender_info:
                continue

            # Deduplikacja
            eid = hashlib.md5(msg_id.encode()).hexdigest()
            if eid in self._seen:
                continue
            self._seen.add(eid)

            # Dla P0 (priority >= 9): wywolaj prepare-article aby wyciagnac obrazki + tresc
            prepared_data = {}
            if sender_info.get('priority', 0) >= 9:
                try:
                    rp = requests.post(
                        f'{pressai_url}/api/gmail/prepare-article',
                        params={'message_id': msg_id, 'account_id': account_id},
                        headers=headers,
                        timeout=30
                    )
                    if rp.status_code == 200:
                        prepared_data = rp.json()
                        logger.info(f'GmailSource prepare-article OK dla {sender[:30]}')
                except Exception as e:
                    logger.warning(f'GmailSource prepare-article error: {e}')

            candidate = self._message_to_candidate(msg, sender_info, prepared_data)
            candidates.append(candidate)

        self._save_seen()
        logger.info(f'GmailSource: {len(candidates)} nowych kandydatow')
        return candidates

    def _message_to_candidate(self, msg: dict, sender_info: dict, prepared: dict = None) -> ContentCandidate:
        """Buduje ContentCandidate z maila + opcjonalnych danych prepare-article."""
        msg_id = msg.get('id', '')
        eid = hashlib.md5(msg_id.encode()).hexdigest()

        # Tresc: z prepare-article jesli dostepna, inaczej snippet
        source_text = ''
        images = []
        if prepared:
            source_text = prepared.get('source_text', '')
            images = prepared.get('images', [])
        if not source_text:
            source_text = msg.get('snippet', '')

        return ContentCandidate(
            id=eid,
            source=f"gmail:{sender_info['name']}",
            portal=sender_info.get('portal', self.portal),
            title=msg.get('subject', '(brak tematu)'),
            summary=source_text[:500],
            content_url=f"https://mail.google.com/mail/u/0/#inbox/{msg_id}",
            metadata={
                'sender': msg.get('from', ''),
                'received_at': msg.get('date', ''),
                'message_id': msg_id,
                'account_id': msg.get('account_id', ''),
                'pressai_prepared': bool(prepared),
                'images': images,  # obrazki wyciagniete przez PressAI
                'section': 'Współpracownicy',
                'auto_draft': sender_info.get('priority', 0) >= 9  # auto WP draft dla P0
            },
            priority=sender_info['priority']
        )

    def prepare_article(self, message_id: str) -> Optional[dict]:
        """Wywołaj endpoint POST /api/gmail/prepare-article w PressAI."""
        token = self._get_token()
        if not token:
            self.logger.error("GmailSource: brak tokenu PRESSAI_JWT_USER / PRESSAI_JWT")
            return None

        headers = {'Authorization': f'Bearer {token}'}
        account_id = self.account_id
        if not account_id:
            try:
                r = requests.get(f'{self.pressai_url}/api/gmail/accounts', headers=headers, timeout=10)
                if r.status_code == 200:
                    accounts = r.json().get('accounts', [])
                    if accounts:
                        account_id = accounts[0]['id']
            except Exception as e:
                self.logger.error(f"GmailSource accounts lookup error: {e}")

        if not account_id:
            return None

        try:
            rp = requests.post(
                f'{self.pressai_url}/api/gmail/prepare-article',
                params={'message_id': message_id, 'account_id': account_id},
                headers=headers,
                timeout=60
            )
            if rp.status_code == 200:
                return rp.json()
        except Exception as e:
            self.logger.error(f"GmailSource prepare_article error dla {message_id}: {e}")

        return None

    def health_check(self) -> bool:
        """Sprawdź połączenie z PressAI Gmail API."""
        token = self._get_token()
        if not token:
            return False
        try:
            r = requests.get(f"{self.pressai_url}/api/gmail/accounts", headers={'Authorization': f'Bearer {token}'}, timeout=10)
            return r.status_code == 200
        except Exception:
            return False
