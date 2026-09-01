"""
GmailSource v1.0 — Gmail source via PressAI API
Monitoruje skrzynkę tobroz@gmail.com przez PressAI backend (https://press.impresjapr.pl/api/gmail).
Priorytetowi nadawcy: WEI, Cezary Rudiński, Arkadiusz Bińczyk, Biały Kruk.
media-dispatch | media-dev-30 | 01.09.2026
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional, Union
import urllib.request
import urllib.parse
import urllib.error

from agents.base.worker_base import SourcePlugin, ContentCandidate


class GmailSource(SourcePlugin):
    """Gmail źródło — monitoruje skrzynkę przez PressAI Gmail API."""
    name = 'gmail'

    # Priorytetowi nadawcy i ich priorytety (P0 = 8-10)
    PRIORITY_SENDERS = {
        'wei.org.pl': {'name': 'WEI', 'priority': 9, 'portal': 'kurier365'},
        'bialykruk.pl': {'name': 'Biały Kruk', 'priority': 8, 'portal': 'kurier365'},
        'rudinski': {'name': 'Cezary Rudiński', 'priority': 9, 'portal': 'kurier365'},
        'rudzinski': {'name': 'Cezary Rudiński', 'priority': 9, 'portal': 'kurier365'},
        'binczyk': {'name': 'Arkadiusz Bińczyk', 'priority': 8, 'portal': 'kurier365'},
        'arkadiusz.binczyk': {'name': 'Arkadiusz Bińczyk', 'priority': 8, 'portal': 'kurier365'},
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
            token:            JWT token PressAI (jeśli None, czyta z env PRESSAI_JWT / PRESSAI_TOKEN)
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
        return self.token or os.environ.get('PRESSAI_JWT') or os.environ.get('PRESSAI_TOKEN')

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

    def _resolve_account_id(self, token: str) -> Optional[int]:
        """Automatycznie znajdź account_id dla danego adresu w PressAI."""
        if self.account_id:
            return self.account_id

        url = f"{self.pressai_url}/api/gmail/accounts"
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'User-Agent': 'media-dispatch/GmailSource-1.0'
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    accounts = data.get('accounts', [])
                    for acc in accounts:
                        if self.account_email and self.account_email.lower() in acc.get('email', '').lower():
                            self.account_id = acc.get('id')
                            self.logger.info(f"Wykryto Gmail account_id={self.account_id} dla {acc.get('email')}")
                            return self.account_id
                    if accounts:
                        self.account_id = accounts[0].get('id')
                        self.logger.info(f"Użyto domyślnego Gmail account_id={self.account_id} ({accounts[0].get('email')})")
                        return self.account_id
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania kont Gmail z PressAI: {e}")

        return None

    def fetch(self) -> List[ContentCandidate]:
        """Pobierz nowe maile przez PressAI Gmail API."""
        token = self._get_token()
        if not token:
            self.logger.warning("GmailSource: brak tokenu PRESSAI_JWT — pomijam pobieranie maili")
            return []

        account_id = self._resolve_account_id(token)
        if not account_id:
            self.logger.warning(f"GmailSource: brak aktywnego konta Gmail ({self.account_email}) w PressAI")
            return []

        days = max(1, (self.hours_back + 23) // 24)
        query = f"in:inbox newer_than:{days}d"
        params = urllib.parse.urlencode({
            'account_id': account_id,
            'q': query,
            'max_results': self.max_results
        })
        url = f"{self.pressai_url}/api/gmail/messages?{params}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'User-Agent': 'media-dispatch/GmailSource-1.0'
        }

        raw_messages = []
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    raw_messages = data.get('messages', [])
        except urllib.error.HTTPError as he:
            if he.code == 401:
                self.logger.error("GmailSource: PressAI 401 Unauthorized — token nieprawidłowy lub wymagana reautoryzacja Gmail")
            else:
                self.logger.error(f"GmailSource HTTP Error {he.code}: {he.reason}")
            return []
        except Exception as e:
            self.logger.error(f"GmailSource: błąd pobierania wiadomości: {e}")
            return []

        candidates = []
        for msg in raw_messages:
            from_addr = msg.get('from', '')
            sender_info = self._detect_sender(from_addr)
            if not sender_info:
                continue

            msg_id = str(msg.get('id', ''))
            if not msg_id or msg_id in self._seen:
                continue

            self._seen.add(msg_id)
            candidate = self._message_to_candidate(msg, sender_info)
            candidates.append(candidate)

        self._save_seen()
        self.logger.info(f"GmailSource: pobrano {len(raw_messages)} wiadomości, znaleziono {len(candidates)} nowych kandydatów.")
        return candidates

    def _message_to_candidate(self, msg: dict, sender_info: dict) -> ContentCandidate:
        """Konwertuje wiadomość Gmail na obiekt ContentCandidate."""
        msg_id = str(msg.get('id', msg.get('message_id', hash(msg.get('subject', '')))))
        eid = hashlib.md5(msg_id.encode('utf-8')).hexdigest()

        portal_target = sender_info.get('portal', self.portal)
        if portal_target == 'kurier365':
            portal_target = 'kurier365.pl'

        subject = msg.get('subject') or '(brak tematu)'
        snippet = msg.get('snippet') or msg.get('body') or ''

        return ContentCandidate(
            id=eid,
            source=f"gmail:{sender_info['name']}",
            portal=portal_target,
            title=subject,
            summary=snippet[:500],
            content_url=f"https://mail.google.com/mail/u/0/#inbox/{msg_id}",
            raw_content=msg.get('body') or snippet,
            metadata={
                'sender': msg.get('from', ''),
                'received_at': msg.get('date', ''),
                'message_id': msg_id,
                'pressai_prepared': False,
                'section': 'Współpracownicy',
                'has_attachments': msg.get('has_attachments', False),
                'labels': msg.get('labels', []),
                'account_id': self.account_id,
                'author': sender_info['name'],
                'requires_review': sender_info.get('requires_review', True)
            },
            priority=sender_info.get('priority', 8)
        )

    def prepare_article(self, message_id: str) -> Optional[dict]:
        """Wywołaj endpoint POST /api/gmail/prepare-article w PressAI."""
        token = self._get_token()
        if not token:
            self.logger.error("GmailSource: brak tokenu PRESSAI_JWT")
            return None

        account_id = self._resolve_account_id(token)
        if not account_id:
            return None

        params = urllib.parse.urlencode({
            'message_id': message_id,
            'account_id': account_id
        })
        url = f"{self.pressai_url}/api/gmail/prepare-article?{params}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'User-Agent': 'media-dispatch/GmailSource-1.0'
        }
        try:
            req = urllib.request.Request(url, data=b'', headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            self.logger.error(f"GmailSource prepare_article error dla {message_id}: {e}")

        return None

    def health_check(self) -> bool:
        """Sprawdź połączenie z PressAI Gmail API."""
        token = self._get_token()
        if not token:
            return False
        try:
            url = f"{self.pressai_url}/api/gmail/accounts"
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
                'User-Agent': 'media-dispatch/GmailSource-1.0'
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False
