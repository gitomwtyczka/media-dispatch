#!/usr/bin/env python3
"""agents/pressai-worker/auto_publisher.py

AutoPublisher — silnik generowania i publikacji artykułów w PressAI.
media-dispatch | media-dev-B | 12.09.2026

Architektura:
  1. Źródło (Source):
     - Bezpośredni URL / tekst
     - Auto-pick z Feed Crawlera (selekcja PL/EU kandydatów)
  2. Generowanie artykułu:
     - POST /api/editor/generate (PressAI SSE stream)
     - Obsługa eventów SSE i parsowanie article_id
     - Fallback: POST /api/articles/ jeśli SSE zwróci treść bez article_id
  3. Publikacja WordPress:
     - POST /api/publisher/publish/{article_id}
     - BEZWZGLĘDNA ZASADA: ZAWSZE status='draft' (NIGDY 'publish'!)
     - Ekstrakcja wp_post_id i wp_edit_url (z fallbackiem per portal)

Env vars:
  PRESSAI_URL         — URL instancji PressAI (domyślnie: https://press.impresjapr.pl)
  PRESSAI_JWT_TOKEN   — Bearer JWT token autoryzacyjny (wymagany)
  PRESSAI_PORTAL_ID   — Domyślny ID portalu WordPress w PressAI (domyślnie: 1 dla Kurier365)
  FEED_CRAWLER_URL    — URL API Feed Crawlera (domyślnie: https://crawler.impresjapr.pl)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pressai-worker.auto_publisher")


class AutoPublisher:
    """Klasa obsługująca zautomatyzowany cykl generowania i publikacji artykułów w PressAI."""

    PL_KEYWORDS = [
        "polska", "polski", "polsk", "uokik", "rpp", "pln", "zus", "nfz",
        "pap", "warszawa", "inflacja", "podatek", "rząd", "sejm",
        "konsument", "biznes", "gospodark", "przedsiębiorc", "gield", "giełd",
        "nbp", "złoty", "zloty"
    ]

    PORTAL_DOMAINS = {
        "kurier365": "https://kurier365.pl",
        "kurier365.pl": "https://kurier365.pl",
        "prawy": "https://prawy.pl",
        "prawy.pl": "https://prawy.pl",
        "biznesciti": "https://biznesciti.com",
        "biznesciti.com": "https://biznesciti.com",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.pressai_url = (
            cfg.get("pressai_url")
            or os.environ.get("PRESSAI_URL")
            or "https://press.impresjapr.pl"
        ).rstrip("/")

        # PRESSAI_JWT_TOKEN jako główna zmienna, z fallbackami kompatybilnościowymi
        self.token = (
            cfg.get("token")
            or os.environ.get("PRESSAI_JWT_TOKEN")
            or os.environ.get("PRESSAI_JWT_USER")
            or os.environ.get("PRESSAI_JWT")
            or os.environ.get("PRESSAI_TOKEN")
            or ""
        )

        self.default_portal_id = int(
            cfg.get("portal_id")
            or os.environ.get("PRESSAI_PORTAL_ID")
            or 1
        )

        self.feed_crawler_url = (
            cfg.get("feed_crawler_url")
            or os.environ.get("FEED_CRAWLER_URL")
            or "https://crawler.impresjapr.pl"
        ).rstrip("/")

        self._last_status: str = "initialized"
        self._last_run: Optional[str] = None
        self._last_result: Optional[Dict[str, Any]] = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def health_check(self) -> Dict[str, Any]:
        """Sprawdza połączenie z PressAI oraz Feed Crawler."""
        pressai_ok = False
        feed_crawler_ok = False
        pressai_code = None
        feed_crawler_code = None
        details: Dict[str, Any] = {}

        # 1. Sprawdź PressAI
        try:
            r_press = requests.get(
                f"{self.pressai_url}/api/publisher/portals",
                headers=self._get_headers(),
                timeout=10,
            )
            pressai_code = r_press.status_code
            pressai_ok = r_press.status_code in (200, 201)
            details["pressai_response"] = r_press.text[:200]
        except Exception as e:
            details["pressai_error"] = str(e)

        # 2. Sprawdź Feed Crawler (przez proxy PressAI lub direct)
        try:
            r_fc = requests.get(
                f"{self.pressai_url}/api/feed-crawler/articles?status=new&portal=Kurier365&limit=1",
                headers=self._get_headers(),
                timeout=10,
            )
            feed_crawler_code = r_fc.status_code
            if r_fc.status_code in (200, 201):
                feed_crawler_ok = True
                details["feed_crawler_source"] = "pressai_proxy"
            else:
                r_fc_direct = requests.get(
                    f"{self.feed_crawler_url}/api/stats",
                    timeout=10,
                )
                feed_crawler_code = r_fc_direct.status_code
                feed_crawler_ok = r_fc_direct.status_code in (200, 201)
                details["feed_crawler_source"] = "direct_crawler"
        except Exception as e:
            details["feed_crawler_error"] = str(e)

        overall_status = (
            "ok"
            if (pressai_ok and feed_crawler_ok)
            else ("degraded" if (pressai_ok or feed_crawler_ok) else "error")
        )

        return {
            "status": overall_status,
            "pressai_connected": pressai_ok,
            "feed_crawler_connected": feed_crawler_ok,
            "token_configured": bool(self.token),
            "pressai_url": self.pressai_url,
            "feed_crawler_url": self.feed_crawler_url,
            "pressai_code": pressai_code,
            "feed_crawler_code": feed_crawler_code,
            "details": details,
        }

    def _fetch_best_candidate(self, portal: str = "Kurier365") -> Dict[str, Any]:
        """Pobiera i wybiera najbardziej adekwatnego kandydata z feed-crawlera."""
        articles: List[Dict[str, Any]] = []

        # Próba 1: PressAI proxy feed-crawler
        try:
            url = f"{self.pressai_url}/api/feed-crawler/articles?status=new&portal={portal}&limit=15"
            r = requests.get(url, headers=self._get_headers(), timeout=15)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    articles = data
                elif isinstance(data, dict):
                    articles = data.get("articles") or data.get("items") or []
        except Exception as e:
            logger.warning(f"Błąd pobierania przez PressAI proxy feed-crawler: {e}")

        # Próba 2: Bezpośrednie API feed-crawlera
        if not articles:
            try:
                url = f"{self.feed_crawler_url}/api/articles?limit=20"
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        articles = data
                    elif isinstance(data, dict):
                        articles = data.get("articles") or data.get("items") or []
            except Exception as e:
                logger.warning(f"Błąd bezpośredniego pobierania z feed-crawlera: {e}")

        if not articles:
            raise RuntimeError("Brak artykułów w feed-crawlerze lub brak połączenia z API")

        # Filtrowanie i scoring kandydatów
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for a in articles:
            score = 0
            title = (a.get("title") or "").lower()
            summary = (a.get("summary") or a.get("content") or "").lower()
            text = f"{title} {summary}"

            lang = (a.get("language") or "").lower()
            country = (a.get("country") or "").upper()

            if lang == "pl" or country == "PL":
                score += 10

            for kw in self.PL_KEYWORDS:
                if kw in text:
                    score += 1

            scored.append((score, a))

        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]
        logger.info(f"Wybrany kandydat (score={scored[0][0]}): {best.get('title')}")
        return best

    def _generate(
        self,
        source_url: str,
        source_text: str,
        target_portal: str,
        model_provider: str,
        model_name: str,
        custom_instructions: str,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Wywołuje POST /api/editor/generate i parsuje strumień SSE."""
        if not self.token:
            raise ValueError("Brak PRESSAI_JWT_TOKEN — wymagany do autoryzacji w PressAI")

        payload = {
            "source_url": source_url,
            "source_text": source_text or "",
            "target_portal": target_portal,
            "model_provider": model_provider,
            "model_name": model_name,
            "is_in_extenso": False,
            "generate_faq": True,
            "discover_overlay": False,
            "formats": [],
            "custom_instructions": custom_instructions,
        }

        url = f"{self.pressai_url}/api/editor/generate"
        logger.info(f"POST {url} [target_portal={target_portal}, model={model_name}]")

        article_id: Optional[str] = None
        generated_article: Optional[str] = None
        extracted_title: Optional[str] = None

        with requests.post(
            url, json=payload, headers=self._get_headers(), stream=True, timeout=180
        ) as resp:
            if resp.status_code not in (200, 201):
                err_text = resp.text[:400]
                raise RuntimeError(f"PressAI generate błąd HTTP {resp.status_code}: {err_text}")

            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if line_str.startswith("data:"):
                    data_str = line_str[5:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        obj = json.loads(data_str)
                        if "article_id" in obj and obj["article_id"]:
                            article_id = str(obj["article_id"])

                        if "result" in obj and isinstance(obj["result"], dict):
                            res = obj["result"]
                            if "article_id" in res and res["article_id"]:
                                article_id = str(res["article_id"])
                            if "generated_article" in res and res["generated_article"]:
                                generated_article = res["generated_article"]
                            if "title" in res and res["title"]:
                                extracted_title = res["title"]

                        if "generated_article" in obj and obj["generated_article"]:
                            generated_article = obj["generated_article"]

                        if "title" in obj and obj["title"]:
                            extracted_title = obj["title"]

                        if "error" in obj and obj["error"]:
                            raise RuntimeError(f"Błąd zgłoszony przez PressAI SSE: {obj['error']}")
                    except json.JSONDecodeError:
                        continue

        # Fallback jeśli SSE nie zwróciło article_id bezpośrednio, ale mamy treść artykułu
        if not article_id and generated_article:
            logger.info("Brak article_id w strumieniu SSE — zapisuję wygenerowany artykuł do POST /api/articles/")
            title = extracted_title
            if not title:
                lines = [l.strip() for l in generated_article.split("\n") if l.strip()]
                for l in lines:
                    if not l.startswith("Glowna") and not l.startswith("Frazy") and len(l) > 10:
                        title = l.lstrip("#").strip()
                        break
            if not title:
                title = "Nowy artykuł"

            save_payload = {
                "title": title[:200],
                "content": generated_article,
                "portal": target_portal,
                "source_url": source_url,
                "source_text": source_text,
                "status": "draft",
            }
            r_save = requests.post(
                f"{self.pressai_url}/api/articles/",
                json=save_payload,
                headers=self._get_headers(),
                timeout=30,
            )
            if r_save.status_code in (200, 201):
                try:
                    sdata = r_save.json()
                    article_id = str(sdata.get("id") or sdata.get("article_id") or "")
                except Exception:
                    pass

        if not article_id:
            raise RuntimeError("Nie udało się uzyskać article_id z PressAI (ani z SSE, ani z /api/articles/)")

        return article_id, generated_article, extracted_title

    def _publish_draft(self, article_id: str, portal_id: int, target_portal: str) -> Tuple[Optional[int], Optional[str]]:
        """Publikuje artykuł w WordPress jako draft.

        BEZWZGLĘDNA ZASADA: status='draft', NIGDY 'publish'!
        """
        url = f"{self.pressai_url}/api/publisher/publish/{article_id}"
        # ZAWSZE status='draft'
        pub_payload = {
            "portal_id": int(portal_id),
            "status": "draft",
            "publish_as_new": True,
        }
        logger.info(f"POST {url} [portal_id={portal_id}, status=draft]")

        r = requests.post(url, json=pub_payload, headers=self._get_headers(), timeout=60)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Błąd publikacji draftu HTTP {r.status_code}: {r.text[:300]}")

        res_data = r.json()
        wp_edit_url = res_data.get("wp_edit_url") or res_data.get("edit_url") or res_data.get("url")
        wp_post_id = res_data.get("post_id") or res_data.get("wp_post_id")

        if not wp_edit_url and wp_post_id:
            portal_clean = target_portal.lower().replace(".pl", "").replace(".com", "")
            base_url = self.PORTAL_DOMAINS.get(portal_clean, "https://kurier365.pl")
            wp_edit_url = f"{base_url}/wp-admin/post.php?post={wp_post_id}&action=edit"

        return wp_post_id, wp_edit_url

    def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Główna metoda przetwarzania zadania publikacji."""
        self._last_run = datetime.now().isoformat()
        target_portal = task.get("target_portal") or task.get("portal") or "Kurier365"
        portal_id = task.get("portal_id") or self.default_portal_id
        model_provider = task.get("model_provider") or "anthropic"
        model_name = task.get("model_name") or "claude-sonnet-4-5"
        custom_instructions = (
            task.get("custom_instructions")
            or "Napisz artykuł przystępnym, popularnym językiem dla polskiego czytelnika. Zoptymalizuj pod Google Discover. Język polski."
        )

        source_url = task.get("source_url") or ""
        source_text = task.get("source_text") or ""

        try:
            # Opcja B: Auto-pick z feed-crawlera
            if task.get("auto_pick"):
                logger.info(f"Auto-pick aktywne dla portalu {target_portal}")
                candidate = self._fetch_best_candidate(portal=target_portal)
                source_url = candidate.get("url") or candidate.get("content_url") or ""
                candidate_summary = candidate.get("summary") or candidate.get("content") or ""
                candidate_title = candidate.get("title") or ""
                source_text = f"{candidate_title}\n\n{candidate_summary}".strip()

            if not source_url and not source_text:
                raise ValueError("Wymagany jest source_url, source_text lub flaga auto_pick=True")

            # Krok 1: Generowanie w PressAI
            article_id, _, _ = self._generate(
                source_url=source_url,
                source_text=source_text,
                target_portal=target_portal,
                model_provider=model_provider,
                model_name=model_name,
                custom_instructions=custom_instructions,
            )

            # Krok 2: Publikacja jako draft w WP
            wp_post_id, wp_edit_url = self._publish_draft(
                article_id=article_id,
                portal_id=portal_id,
                target_portal=target_portal,
            )

            result = {
                "status": "ok",
                "article_id": article_id,
                "wp_post_id": wp_post_id,
                "wp_edit_url": wp_edit_url,
                "source_url": source_url,
            }
            self._last_status = "ok"
            self._last_result = result
            logger.info(f"Publikacja zakończona sukcesem: post_id={wp_post_id}, url={wp_edit_url}")
            return result

        except Exception as e:
            logger.error(f"Błąd procesu AutoPublisher: {e}", exc_info=True)
            result = {
                "status": "error",
                "error": str(e),
                "article_id": None,
                "wp_post_id": None,
                "wp_edit_url": None,
                "source_url": source_url,
            }
            self._last_status = "error"
            self._last_result = result
            return result

    def get_status(self) -> Dict[str, Any]:
        """Zwraca ostatni stan workera."""
        return {
            "status": self._last_status,
            "last_run": self._last_run,
            "last_result": self._last_result,
            "pressai_url": self.pressai_url,
            "feed_crawler_url": self.feed_crawler_url,
            "default_portal_id": self.default_portal_id,
            "token_configured": bool(self.token),
        }


def main():
    parser = argparse.ArgumentParser(description="AutoPublisher — silnik generowania i publikacji w PressAI")
    parser.add_argument("--health", action="store_true", help="Sprawdź stan połączeń (PressAI, Feed Crawler)")
    parser.add_argument("--status", action="store_true", help="Pokaż ostatni stan workera")
    parser.add_argument("--auto-pick", action="store_true", help="Pobierz i opublikuj najlepszego kandydata z feed-crawlera")
    parser.add_argument("--url", type=str, help="URL artykułu źródłowego do przetworzenia")
    parser.add_argument("--text", type=str, help="Opcjonalny tekst źródłowy")
    parser.add_argument("--portal", type=str, default="Kurier365", help="Docelowy portal (domyślnie: Kurier365)")
    parser.add_argument("--portal-id", type=int, help="ID portalu WordPress (domyślnie z PRESSAI_PORTAL_ID lub 1)")
    parser.add_argument("--process-json", type=str, help="Pełne zadanie w formacie JSON do przetworzenia")
    parser.add_argument("--json", action="store_true", help="Zwróć wynik jako JSON")
    args = parser.parse_args()

    publisher = AutoPublisher()

    if args.health:
        res = publisher.health_check()
        print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else f"Health check: {res['status']} (PressAI: {res['pressai_connected']}, FeedCrawler: {res['feed_crawler_connected']})")
        sys.exit(0 if res["status"] in ("ok", "degraded") else 1)

    if args.status:
        res = publisher.get_status()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(0)

    task: Dict[str, Any] = {}
    if args.process_json:
        try:
            task = json.loads(args.process_json)
        except json.JSONDecodeError as e:
            print(f"Błąd parsowania JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if args.auto_pick:
            task["auto_pick"] = True
        if args.url:
            task["source_url"] = args.url
        if args.text:
            task["source_text"] = args.text
        if args.portal:
            task["target_portal"] = args.portal
        if args.portal_id:
            task["portal_id"] = args.portal_id

    if not task:
        parser.print_help()
        sys.exit(0)

    result = publisher.process(task)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Status: {result.get('status')}")
        if result.get("status") == "ok":
            print(f"Article ID: {result.get('article_id')}")
            print(f"WP Post ID: {result.get('wp_post_id')}")
            print(f"WP Edit URL: {result.get('wp_edit_url')}")
        else:
            print(f"Error: {result.get('error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
