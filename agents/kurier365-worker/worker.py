#!/usr/bin/env python3
"""agents/kurier365-worker/worker.py

Kurier365Worker — instancja WorkerBase dla kurier365.pl
media-dispatch | media-dev-30 | 01.09.2026

Architektura rozszerzalna (plugin-based):
  Sources:
    - Gmail (tobroz@gmail.com) — Rudiński, Bińczyk, WEI, Biały Kruk (via PressAI API)
    - FeedCrawler (https://crawler.impresjapr.pl — 13k+ RSS feedów) — LIVE (ogólne + działy: nauka, geopolityka)
    - Newseria (gospodarka, konsument, prawo)
  Trend Signals:
    - GeoRelevanceSignal (waga PL/EU/Global vs Low relevance) — LIVE
    - ContentRadarSignal (radar.impresjapr.pl — LIVE)
    - GoogleTrendsSignal (fallback placeholder)
    - SocialTrendsSignal (fallback placeholder)

CLI:
  python worker.py --health               # status wszystkich komponentów
  python worker.py --run                  # zbierz kandydatów
  python worker.py --run --top 10         # pokaż top-N kandydatów
  python worker.py --run --sheets         # zapisz do Google Sheets
  python worker.py --run --json           # output jako JSON

Status wdrożenia:
  GmailSource v1.0 — LIVE (PressAI Gmail API, tobroz@gmail.com).
  FeedCrawlerSource v1.2 — LIVE (13k+ feedów, crawler.impresjapr.pl, działy tematyczne).
  GeoRelevanceSignal v1.0 — LIVE (priorytetyzacja PL/EU/US-biznes).
  Content Radar LIVE — aktywny gdy CONTENT_RADAR_JWT ustawiony.
  Discord notifications — aktywne gdy DISCORD_WEBHOOK_KURIER365 ustawiony.
  Google Sheets — aktywny gdy GOOGLE_SA_FILE ustawiony.
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Dodaj root projektu do Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.base.worker_base import WorkerBase, ContentCandidate
from agents.base.sources.gmail_source import GmailSource
from agents.base.sources.feed_crawler_source import FeedCrawlerSource
from agents.base.sources.newseria_source import NewseriaSource
from agents.base.trend_signals.geo_relevance_signal import GeoRelevanceSignal
from agents.base.trend_signals.content_radar_signal import ContentRadarSignal
from agents.base.trend_signals.google_trends_signal import GoogleTrendsSignal, SocialTrendsSignal

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent / 'worker.log',
            encoding='utf-8'
        ),
    ]
)
log = logging.getLogger('kurier365-worker')

# ---------------------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------------------

CONFIG = {
    'portal': 'kurier365.pl',
    'pressai_url': 'https://press.impresjapr.pl',
    'feed_crawler_url': os.environ.get('FEED_CRAWLER_URL', 'https://crawler.impresjapr.pl'),
    'state_file': str(Path(__file__).parent / 'kurier365_state.json'),

    # Token PressAI — uzupełnij przez docker exec lub secrets manager
    'pressai_token': os.environ.get('PRESSAI_JWT'),  # lub ustaw wprost

    # Dane logowania Newseria — uzupełnij gdy konto gotowe
    'newseria_username': os.environ.get('NEWSERIA_USER'),
    'newseria_password': os.environ.get('NEWSERIA_PASS'),

    # Content Radar JWT — LIVE na radar.impresjapr.pl
    # Uzyskaj przez: POST https://radar.impresjapr.pl/api/v1/auth/login
    # Wymaga planu Pro lub Enterprise w Content Radar.
    'content_radar_jwt': os.environ.get('CONTENT_RADAR_JWT'),
    'content_radar_url': 'https://radar.impresjapr.pl',
}

# ---------------------------------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------------------------------

def write_candidates_to_sheets(candidates: list, spreadsheet_id: str = '1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig') -> bool:
    """Zapisuje kandydatów do zakładki Kandydaci w Google Sheets."""
    import os
    from datetime import datetime
    try:
        from google.oauth2.service_account import Credentials
        import gspread
    except ImportError:
        log.warning("Brak bibliotek google-auth / gspread — pomijam zapis do Sheets")
        return False

    sa_file = os.getenv('GOOGLE_SA_FILE', '/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json')
    if not os.path.exists(sa_file):
        log.warning(f"Brak pliku service account ({sa_file}) — pomijam zapis do Sheets")
        return False

    try:
        creds = Credentials.from_service_account_file(
            sa_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(spreadsheet_id)
        ws = sh.worksheet('Kandydaci')

        now = datetime.now().strftime('%d.%m.%Y %H:%M')
        rows = []
        for c in candidates:
            rows.append([
                c.id,
                now,
                c.source,
                c.portal,
                c.metadata.get('category', ''),
                f'P{max(0, 10-c.priority)}',
                c.title,
                (c.summary or '')[:200],
                c.content_url,
                c.metadata.get('author', ''),
                str(c.metadata.get('geo_relevance_score', '')),
                'nowy',  # Status
                '', '', '', '', '',  # puste pola
                c.metadata.get('geo_relevance', '')
            ])
        if rows:
            ws.append_rows(rows, value_input_option='USER_ENTERED')
            log.info(f'Zapisano {len(rows)} kandydatów do Sheets')
        return True
    except Exception as e:
        log.error(f'Błąd zapisu do Sheets: {e}')
        return False


# ---------------------------------------------------------------------------
# WORKER
# ---------------------------------------------------------------------------


class Kurier365Worker(WorkerBase):
    """Orkiestrator contentu dla kurier365.pl.

    Pipeline:
        1. collect_candidates() — zbiera z Gmail + FeedCrawler + Newseria
        2. enrich_with_trends() — ocenia trend_score i geo_relevance
        3. Kandydaci sortowani (priority DESC, trend_score DESC)
        4. process() — wysyła top kandydatów do Redaktora Naczelnego (Telegram bot)

    Dodawanie nowego źródła:
        from agents.base.sources.moj_source import MojSource
        self.add_source(MojSource(portal='kurier365.pl', ...))

    Dodawanie nowego sygnału trendów:
        from agents.base.trend_signals.moj_signal import MojSignal
        self.add_trend_signal(MojSignal(api_url=...))
    """

    def __init__(self, config: dict = None):
        """
        Args:
            config: nadpisz domyślną konfigurację CONFIG (opcjonalne).
        """
        effective_config = {**CONFIG, **(config or {})}
        super().__init__(effective_config)

        pressai_url = effective_config['pressai_url']
        pressai_token = effective_config.get('pressai_token')
        feed_crawler_url = effective_config.get('feed_crawler_url', 'https://crawler.impresjapr.pl')
        content_radar_jwt = effective_config.get('content_radar_jwt')
        content_radar_url = effective_config.get('content_radar_url', 'https://radar.impresjapr.pl')

        # ------------------------------------------------------------------
        # Źródła (Sources)
        # ------------------------------------------------------------------

        # Gmail — monitorowanie skrzynki przez PressAI API (tobroz@gmail.com)
        self.add_source(GmailSource(
            pressai_url=pressai_url,
            portal='kurier365',
            token=pressai_token,
            hours_back=24,
            state_file='/tmp/gmail_state_kurier365.json'
        ))

        # Feed Crawler — 13k+ źródeł RSS (UOKiK, PAP, Nauka, ISBNews, Biznes, etc.)
        self.add_source(FeedCrawlerSource(
            api_url=feed_crawler_url,
            portal='kurier365',
            categories=['prawo', 'konsument', 'uokik', 'gospodark', 'nauka', 'pap', 'biznes', 'finans', 'podatk', 'rynek', 'wnp', 'inflacj', 'cen', 'pols'],
            hours_back=6,
            limit=50,
            state_file='/tmp/feed_crawler_state_kurier365.json'
        ))

        # Dział NAUKA (Tier 1 Scientific + popularnonaukowe PL)
        self.add_source(FeedCrawlerSource(
            api_url=feed_crawler_url,
            portal='kurier365',
            departments=['science-high-tech', 'health-biotech'],
            limit=20,
            state_file='/tmp/fc_kurier365_science.json'
        ))

        # Geostrategia periodyczna (Chiny/Indie/Rosja + obrona)
        self.add_source(FeedCrawlerSource(
            api_url=feed_crawler_url,
            portal='kurier365',
            departments=['defence-geopolitics'],
            limit=10,
            state_file='/tmp/fc_kurier365_geo.json'
        ))

        # Newseria — agencja B2B z Eco-Bias Gate
        self.add_source(NewseriaSource(
            portal='kurier365.pl',
            username=effective_config.get('newseria_username'),
            password=effective_config.get('newseria_password'),
            categories=['gospodarka', 'konsument', 'prawo', 'nauka', 'turystyka']
        ))

        # ------------------------------------------------------------------
        # Sygnały trendów
        # ------------------------------------------------------------------

        # GeoRelevanceSignal — waży relevancję PL/EU/US-biznes vs low relevance
        self.add_trend_signal(GeoRelevanceSignal())

        # Content Radar — LIVE integracja z radar.impresjapr.pl
        # Aktywna gdy CONTENT_RADAR_JWT jest ustawiony w środowisku.
        # Wymaga planu Pro lub Enterprise w Content Radar.
        self.add_trend_signal(ContentRadarSignal(
            api_url=content_radar_url,
            jwt_token=content_radar_jwt,  # None = tryb placeholder
        ))

        # GoogleTrends + Social — fallback placeholder
        # (Content Radar już agreguje te dane — te pluginy jako backup)
        self.add_trend_signal(GoogleTrendsSignal())
        self.add_trend_signal(SocialTrendsSignal())

    def write_to_sheets(self, candidates: list, spreadsheet_id: str = '1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig') -> bool:
        """Zapisuje kandydatów do Google Sheets."""
        return write_candidates_to_sheets(candidates, spreadsheet_id=spreadsheet_id)

    def process(self, candidate: ContentCandidate) -> dict:
        """Wyślij kandydata do Redaktora Naczelnego (Telegram bot).

        TODO: Faza 2 — integracja z redaktor-naczelny-bot:
            POST {telegram_bot_url}/api/candidate
            Payload: candidate.to_dict() + przyciski inline:
            [Akceptuj] [Odrzuć] [Odroc D+1] [Odroc D+7] [Uwagi]

        Args:
            candidate: zatwierdzony kandydat do wysłania

        Returns:
            Dict z wynikiem: {'status': str, 'candidate_id': str}
        """
        log.info("process() placeholder: candidate %s '%s'", candidate.id, candidate.title[:50])
        return {'status': 'placeholder_sent_to_editor', 'candidate_id': candidate.id}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='kurier365-worker — Content pipeline dla kurier365.pl',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  python worker.py --health
  python worker.py --run
  python worker.py --run --top 5
  python worker.py --run --sheets
  python worker.py --run --json

Zmienne środowiskowe:
  FEED_CRAWLER_URL            — URL API Feed Crawler (domyślnie: https://crawler.impresjapr.pl)
  PRESSAI_JWT                 — JWT token PressAI
  NEWSERIA_USER               — login Newseria
  NEWSERIA_PASS               — hasło Newseria
  CONTENT_RADAR_JWT           — JWT token Content Radar (radar.impresjapr.pl)
  DISCORD_WEBHOOK_KURIER365   — Webhook URL Discord dla powiadomień
  DISCORD_WEBHOOK_PRIORITY    — Webhook URL Discord dla powiadomień priorytetowych (P0/Gmail)
  GOOGLE_SA_FILE              — Ścieżka do klucza Service Account Google
"""
    )
    parser.add_argument('--health', action='store_true', help='Status komponentów workera')
    parser.add_argument('--run', action='store_true', help='Zbierz kandydatów ze źródeł')
    parser.add_argument('--top', type=int, default=10, metavar='N', help='Pokaż top-N kandydatów (domyślnie 10)')
    parser.add_argument('--sheets', action='store_true', help='Zapisz zebranych kandydatów do Google Sheets')
    parser.add_argument('--json', action='store_true', help='Output jako JSON')
    args = parser.parse_args()

    worker = Kurier365Worker()

    if args.health:
        status = worker.health_check()
        if args.json:
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            print(f"Worker: {status['worker']}")
            print(f"State file: {status['state_file']}")
            print("Sources:")
            for s in status['sources']:
                icon = '✅' if s['healthy'] else '❌ (placeholder)'
                print(f"  {icon} {s['name']}")
            signals = status['trend_signals']
            print(f"Trend signals: {', '.join(signals) if signals else 'none'}")
            cr_jwt = os.environ.get('CONTENT_RADAR_JWT')
            print(f"Content Radar JWT: {'SET (✅ LIVE)' if cr_jwt else 'NOT SET (⚠️ trends disabled)'}")
            discord_url = os.environ.get('DISCORD_WEBHOOK_KURIER365')
            print(f"Discord Webhook: {'SET (✅ LIVE)' if discord_url else 'NOT SET (⚠️ discord disabled)'}")
            priority_url = os.environ.get('DISCORD_WEBHOOK_PRIORITY')
            print(f"Discord Priority Webhook: {'SET (✅ LIVE)' if priority_url else 'NOT SET'}")
            sa_file = os.environ.get('GOOGLE_SA_FILE', '/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json')
            sa_ok = os.path.exists(sa_file)
            print(f"Google SA File: {'SET (✅ FOUND)' if sa_ok else f'NOT FOUND ({sa_file})'}")
        return

    if args.run:
        candidates = worker.run()
        top = candidates[:args.top]

        # Discord notify dla top kandydatów (priority >= 6 lub Gmail)
        discord_sent = 0
        for c in top:
            if c.priority >= 6 or c.source.startswith('gmail:'):
                if worker.notify_discord(c):
                    discord_sent += 1

        # Zapis do Google Sheets jeśli włączono flagę --sheets
        if args.sheets:
            write_candidates_to_sheets(candidates)

        if args.json:
            print(json.dumps([c.to_dict() for c in top], indent=2, ensure_ascii=False))
        else:
            print(f"\nZnaleziono {len(candidates)} kandydatów. Top-{len(top)}:\n")
            for c in top:
                trend = f" trend={c.trend_score:.2f}" if c.trend_score > 0 else ""
                geo = f" [{c.metadata.get('geo_relevance', '')}]" if 'geo_relevance' in c.metadata else ""
                print(f"  [{c.priority:2d}] [{c.source:20s}]{trend}{geo} {c.title[:70]}")
            if len(candidates) > args.top:
                print(f"  ... i {len(candidates) - args.top} więcej")
            if discord_sent > 0:
                print(f"\nWysłano {discord_sent} powiadomień do Discord.")
        return

    parser.print_help()


if __name__ == '__main__':
    main()
