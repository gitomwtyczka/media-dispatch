#!/usr/bin/env python3
"""agents/kurier365-worker/worker.py

Kurier365Worker — instancja WorkerBase dla kurier365.pl
media-dispatch | media-dev-architect | 31.08.2026

Architektura rozszerzalna (plugin-based):
  Sources:
    - Gmail (tobroz@gmail.com) — Rudiński, Bińczyk, WEI, Biały Kruk
    - RSS (UOKiK, Nauka w Polsce, PAP, ISBNews)
    - Newseria (gospodarka, konsument, prawo)
  Trend Signals:
    - ContentRadarSignal (radar.impresjapr.pl — LIVE)
    - GoogleTrendsSignal (fallback placeholder)
    - SocialTrendsSignal (fallback placeholder)

CLI:
  python worker.py --health               # status wszystkich komponentów
  python worker.py --run                  # zbierz kandydatów
  python worker.py --run --top 10         # pokaż top-N kandydatów
  python worker.py --run --json           # output jako JSON

Status wdrożenia:
  v0.1 skeleton — wszystkie źródła w placeholder mode (fetch zwraca []).
  Content Radar LIVE — aktywny gdy CONTENT_RADAR_JWT ustawiony.
  Aktywacja źródeł: dodaj token PressAI i dane logowania w CONFIG.
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
from agents.base.sources.gmail_source import GmailSource, RSSSource
from agents.base.sources.newseria_source import NewseriaSource
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
# WORKER
# ---------------------------------------------------------------------------


class Kurier365Worker(WorkerBase):
    """Orkiestrator contentu dla kurier365.pl.

    Pipeline:
        1. collect_candidates() — zbiera z Gmail + RSS + Newseria
        2. enrich_with_trends() — ocenia trend_score przez Content Radar LIVE
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
        content_radar_jwt = effective_config.get('content_radar_jwt')
        content_radar_url = effective_config.get('content_radar_url', 'https://radar.impresjapr.pl')

        # ------------------------------------------------------------------
        # Źródła (Sources)
        # ------------------------------------------------------------------

        # Gmail — biała lista nadawców z redakcji kurier365.pl
        self.add_source(GmailSource(
            portal='kurier365.pl',
            pressai_url=pressai_url,
            token=pressai_token,
            allowed_senders=[
                # Cezary Rudiński — wymaga review przed publikacją
                {'email': '*rudzinski*', 'name': 'Cezary Rudiński', 'requires_review': True},
                # Arkadiusz Bińczyk — może iść bezpośrednio do draftu
                {'email': '*binczyk*', 'name': 'Arkadiusz Bińczyk', 'requires_review': False},
                # Instytucje — automatyczna akceptacja
                {'email': '*@wei.org.pl', 'name': 'WEI', 'requires_review': False},
                {'email': '*@bialykruk.pl', 'name': 'Biały Kruk', 'requires_review': False},
            ]
        ))

        # RSS — instytucjonalne źródła (urzędy, nauka, depesze)
        self.add_source(RSSSource(
            portal='kurier365.pl',
            pressai_url=pressai_url,
            token=pressai_token,
            feeds=[
                # Priorytet 9 — komunikaty UOKiK (prawo konsumenta)
                {'url': 'https://uokik.gov.pl/rss.xml', 'category': 'prawo-konsumenta', 'priority': 9},
                # Priorytet 8 — PAP (ogólnopolskie)
                {'url': 'https://www.pap.pl/rss.xml', 'category': 'kraj', 'priority': 8},
                # Priorytet 7 — nauka
                {'url': 'https://naukawpolsce.pl/rss', 'category': 'nauka', 'priority': 7},
                # Priorytet 7 — ISBNews (biznes/finanse)
                {'url': 'https://isbnews.pl/rss', 'category': 'finanse', 'priority': 7},
            ]
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
  python worker.py --run --json

Zmienne środowiskowe:
  PRESSAI_JWT          — JWT token PressAI
  NEWSERIA_USER        — login Newseria
  NEWSERIA_PASS        — hasło Newseria
  CONTENT_RADAR_JWT    — JWT token Content Radar (radar.impresjapr.pl)
"""
    )
    parser.add_argument('--health', action='store_true', help='Status komponentów workera')
    parser.add_argument('--run', action='store_true', help='Zbierz kandydatów ze źródeł')
    parser.add_argument('--top', type=int, default=10, metavar='N', help='Pokaż top-N kandydatów (domyślnie 10)')
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
        return

    if args.run:
        candidates = worker.run()
        top = candidates[:args.top]

        if args.json:
            print(json.dumps([c.to_dict() for c in top], indent=2, ensure_ascii=False))
        else:
            print(f"\nZnaleziono {len(candidates)} kandydatów. Top-{len(top)}:\n")
            for c in top:
                trend = f" trend={c.trend_score:.2f}" if c.trend_score > 0 else ""
                print(f"  [{c.priority:2d}] [{c.source:10s}]{trend} {c.title[:70]}")
            if len(candidates) > args.top:
                print(f"  ... i {len(candidates) - args.top} więcej")
        return

    parser.print_help()


if __name__ == '__main__':
    main()
