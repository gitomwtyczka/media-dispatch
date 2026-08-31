# agents/base — Plugin-based Worker Architecture

> media-dispatch | media-dev-architect | 31.08.2026

## Filozofia

Każdy worker składa się z dwóch warstw wejściowych:

1. **Sources** (trwałe) — Gmail, RSS, Newseria, API
2. **Trend Signals** (dynamiczne) — Content Radar (LIVE), Google Trends, Social

Worker decyduje jak połączyć te strumienie i co zrobić z kandydatami.

## Struktura

```
agents/base/
├── worker_base.py          # Abstrakcyjna baza: WorkerBase, SourcePlugin, TrendSignal, ContentCandidate
├── sources/
│   ├── gmail_source.py      # Gmail + PressAI API (whitelist nadawców)
│   ├── newseria_source.py   # Newseria (eco-bias gate)
│   └── (rss_source)         # RSSSource jest w gmail_source.py
└── trend_signals/
    ├── content_radar_signal.py    # ✅ LIVE — radar.impresjapr.pl
    ├── google_trends_signal.py    # Placeholder (Content Radar już to obsługuje)
    └── social_trends_signal.py    # Placeholder
```

## Klasy bazowe

### `ContentCandidate` — wspólna waluta systemu

```python
@dataclass
class ContentCandidate:
    id: str           # unikalny ID
    source: str       # 'gmail' | 'rss' | 'newseria' | ...
    portal: str       # 'kurier365.pl' | 'prawy.pl' | 'biznesciti.com'
    title: str        # tytuł roboczy
    summary: str      # resume max 300 zn
    trend_score: float = 0.0   # 0-1, z Content Radar
    priority: int = 5          # 1-10
    status: str = 'new'        # new | approved | rejected | postponed
```

### `SourcePlugin` — interfejs źródła

```python
class MojSource(SourcePlugin):
    name = 'moj_source'
    portal = 'kurier365.pl'

    def fetch(self) -> List[ContentCandidate]:
        # Pobierz dane, zwróć listę
        return [...]
```

### `TrendSignal` — interfejs sygnału trendu

```python
class MojSignal(TrendSignal):
    name = 'moj_signal'

    def get_trending_topics(self, category=None, geo='PL') -> List[dict]:
        # Zwróć: [{'topic': str, 'score': float 0-1, 'source': str}]
        return [...]
```

### `WorkerBase` — orkiestrator

```python
class MojWorker(WorkerBase):
    def __init__(self):
        super().__init__(config)
        self.add_source(GmailSource(...))
        self.add_trend_signal(ContentRadarSignal(jwt_token='eyJ...'))

    def process(self, candidate: ContentCandidate) -> dict:
        # Wyślij do Redaktora lub PressAI
        return {'status': 'sent'}

# Uruchomienie:
worker = MojWorker()
candidates = worker.run()  # zbierz + wzbogac o trendy + sortuj
```

## Sygnały trendów

### `ContentRadarSignal` (LIVE)

| Para | Wartość |
|------|--------|
| URL | `https://radar.impresjapr.pl` |
| Endpoint | `GET /api/v1/trending/global?limit=50&category=X` |
| Auth | JWT Bearer token |
| Wymagany plan | Pro lub Enterprise |
| Odświeżanie | co 15 min (APScheduler) |
| Źródła | Google Trends, Twitter/X, TikTok, Instagram, YouTube, Reddit, FB, LinkedIn, RSS |

Konfiguracja:
```bash
export CONTENT_RADAR_JWT=eyJ...  # JWT z konta Content Radar
python worker.py --health
```

### Viral Score formula (Content Radar)

```
views * 0.1 + likes * 1.0 + shares * 3.0 + comments * 2.0
+ Google Trends boost (+10 jeśli interest > 70)
```

## Jak dodać nowego workera

1. Utwórz `agents/nazwa-worker/worker.py`
2. Dziedzicz z `WorkerBase`
3. Dodaj źródła przez `self.add_source()`
4. Dodaj sygnały trendów przez `self.add_trend_signal()`
5. Zaimplementuj `process()`

Przykład: [`agents/kurier365-worker/worker.py`](../kurier365-worker/worker.py)

## Jak dodać nowe źródło

1. Utwórz `agents/base/sources/nowe_source.py`
2. Dziedzicz z `SourcePlugin`
3. Zaimplementuj `fetch()` zwracając `List[ContentCandidate]`
4. Dodaj do workera: `self.add_source(NoweSource(...))`

## Obsługiwane portale (docelowo)

| Portal | Worker | Status |
|--------|--------|--------|
| kurier365.pl | `kurier365-worker` | ✅ skeleton v0.1 |
| prawy.pl | `prawy-studio-worker` | ✅ produkcja |
| biznesciti.com | *(planowany)* | 🔴 Faza 2 |
