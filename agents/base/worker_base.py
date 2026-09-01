\"\"\"agents/base/worker_base.py

Plugin-based Worker Architecture — abstrakcyjna baza dla wszystkich workerów media-dispatch.
media-dispatch | media-dev-architect | 31.08.2026
\"\"\"
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import json
import logging
from pathlib import Path


@dataclass
class ContentCandidate:
    \"\"\"Kandydat do publikacji — wspólna waluta systemu.

    Przepływa przez cały pipeline: Source -> TrendSignal -> Worker -> Redaktor Naczelny.
    \"\"\"
    id: str                          # unikalny ID (np. hash URL lub message_id)
    source: str                      # 'gmail' | 'rss' | 'trends' | 'yt' | 'newseria'
    portal: str                      # 'prawy.pl' | 'kurier365.pl' | 'biznesciti.com'
    title: str                       # tytuł roboczy
    summary: str                     # resume max 300 znaków
    content_url: Optional[str] = None    # link do oryginału
    raw_content: Optional[str] = None    # surowa treść jeśli pobrana
    trend_score: float = 0.0             # 0-1, 0 = brak sygnału trendu
    priority: int = 5                    # 1-10, 10 = pilne
    metadata: dict = field(default_factory=dict)  # pola specyficzne dla źródła
    status: str = 'new'              # new | approved | rejected | postponed

    def to_dict(self) -> dict:
        \"\"\"Serializacja do JSON-friendly dict.\"\"\"
        return {
            'id': self.id,
            'source': self.source,
            'portal': self.portal,
            'title': self.title,
            'summary': self.summary,
            'content_url': self.content_url,
            'raw_content': self.raw_content,
            'trend_score': self.trend_score,
            'priority': self.priority,
            'metadata': self.metadata,
            'status': self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ContentCandidate':
        \"\"\"Deserializacja z dict (stan z pliku JSON).\"\"\"
        return cls(**data)


class SourcePlugin(ABC):
    \"\"\"Bazowa klasa dla pluginów źródłowych.

    Każdy plugin odpowiada za jedno źródło danych (Gmail, RSS, Newseria, API).
    Pluginy są rejestrowane w WorkerBase.add_source().

    Implementacja:
        class MySource(SourcePlugin):
            name = 'my_source'
            portal = 'kurier365.pl'

            def fetch(self) -> List[ContentCandidate]:
                # pobierz dane, zbuduj ContentCandidate, zwróć listę
                return [...]
    \"\"\"
    name: str    # identyfikator źródła — musi być unikalny w ramach workera
    portal: str  # docelowy portal

    @abstractmethod
    def fetch(self) -> List[ContentCandidate]:
        \"\"\"Pobierz nowych kandydatów ze źródła.

        Returns:
            Lista ContentCandidate gotowych do dalszego przetwarzania.
        \"\"\"
        pass

    def health_check(self) -> bool:
        \"\"\"Sprawdź czy źródło jest dostępne.

        Override w implementacji aby weryfikować połączenie z API/feedem.
        \"\"\"
        return True


class TrendSignal(ABC):
    \"\"\"Bazowa klasa dla sygnałów trendów.

    Sygnały trendów wzbogacają ContentCandidate o trend_score.
    Są opcjonalne — WorkerBase działa bez nich.

    Placeholder pattern:
        Zaimplementuj klasę z get_trending_topics() zwracającym []
        gdy API nie jest jeszcze dostępne. Podmień na wywołanie API
        content-radar gdy będzie gotowe.
    \"\"\"
    name: str  # identyfikator sygnału

    @abstractmethod
    def get_trending_topics(self, category: str = None, geo: str = 'PL') -> List[dict]:
        \"\"\"Zwróć listę trendujących tematów.

        Args:
            category: opcjonalna kategoria tematyczna (np. 'biznes', 'polityka')
            geo:      kod geograficzny ISO (domyślnie 'PL')

        Returns:
            Lista dicts: [{'topic': str, 'score': float 0-1, 'source': str}]
        \"\"\"
        pass

    def enrich_candidate(self, candidate: ContentCandidate, topics: List[dict]) -> ContentCandidate:
        \"\"\"Wzbogac kandydata o trend_score na podstawie dopasowania tematów.

        Domyślna implementacja: bag-of-words matching tytułu z topic.
        Override w subklasie dla bardziej zaawansowanego scoringu.

        Args:
            candidate: kandydat do wzbogacenia
            topics:    lista trendujących tematów z get_trending_topics()

        Returns:
            Kandydat z zaktualizowanym trend_score (max z poprzedniego i nowego).
        \"\"\"
        if not topics:
            return candidate

        title_lower = candidate.title.lower()
        max_score = candidate.trend_score  # nie nadpisuj istniejącego wyższego score

        for topic in topics:
            topic_words = topic.get('topic', '').lower().split()
            if not topic_words:
                continue
            matches = sum(1 for word in topic_words if word in title_lower)
            score = (matches / len(topic_words)) * topic.get('score', 0.5)
            max_score = max(max_score, score)

        candidate.trend_score = round(max_score, 4)
        return candidate


class WorkerBase(ABC):
    \"\"\"Abstrakcyjna klasa bazowa dla wszystkich workerów media-dispatch.

    Architektura:
        WorkerBase
        ├── sources: List[SourcePlugin]      — skąd brać treści
        ├── trend_signals: List[TrendSignal] — jak oceniać trendy
        └── process(candidate)               — co zrobić z kandydatem

    Implementacja minimalnego workera:
        class MyWorker(WorkerBase):
            def process(self, candidate: ContentCandidate) -> dict:
                # wyślij do Redaktora Naczelnego, PressAI, etc.
                return {'status': 'sent'}

        worker = MyWorker({'state_file': 'worker_state.json'})
        worker.add_source(GmailSource(...))
        worker.add_trend_signal(GoogleTrendsSignal(...))
        candidates = worker.run()
    \"\"\"

    def __init__(self, config: dict):
        \"\"\"
        Args:
            config: słownik konfiguracyjny. Obsługiwane klucze:
                - state_file (str): ścieżka do pliku stanu JSON
        \"\"\"
        self.config = config
        self.sources: List[SourcePlugin] = []
        self.trend_signals: List[TrendSignal] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.state_file = Path(config.get('state_file', 'worker_state.json'))

    # ------------------------------------------------------------------
    # Plugin registration
    # ------------------------------------------------------------------

    def add_source(self, source: SourcePlugin) -> 'WorkerBase':
        \"\"\"Zarejestruj plugin źródłowy.

        Returns:
            self (fluent interface): worker.add_source(A).add_source(B)
        \"\"\"
        self.sources.append(source)
        self.logger.debug(\"Source registered: %s\", source.name)
        return self

    def add_trend_signal(self, signal: TrendSignal) -> 'WorkerBase':
        \"\"\"Zarejestruj sygnał trendów.

        Returns:
            self (fluent interface)
        \"\"\"
        self.trend_signals.append(signal)
        self.logger.debug(\"TrendSignal registered: %s\", signal.name)
        return self

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def collect_candidates(self) -> List[ContentCandidate]:
        \"\"\"Zbierz kandydatów ze wszystkich zarejestrowanych źródeł.

        Błędy pojedynczego source są logowane i pomijane
        (graceful degradation — jeden broken source nie blokuje pipeline).

        Returns:
            Połączona lista kandydatów ze wszystkich źródeł.
        \"\"\"
        all_candidates: List[ContentCandidate] = []
        for source in self.sources:
            try:
                candidates = source.fetch()
                self.logger.info(\"Source %s: %d candidates\", source.name, len(candidates))
                all_candidates.extend(candidates)
            except Exception as e:
                self.logger.error(\"Source %s failed: %s\", source.name, e, exc_info=True)
        return all_candidates

    def enrich_with_trends(self, candidates: List[ContentCandidate]) -> List[ContentCandidate]:
        \"\"\"Wzbogac kandydatów o sygnały trendów i posortuj.

        Jeśli brak zarejestrowanych sygnałów — kandydaci wracają bez zmian.
        Sortowanie: (priority DESC, trend_score DESC).

        Args:
            candidates: lista kandydatów z collect_candidates()

        Returns:
            Posortowana lista kandydatów z zaktualizowanymi trend_score.
        \"\"\"
        if not self.trend_signals:
            return candidates

        # Zbierz wszystkie trendy
        trending: List[dict] = []
        for signal in self.trend_signals:
            try:
                topics = signal.get_trending_topics()
                self.logger.info(\"TrendSignal %s: %d topics\", signal.name, len(topics))
                trending.extend(topics)
            except Exception as e:
                self.logger.error(\"TrendSignal %s failed: %s\", signal.name, e, exc_info=True)

        # Wzbogac każdego kandydata przez każdy sygnał
        for i, candidate in enumerate(candidates):
            for signal in self.trend_signals:
                try:
                    candidates[i] = signal.enrich_candidate(candidate, trending)
                except Exception as e:
                    self.logger.warning(\"enrich_candidate failed for %s: %s\", candidate.id, e)

        return sorted(
            candidates,
            key=lambda c: (c.priority, c.trend_score),
            reverse=True
        )

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def save_state(self, data: dict) -> None:
        \"\"\"Zapisz stan do pliku JSON.

        Tworzy katalog nadrzędny jeśli nie istnieje.
        \"\"\"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def load_state(self) -> dict:
        \"\"\"Wczytaj stan z pliku JSON.

        Returns:
            Dict ze stanem lub pusty dict jeśli plik nie istnieje.
        \"\"\"
        if self.state_file.exists():
            return json.loads(self.state_file.read_text(encoding='utf-8'))
        return {}

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def process(self, candidate: ContentCandidate) -> dict:
        \"\"\"Przetwórz kandydata (wyślij do Redaktora, generuj artykuł, etc.).

        Args:
            candidate: kandydat zatwierdzony do przetwarzania

        Returns:
            Dict z wynikiem (np. {'status': 'sent', 'telegram_msg_id': 123})
        \"\"\"
        pass

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def notify_discord(self, candidate: ContentCandidate,
                       webhook_url: str = None,
                       priority_webhook_url: str = None) -> bool:
        \"\"\"Wysyła kandydata do Discord.
        - Każdy kandydat idzie na webhook_url (kanał ogólny)
        - Kandydaci P0 (priority>=8) LUB z Gmail idą TEZ na priority_webhook_url
        - Można być na obu kanałach jednocześnie (duplikacja OK)
        \"\"\"
        import os
        import requests

        general_url = webhook_url or os.getenv('DISCORD_WEBHOOK_KURIER365')
        priority_url = priority_webhook_url or os.getenv('DISCORD_WEBHOOK_PRIORITY')

        is_gmail = candidate.source.startswith('gmail:')
        is_p0 = candidate.priority >= 8
        is_priority = is_gmail or is_p0

        def _send(url, extra_content=''):
            if not url:
                return False
            geo = candidate.metadata.get('geo_relevance', 'unknown')
            priority = candidate.priority
            section = candidate.metadata.get('section', '')

            # Kolor embeda
            if is_gmail:
                color = 0xFFD700  # złoty — Gmail współpracownicy
            elif priority >= 8:
                color = 0xdc3545  # czerwony P0
            elif priority >= 6:
                color = 0xfd7e14  # pomarańczowy P1
            elif priority >= 4:
                color = 0xffc107  # żółty P2
            else:
                color = 0x1a73e8  # niebieski default

            emoji_source = '📧' if is_gmail else '📰'
            emoji_geo = {'🇵🇱': 'PL-high', '🇪🇺': 'EU', '🌐': 'global', '⬇️': 'low'}.get(geo, '🌐')
            section_badge = f' | 🔬 {section}' if section == 'Nauka' else f' | 🌐 {section}' if section else ''

            embed = {
                'title': candidate.title[:250],
                'url': candidate.content_url,
                'color': color,
                'fields': [
                    {'name': f'{emoji_source} Źródło', 'value': candidate.source, 'inline': True},
                    {'name': '🏷️ Portal', 'value': f'{candidate.portal}{section_badge}', 'inline': True},
                    {'name': '⚡ Priorytet', 'value': f'score: {priority}', 'inline': True},
                    {'name': '📝 Lead', 'value': (candidate.summary or 'brak')[:300], 'inline': False},
                ],
                'footer': {'text': f'media-dispatch • {candidate.metadata.get(\"published_at\", \"\")}'}
            }

            # Dla Gmail: specjalny nagłówek
            content = extra_content or f'**Nowy kandydat** | {candidate.portal}'
            if is_gmail:
                content = f'🔔 **PRIORYTET — współpracownik** | {candidate.metadata.get(\"sender\", \"\")}'
            elif is_p0:
                content = f'🔴 **PRIORYTET P0** | {candidate.portal}'

            try:
                r = requests.post(url, json={'content': content, 'embeds': [embed]}, timeout=10)
                return r.status_code in (200, 204)
            except Exception as e:
                self.logger.error(f'Discord notify error: {e}')
                return False

        results = []
        # Zawsze na kanał ogólny
        if general_url:
            results.append(_send(general_url))

        # Dodatkowo na kanał priorytetowy jeśli Gmail lub P0
        if is_priority and priority_url:
            results.append(_send(priority_url, extra_content=''))

        return any(results)

    # ------------------------------------------------------------------
    # Health & run
    # ------------------------------------------------------------------

    def health_check(self) -> dict:
        \"\"\"Zwróć status wszystkich komponentów workera.

        Returns:
            Dict z listą zarejestrowanych źródeł i sygnałów trendów.
        \"\"\"
        source_health = []
        for s in self.sources:
            try:
                ok = s.health_check()
            except Exception as e:
                ok = False
                self.logger.warning(\"Source health check failed for %s: %s\", s.name, e)
            source_health.append({'name': s.name, 'healthy': ok})

        return {
            'worker': self.__class__.__name__,
            'sources': source_health,
            'trend_signals': [t.name for t in self.trend_signals],
            'state_file': str(self.state_file),
        }

    def run(self) -> List[ContentCandidate]:
        \"\"\"Główna pętla: zbierz kandydatów ze wszystkich źródeł, wzbogac o trendy.

        Nie wywołuje process() — to zadanie orchestratora (kurier365-worker CLI
        lub redaktor-naczelny-bot).

        Returns:
            Posortowana lista kandydatów gotowych do review przez Redaktora.
        \"\"\"
        self.logger.info(\"[%s] Starting run...\", self.__class__.__name__)
        candidates = self.collect_candidates()
        self.logger.info(\"Collected %d candidates total\", len(candidates))
        enriched = self.enrich_with_trends(candidates)
        self.logger.info(\"Run complete. %d candidates ready for editor.\", len(enriched))
        return enriched
