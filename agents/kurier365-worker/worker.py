#!/usr/bin/env python3
"""agents/kurier365-worker/worker.py

Kurier365Worker — instancja WorkerBase dla kurier365.pl i biznesciti.com
media-dispatch | media-dev-36 | 01.09.2026

Architektura rozszerzalna (plugin-based):
  Sources:
    - Gmail (tobroz@gmail.com) — Rudiński, Bińczyk, WEI, Biały Kruk (via PressAI API)
    - FeedCrawler (https://crawler.impresjapr.pl — 13k+ RSS feedów) — LIVE (ogólne + działy: nauka, geopolityka)
    - Newseria (gospodarka, konsument, prawo)
  Trend Signals:
    - GeoRelevanceSignal (waga PL/EU/Global vs Low relevance) — LIVE
    - RadarEnricher (Content Radar viral_score boost per-portal) — LIVE
    - ContentRadarSignal (radar.impresjapr.pl — LIVE)
    - GoogleTrendsSignal (fallback placeholder)
    - SocialTrendsSignal (fallback placeholder)

CLI:
  python worker.py --health               # status wszystkich komponentów
  python worker.py --run                  # zbierz kandydatów
  python worker.py --run --top 10         # pokaż top-N kandydatów
  python worker.py --run --sheets         # zapisz do Google Sheets
  python worker.py --run --json           # output jako JSON
  python worker.py --process CANDIDATE_ID # przetwórz kandydata przez PressAI

Status wdrożenia:
  GmailSource v1.0 — LIVE (PressAI Gmail API, tobroz@gmail.com).
  FeedCrawlerSource v1.2 — LIVE (13k+ feedów, crawler.impresjapr.pl, działy tematyczne).
  GeoRelevanceSignal v1.0 — LIVE (priorytetyzacja PL/EU/US-biznes).
  RadarEnricher v1.0 — LIVE (Content Radar per-portal viral_score boost).
  Content Radar LIVE — aktywny gdy CONTENT_RADAR_JWT ustawiony.
  Discord notifications — aktywne gdy DISCORD_WEBHOOK_KURIER365 ustawiony.
  Google Sheets — aktywny gdy GOOGLE_SA_FILE ustawiony.
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests

# Dodaj root projektu do Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.base.worker_base import WorkerBase, ContentCandidate
from agents.base.sources.gmail_source import GmailSource
from agents.base.sources.feed_crawler_source import FeedCrawlerSource
from agents.base.sources.newseria_source import NewseriaSource
from agents.base.trend_signals.geo_relevance_signal import GeoRelevanceSignal
from agents.base.trend_signals.radar_enricher import RadarEnricher
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
    'pressai_url': os.environ.get('PRESSAI_URL', 'https://press.impresjapr.pl'),
    'feed_crawler_url': os.environ.get('FEED_CRAWLER_URL', 'https://crawler.impresjapr.pl'),
    'spreadsheet_id': os.environ.get('SPREADSHEET_ID', '1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig'),
    'state_file': str(Path(__file__).parent / 'kurier365_state.json'),

    # Token PressAI — uzupełnij przez docker exec lub secrets manager
    'pressai_token': os.environ.get('PRESSAI_JWT_USER') or os.environ.get('PRESSAI_JWT') or os.environ.get('PRESSAI_TOKEN'),

    # Dane logowania Newseria — uzupełnij gdy konto gotowe
    'newseria_username': os.environ.get('NEWSERIA_USER'),
    'newseria_password': os.environ.get('NEWSERIA_PASS'),

    # Content Radar JWT — LIVE na radar.impresjapr.pl
    'content_radar_jwt': os.environ.get('CONTENT_RADAR_JWT'),
    'content_radar_url': 'https://radar.impresjapr.pl',
}

# ---------------------------------------------------------------------------
# ROUTING & PROMPTY
# ---------------------------------------------------------------------------

def _get_target_portal(candidate: ContentCandidate) -> str:
    """Wybierz portal docelowy na podstawie sekcji/kategorii kandydata."""
    section = candidate.metadata.get('section', '')
    category = candidate.metadata.get('category', '')
    source = candidate.source.lower()

    # Gmail od współpracowników -> kurier365 (polityka, nauka, reportaż)
    if source.startswith('gmail:'):
        return 'Kurier365'
    # Geostrategia/Obroność -> Kurier365
    if 'geostrat' in section.lower() or 'defence' in section.lower():
        return 'Kurier365'
    # Nauka -> Kurier365
    if 'nauka' in section.lower() or 'science' in category.lower():
        return 'Kurier365'
    # Biznes/gospodarka -> BiznesCiti
    if any(kw in category.lower() for kw in ['biznes', 'gospodarka', 'finanse', 'ekonomia']):
        return 'BiznesCiti'
    return 'Kurier365'


def _should_auto_publish(candidate: ContentCandidate) -> bool:
    """Sprawdź czy kandydat ma własne zdjęcia i powinien od razu trafić do WP draft."""
    source_lower = candidate.source.lower()
    return any(kw in source_lower for kw in ['zabka', 'żabka', 'juchniewicz', 'rudzinski', 'rudinski'])


def build_generate_payload(
    candidate: ContentCandidate,
    target_portal: str,
    selected_phrase: str = '',
    secondary_phrases: list = None
) -> dict:
    """Buduje payload do POST /api/editor/generate w PressAI."""
    payload = {
        'title': candidate.title,
        'source_text': candidate.raw_content or candidate.summary or candidate.title,
        'source_url': candidate.content_url,
        'portal': target_portal,
        'custom_instructions': (
            'WYMAGANIA OBOWIĄZKOWE:\n'
            '1. Artykuł MINIMUM 600 słów (lepiej 800-1000) — absolutnie nie może być krótszy.\n'
            '2. Tytuł SEO (H1) MUSI zawierać główną frazę kluczową — nie omin tego wymogu.\n'
            '3. Język polski, przystępny dla szerokiego czytelnika.\n'
            '4. Optymalizacja pod Google Discover: angażujący wstęp, nagłówki H2/H3, wypunktowania.\n'
            '5. FAQ na końcu artykułu (min 3 pytania i odpowiedzi).\n'
            '6. Cross-link z BiznesCiti gdy temat biznesowy.'
        ),
        'generate_faq': True,
        'min_words': 600,  # parametr minimalnej liczby słów PressAI
    }
    if selected_phrase:
        payload['selected_phrase'] = selected_phrase
    if secondary_phrases:
        payload['secondary_phrases'] = secondary_phrases
    return payload


# ---------------------------------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------------------------------

def write_candidates_to_sheets(candidates: list, spreadsheet_id: str = '1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig') -> bool:
    """Zapisuje kandydatów do zakładki Kandydaci w Google Sheets."""
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
            target_portal = _get_target_portal(c)
            rows.append([
                c.id,
                now,
                c.source,
                target_portal,
                c.metadata.get('category', ''),
                f'P{max(0, 10-c.priority)}',
                c.title,
                (c.summary or '')[:200],
                c.content_url,
                c.metadata.get('author', ''),
                str(c.metadata.get('geo_relevance_score', '')),
                'nowy',  # Status
                '', '', '', '', '',  # puste pola M, N, O, P (WP URL), Q
                c.metadata.get('geo_relevance', ''),  # R: Notatki
                c.metadata.get('prompt_image_1', ''), # S: Prompt obraz 1
                c.metadata.get('prompt_image_2', ''), # T: Prompt obraz 2
            ])
        if rows:
            ws.append_rows(rows, value_input_option='USER_ENTERED')
            log.info(f'Zapisano {len(rows)} kandydatów do Sheets')
        return True
    except Exception as e:
        log.error(f'Błąd zapisu do Sheets: {e}')
        return False


def update_candidate_in_sheets(
    candidate_id: str,
    status: str = 'w produkcji',
    wp_url: str = '',
    collab_link: str = '',
    spreadsheet_id: str = '1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig'
) -> bool:
    """Aktualizuje Status (kolumna L) i URL draftu WP (kolumna P) w Google Sheets."""
    try:
        from google.oauth2.service_account import Credentials
        import gspread
    except ImportError:
        log.warning("Brak bibliotek google-auth / gspread — pomijam aktualizację Sheets")
        return False

    sa_file = os.getenv('GOOGLE_SA_FILE', '/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json')
    if not os.path.exists(sa_file):
        log.warning(f"Brak pliku service account ({sa_file}) — pomijam aktualizację Sheets")
        return False

    try:
        creds = Credentials.from_service_account_file(
            sa_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(spreadsheet_id)
        ws = sh.worksheet('Kandydaci')

        cell = ws.find(candidate_id, in_column=1)
        if not cell:
            log.warning(f"Kandydat {candidate_id} nie znaleziony w kolumnie A arkusza Kandydaci")
            return False

        row_idx = cell.row
        # Kolumna L = 12 (Status), Kolumna P = 16 (URL draftu WP), Kolumna Q = 17 (Collab link)
        updates = [
            {'range': f'L{row_idx}', 'values': [[status]]},
            {'range': f'P{row_idx}', 'values': [[wp_url or '']]},
            {'range': f'Q{row_idx}', 'values': [[collab_link or '']]},
        ]
        ws.batch_update(updates, value_input_option='USER_ENTERED')
        log.info(f"Zaktualizowano wiersz {row_idx} w Sheets: Status='{status}', WP_URL='{wp_url}'")
        return True
    except Exception as e:
        log.error(f"Błąd aktualizacji statusu w Sheets dla {candidate_id}: {e}")
        return False


# ---------------------------------------------------------------------------
# WORKER
# ---------------------------------------------------------------------------

class Kurier365Worker(WorkerBase):
    """Orkiestrator contentu dla kurier365.pl i biznesciti.com.

    Pipeline:
        1. collect_candidates() — zbiera z Gmail + FeedCrawler + Newseria
        2. enrich_with_trends() — ocenia trend_score i geo_relevance
        3. radar.enrich() — wzbogaca o viral_score z Content Radar
        4. Kandydaci sortowani (priority DESC, trend_score DESC)
        5. process(candidate) — generuje artykuł w PressAI, zapisuje do historii,
           aktualizuje Sheets ('w produkcji') i publikuje WP draft dla wyjątków.
    """

    def __init__(self, config: dict = None):
        """Args:
            config: nadpisz domyślną konfigurację CONFIG (opcjonalne).
        """
        effective_config = {**CONFIG, **(config or {})}
        super().__init__(effective_config)

        self.pressai_url = effective_config['pressai_url'].rstrip('/')
        self.pressai_token = effective_config.get('pressai_token')
        self.spreadsheet_id = effective_config.get('spreadsheet_id', '1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig')
        feed_crawler_url = effective_config.get('feed_crawler_url', 'https://crawler.impresjapr.pl')
        content_radar_jwt = effective_config.get('content_radar_jwt')
        content_radar_url = effective_config.get('content_radar_url', 'https://radar.impresjapr.pl')

        # ------------------------------------------------------------------
        # Źródła (Sources)
        # ------------------------------------------------------------------

        # Gmail — monitorowanie skrzynki przez PressAI API (tobroz@gmail.com)
        self.add_source(GmailSource(
            pressai_url=self.pressai_url,
            portal='kurier365',
            token=self.pressai_token,
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
        self.radar = RadarEnricher(portal='kurier365')

        # Content Radar — LIVE integracja z radar.impresjapr.pl
        self.add_trend_signal(ContentRadarSignal(
            api_url=content_radar_url,
            jwt_token=content_radar_jwt,  # None = tryb placeholder
        ))

        # GoogleTrends + Social — fallback placeholder
        self.add_trend_signal(GoogleTrendsSignal())
        self.add_trend_signal(SocialTrendsSignal())

    def run(self) -> List[ContentCandidate]:
        candidates = super().run()
        candidates = self.radar.enrich(candidates)
        return candidates

    def _get_auth_headers(self) -> dict:
        token = self.pressai_token or os.environ.get('PRESSAI_JWT_USER') or os.environ.get('PRESSAI_JWT') or os.environ.get('PRESSAI_TOKEN')
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers

    def _get_seo_phrases(self, source_text: str, source_url: str, portal_name: str, portal_url: str) -> tuple:
        """Pobiera frazy SEO z PressAI phrase-candidates.
        Zwraca: (selected_phrase: str, secondary_phrases: list[str])
        """
        token = self.pressai_token or os.environ.get('PRESSAI_JWT_USER') or os.environ.get('PRESSAI_JWT') or os.environ.get('PRESSAI_TOKEN', '')
        if not token:
            return '', []

        try:
            payload = {
                'source_text': source_text[:2000],
                'target_portal': portal_name,
                'site_url': portal_url
            }
            r = requests.post(
                f"{self.pressai_url}/api/editor/phrase-candidates",
                json=payload,
                headers={'Authorization': f'Bearer {token}'},
                timeout=30
            )
            if r.status_code == 200:
                candidates = r.json().get('candidates', [])
                # Posortuj po score
                candidates.sort(key=lambda x: -x.get('score', 0))
                selected = candidates[0]['phrase'] if candidates else ''
                secondary = [c['phrase'] for c in candidates[1:4]]  # top 3 poboczne
                log.info(f'Frazy SEO: {selected} + {secondary}')
                return selected, secondary
        except Exception as e:
            log.warning(f'phrase-candidates error: {e}')
        return '', []

    def write_to_sheets(self, candidates: list, spreadsheet_id: str = None) -> bool:
        """Zapisuje kandydatów do Google Sheets."""
        target_sid = spreadsheet_id or self.spreadsheet_id
        return write_candidates_to_sheets(candidates, spreadsheet_id=target_sid)

    def generate_article(self, candidate: ContentCandidate, target_portal: str) -> Optional[dict]:
        """Wywołaj POST /api/editor/generate w PressAI."""
        portal_urls = {
            'Kurier365': 'https://kurier365.pl',
            'BiznesCiti': 'https://biznesciti.com',
            'Prawy.pl': 'https://prawy.pl'
        }
        portal_name = _get_target_portal(candidate)
        site_url = portal_urls.get(portal_name, 'https://kurier365.pl')

        selected_phrase, secondary_phrases = self._get_seo_phrases(
            source_text=candidate.title + ' ' + (candidate.summary or ''),
            source_url=candidate.content_url or '',
            portal_name=portal_name,
            portal_url=site_url
        )

        url = f"{self.pressai_url}/api/editor/generate"
        payload = build_generate_payload(
            candidate,
            target_portal,
            selected_phrase=selected_phrase,
            secondary_phrases=secondary_phrases
        )
        headers = self._get_auth_headers()

        log.info(f"Wysyłam zapytanie o generowanie artykułu do {url} dla portalu {target_portal} (fraza: '{selected_phrase}')")
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=180)
            if resp.status_code in (200, 201):
                data = resp.json()
                log.info(f"Pomyślnie wygenerowano artykuł w PressAI dla {candidate.id}")
                return data
            log.error(f"Błąd generowania w PressAI HTTP {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            log.error(f"Wyjątek podczas generowania artykułu: {e}")
        return None

    def save_article_history(self, candidate: ContentCandidate, generated: dict, target_portal: str) -> Optional[dict]:
        """Zapisz wygenerowany artykuł do historii PressAI (POST /api/articles/)."""
        url = f"{self.pressai_url}/api/articles/"
        headers = self._get_auth_headers()

        article_payload = {
            'title': generated.get('title') or candidate.title,
            'content': generated.get('content') or generated.get('body') or generated.get('html') or '',
            'portal': target_portal,
            'source_url': candidate.content_url or '',
            'candidate_id': candidate.id,
            'meta': {
                'faq': generated.get('faq'),
                'seo_title': generated.get('seo_title'),
                'category': candidate.metadata.get('category', ''),
                'section': candidate.metadata.get('section', ''),
                'generated_at': datetime.now().isoformat(),
            }
        }

        try:
            resp = requests.post(url, json=article_payload, headers=headers, timeout=30)
            if resp.status_code in (200, 201):
                saved = resp.json()
                log.info(f"Zapisano artykuł do historii PressAI (ID: {saved.get('id', 'brak')})")
                return saved
            log.warning(f"Zapis do historii PressAI HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log.error(f"Błąd podczas zapisu do historii PressAI: {e}")
        return None

    def publish_to_wp(self, candidate: ContentCandidate, generated: dict, target_portal: str) -> Optional[dict]:
        """Wywołaj POST /api/publisher/publish w PressAI (dla wyjątków z własnymi zdjęciami)."""
        url = f"{self.pressai_url}/api/publisher/publish"
        headers = self._get_auth_headers()

        publish_payload = {
            'portal': target_portal,
            'title': generated.get('title') or candidate.title,
            'content': generated.get('content') or generated.get('body') or generated.get('html') or '',
            'status': 'draft',  # Zawsze draft w WP
            'source_url': candidate.content_url or '',
            'candidate_id': candidate.id,
            'tags': generated.get('tags', []),
            'category': candidate.metadata.get('category', ''),
        }

        try:
            resp = requests.post(url, json=publish_payload, headers=headers, timeout=60)
            if resp.status_code in (200, 201):
                pub_data = resp.json()
                log.info(f"Opublikowano draft w WordPress dla {candidate.id}: {pub_data}")
                return pub_data
            log.error(f"Błąd publikacji WP draft HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log.error(f"Błąd podczas publikacji WP draft: {e}")
        return None

    def _generate_collab_link(self, post_id: int, email: str = "tobroz@gmail.com") -> str | None:
        """Generate draft collab link via WP REST API."""
        wp_user = os.environ.get("PRAWY_WP_USER", "")
        wp_app_pass = os.environ.get("PRAWY_WP_APP_PASS", "")
        if not wp_user or not wp_app_pass:
            log.warning("PRAWY_WP_USER / PRAWY_WP_APP_PASS not set — skipping collab link")
            return None
        try:
            import requests as req
            r = req.post(
                "https://prawy.pl/wp-json/draft-collab/v1/generate",
                json={"post_id": post_id, "email": email, "expire_on_publish": True},
                auth=(wp_user, wp_app_pass),
                timeout=10,
            )
            r.raise_for_status()
            return r.json().get("link")
        except Exception as e:
            log.warning(f"collab link generation failed: {e}")
            return None

    def process(self, candidate: ContentCandidate) -> dict:
        """Przetwarzanie zatwierdzonego kandydata:
        1. Określ portal docelowy (_get_target_portal)
        2. Wywołaj generowanie artykułu w PressAI (POST /api/editor/generate)
        3. Zapisz do historii PressAI (POST /api/articles/) BEZ publikacji
        4. WYJĄTEK: jeśli nadawca z własnymi zdjęciami (zabka, juchniewicz, rudzinski) -> publikuj draft WP
        5. Zaktualizuj Google Sheets: Status -> 'w produkcji', URL draftu WP pusty (lub URL jeśli wyjątek)
        """
        target_portal = _get_target_portal(candidate)
        auto_publish = _should_auto_publish(candidate)
        log.info(f"Przetwarzanie kandydata {candidate.id} '{candidate.title[:50]}' -> Portal: {target_portal}, Auto-publish: {auto_publish}")

        # 1. Generowanie artykułu
        generated = self.generate_article(candidate, target_portal)
        if not generated:
            log.error(f"Generowanie nie powiodło się dla kandydata {candidate.id}")
            return {'status': 'error', 'candidate_id': candidate.id, 'error': 'Generation failed'}

        # 2. Zapis do historii PressAI
        saved_article = self.save_article_history(candidate, generated, target_portal)

        # 3. Publikacja WP (tylko wyjątki)
        wp_url = ''
        wp_post_id = None
        collab_link = ''
        if auto_publish:
            pub_res = self.publish_to_wp(candidate, generated, target_portal)
            if pub_res:
                wp_url = pub_res.get('wp_url') or pub_res.get('post_url') or pub_res.get('url') or ''
                wp_post_id = pub_res.get('wp_post_id') or pub_res.get('post_id')
                if wp_post_id and target_portal == 'Prawy.pl':
                    collab_link = self._generate_collab_link(wp_post_id)
        else:
            log.info(f"Artykuł {candidate.id} zapisany w historii PressAI — oczekuje na ręczne dodanie zdjęć i publikację.")

        # 4. Aktualizacja Sheets
        update_candidate_in_sheets(
            candidate_id=candidate.id,
            status='w produkcji',
            wp_url=wp_url,
            collab_link=collab_link,
            spreadsheet_id=self.spreadsheet_id
        )

        return {
            'status': 'w produkcji',
            'candidate_id': candidate.id,
            'target_portal': target_portal,
            'auto_published': auto_publish,
            'wp_url': wp_url,
            'wp_post_id': wp_post_id,
            'pressai_article_id': saved_article.get('id') if saved_article else None
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='kurier365-worker — Content pipeline dla kurier365.pl i biznesciti.com',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  python worker.py --health
  python worker.py --run
  python worker.py --run --top 5
  python worker.py --run --sheets
  python worker.py --run --json
  python worker.py --process CANDIDATE_ID

Zmienne środowiskowe:
  FEED_CRAWLER_URL            — URL API Feed Crawler (domyślnie: https://crawler.impresjapr.pl)
  PRESSAI_URL                 — URL API PressAI (domyślnie: https://press.impresjapr.pl)
  PRESSAI_JWT                 — JWT token PressAI
  PRESSAI_JWT_USER            — JWT token użytkownika PressAI (tobroz@gmail.com)
  NEWSERIA_USER               — login Newseria
  NEWSERIA_PASS               — hasło Newseria
  CONTENT_RADAR_JWT           — JWT token Content Radar (radar.impresjapr.pl)
  DISCORD_WEBHOOK_KURIER365   — Webhook URL Discord dla powiadomień
  DISCORD_WEBHOOK_PRIORITY    — Webhook URL Discord dla powiadomień priorytetowych (P0/Gmail)
  GOOGLE_SA_FILE              — Ścieżka do klucza Service Account Google
  SPREADSHEET_ID              — ID arkusza Google Sheets
"""
    )
    parser.add_argument('--health', action='store_true', help='Status komponentów workera')
    parser.add_argument('--run', action='store_true', help='Zbierz kandydatów ze źródeł')
    parser.add_argument('--top', type=int, default=10, metavar='N', help='Pokaż top-N kandydatów (domyślnie 10)')
    parser.add_argument('--sheets', action='store_true', help='Zapisz zebranych kandydatów do Google Sheets')
    parser.add_argument('--json', action='store_true', help='Output jako JSON')
    parser.add_argument('--process', metavar='CANDIDATE_ID', help='Przetwórz pojedynczego kandydata przez PressAI')
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

    if args.process:
        cid = args.process
        # Stwórz tymczasowego kandydata lub pobierz z pliku stanu
        state = worker.load_state()
        cand_dict = state.get('candidates', {}).get(cid)
        if cand_dict:
            candidate = ContentCandidate.from_dict(cand_dict)
        else:
            candidate = ContentCandidate(
                id=cid,
                source='manual',
                portal='Kurier365',
                title=f'Kandydat {cid}',
                summary=''
            )
        result = worker.process(candidate)
        print(json.dumps(result, indent=2, ensure_ascii=False))
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
            worker.write_to_sheets(candidates)

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
