#!/usr/bin/env python3
"""
agents/vse-worker/pipeline.py — Autonomiczny 4-krokowy pipeline Video SEO Engine

Obsługiwane kroki:
1. POST /v1/generate — generowanie metadanych SEO, tytułów, rozdziałów i artykułu (Claude)
2. POST /v1/inject — wstrzyknięcie artykułu do WordPress (ZAWSZE post_status='draft')
3. Update YouTube metadata — aktualizacja tytułu, opisu z linkiem do WP, rozdziałów (ZAWSZE privacyStatus='unlisted')
4. POST /v1/shorts/candidates & POST /v1/shorts/render — wyłonienie kandydatów i submit render jobs dla Shortów

Zasady nadrzędne:
- WP post_status: ZAWSZE 'draft'
- YT privacyStatus: ZAWSZE 'unlisted'
- Bezpieczne zarządzanie tokenami (zmienne środowiskowe / SSH / docker exec)
"""

import os
import sys
import json
import time
import re
import base64
import logging
import subprocess
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger("vse_worker.pipeline")


def extract_youtube_id(url_or_id: str) -> str:
    """Wyciąga 11-znakowy identyfikator wideo YouTube z URL lub zwraca sam identyfikator."""
    if not url_or_id:
        return ""
    url_or_id = url_or_id.strip()
    if len(url_or_id) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url_or_id):
        return url_or_id

    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$"
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id


class VSEPipeline:
    """4-etapowy pipeline produkcyjny Video SEO Engine (VSE)."""

    def __init__(
        self,
        vse_url: Optional[str] = None,
        jwt_token: Optional[str] = None,
        portal_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        output_dir: Optional[str] = None,
        ssh_key: Optional[str] = None,
        vps_host: Optional[str] = None,
        llm_provider: Optional[str] = None,
    ):
        self.vse_url = (
            vse_url
            or os.environ.get("VSE_URL")
            or os.environ.get("VSE_API_URL")
            or "http://localhost:8085"
        ).rstrip("/")
        self.jwt_token = jwt_token or os.environ.get("VSE_JWT_TOKEN")
        self.portal_id = (
            portal_id
            or os.environ.get("VSE_PORTAL_ID")
            or "2b047d7d-15a1-4d2f-8463-f89c2275bb73"  # prawy.pl
        )
        self.channel_id = (
            channel_id
            or os.environ.get("VSE_CHANNEL_ID")
            or "UCoH2G9By4OX3kcLsc8lHgDw"  # Prawy
        )
        self.output_dir = (
            output_dir
            or os.environ.get("VSE_OUTPUT_DIR")
            or "/home/ubuntu/VSE/Shorts"
        )
        self.ssh_key = (
            ssh_key
            or os.environ.get("VSE_SSH_KEY")
            or os.environ.get("SSH_KEY")
            or r"C:\Users\tomas2\.ssh\oracle-crimson.key"
        )
        self.vps_host = (
            vps_host
            or os.environ.get("VSE_VPS_HOST")
            or os.environ.get("VPS_HOST")
            or "ubuntu@147.224.162.100"
        )
        self.llm_provider = (
            llm_provider
            or os.environ.get("VSE_LLM_PROVIDER")
            or "claude"
        )

        self.last_task: Optional[Dict[str, Any]] = None
        self.last_result: Optional[Dict[str, Any]] = None

    def _exec_container_script(self, python_code: str, timeout: int = 60) -> subprocess.CompletedProcess:
        """
        Uruchamia skrypt python wewnątrz kontenera vse-api.
        Skrypt jest kodowany w base64, co eliminuje problemy ze znakami specjalnymi i cudzysłowami w powłokach.
        Najpierw próbuje lokalnego dockera, a w razie braku przełącza na SSH do VPS.
        """
        b64_code = base64.b64encode(python_code.encode("utf-8")).decode("ascii")
        inline_runner = f"import base64; exec(base64.b64decode('{b64_code}').decode('utf-8'))"

        # 1. Próba lokalnego docker exec
        try:
            cmd = ["docker", "exec", "-w", "/app", "vse-api", "python3", "-c", inline_runner]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if res.returncode == 0 or "No such container" not in res.stderr:
                return res
        except (FileNotFoundError, PermissionError):
            pass

        # 2. Fallback na SSH do VPS
        ssh_cmd = [
            "ssh",
            "-i", self.ssh_key,
            "-o", "StrictHostKeyChecking=no",
            self.vps_host,
            f'docker exec -w /app vse-api python3 -c "{inline_runner}"'
        ]
        return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)

    def get_jwt_token(self, force_refresh: bool = False) -> str:
        """Pobiera token JWT z instancji lub generuje dynamicznie w vse-api przez sekret."""
        if self.jwt_token and not force_refresh:
            return self.jwt_token

        env_token = os.environ.get("VSE_JWT_TOKEN")
        if env_token and not force_refresh:
            self.jwt_token = env_token.strip()
            return self.jwt_token

        token_gen_script = """
import os, datetime
from jose import jwt
secret = os.environ.get('JWT_SECRET_KEY', '')
payload = {
    'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}
print(jwt.encode(payload, secret, algorithm='HS256'))
"""
        res = self._exec_container_script(token_gen_script, timeout=30)
        token = res.stdout.strip()
        if not token or res.returncode != 0:
            err_msg = res.stderr.strip() or res.stdout.strip()
            raise RuntimeError(f"JWT generation failed via docker/ssh: {err_msg}")

        self.jwt_token = token
        return self.jwt_token

    def _get_headers(self) -> Dict[str, str]:
        token = self.get_jwt_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def health_check(self) -> Dict[str, Any]:
        """Sprawdza dostępność VSE API oraz stan autoryzacji."""
        report: Dict[str, Any] = {
            "status": "ok",
            "vse_url": self.vse_url,
            "api_reachable": False,
            "jwt_status": "unknown",
            "details": {}
        }

        # Test endpointu /health lub /v1/users/me
        try:
            r_health = requests.get(f"{self.vse_url}/health", timeout=10)
            report["api_reachable"] = (r_health.status_code == 200)
            report["details"]["health_status_code"] = r_health.status_code
        except Exception as e:
            report["api_reachable"] = False
            report["details"]["health_error"] = str(e)

        # Test JWT autoryzacji
        try:
            token = self.get_jwt_token()
            headers = {"Authorization": f"Bearer {token}"}
            r_auth = requests.get(f"{self.vse_url}/v1/users/me", headers=headers, timeout=10)
            if r_auth.status_code == 200:
                report["jwt_status"] = "ok"
                report["details"]["user"] = r_auth.json().get("email")
            else:
                report["jwt_status"] = f"http_{r_auth.status_code}"
                report["details"]["auth_response"] = r_auth.text[:200]
        except Exception as e:
            report["jwt_status"] = "error"
            report["details"]["jwt_error"] = str(e)

        if not report["api_reachable"] or report["jwt_status"] != "ok":
            report["status"] = "error"

        return report

    def get_status(self) -> Dict[str, Any]:
        """Zwraca ostatni stan przetwarzania zadania."""
        return {
            "status": "idle" if not self.last_result else self.last_result.get("status", "unknown"),
            "vse_url": self.vse_url,
            "portal_id": self.portal_id,
            "channel_id": self.channel_id,
            "last_task": self.last_task,
            "last_result": self.last_result,
        }

    def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wykonuje 4-krokowy pipeline dla podanego zadania.

        task = {
            "video_url": "https://youtube.com/...",
            "video_id": "...",                         # opcjonalnie jeśli podano video_url
            "local_path": "/path/to/video.mp4",        # opcjonalnie dla render
            "portal_id": "2b047d7d-...",               # opcjonalnie, default z env
            "channel_id": "UCoH2G9By4OX3kcLsc8lHgDw",  # opcjonalnie
            "provider": "claude",                      # opcjonalnie
            "steps": [1, 2, 3, 4],                     # opcjonalnie — które kroki wykonać
            "output_dir": "/home/ubuntu/VSE/Shorts"     # opcjonalnie
        }
        """
        video_url = task.get("video_url")
        video_id = task.get("video_id")

        if not video_id and video_url:
            video_id = extract_youtube_id(video_url)
        if not video_url and video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        if not video_url or not video_id:
            return {
                "status": "error",
                "error": "Brak wymaganego video_url lub video_id w zadaniu."
            }

        portal_id = task.get("portal_id") or self.portal_id
        channel_id = task.get("channel_id") or self.channel_id
        provider = task.get("provider") or task.get("llm_provider") or self.llm_provider
        local_path = task.get("local_path")
        output_dir = task.get("output_dir") or self.output_dir
        steps = task.get("steps") or [1, 2, 3, 4]

        result: Dict[str, Any] = {
            "status": "ok",
            "step1_generate": {},
            "step2_inject": {},
            "step3_yt_update": {},
            "step4_shorts": {}
        }

        schema_data: Dict[str, Any] = task.get("schema_data", {})
        wp_post_url: str = task.get("wp_post_url", "")
        wp_post_id: Optional[int] = task.get("wp_post_id")

        headers = self._get_headers()

        # =========================================================================
        # KROK 1: POST /v1/generate
        # =========================================================================
        if 1 in steps:
            logger.info(f"[1/4] POST /v1/generate dla {video_url} (provider={provider})...")
            gen_payload = {
                "video_url": video_url,
                "portal_id": portal_id,
                "provider": provider,
                "llm_provider": provider,
                "lang": "pl",
                "publication_type": "full_analysis"
            }
            if task.get("post_title"):
                gen_payload["post_title"] = task["post_title"]

            try:
                resp_gen = requests.post(
                    f"{self.vse_url}/v1/generate",
                    headers=headers,
                    json=gen_payload,
                    timeout=360
                )
                if resp_gen.status_code == 200:
                    gen_json = resp_gen.json()
                    schema_data = gen_json.get("schema_data", {})
                    result["step1_generate"] = {
                        "status": "ok",
                        "status_code": resp_gen.status_code,
                        "schema_data": schema_data
                    }
                else:
                    result["step1_generate"] = {
                        "status": "error",
                        "status_code": resp_gen.status_code,
                        "error": resp_gen.text[:500]
                    }
                    result["status"] = "error"
            except Exception as e:
                result["step1_generate"] = {
                    "status": "error",
                    "error": str(e)
                }
                result["status"] = "error"

        # =========================================================================
        # KROK 2: POST /v1/inject (ZAWSZE post_status='draft')
        # =========================================================================
        if 2 in steps:
            if result["status"] == "error" and 1 in steps and not schema_data:
                result["step2_inject"] = {
                    "status": "skipped",
                    "error": "Krok 1 nie powiódł się lub brak schema_data."
                }
            else:
                logger.info(f"[2/4] POST /v1/inject do WordPress (post_status='draft')...")
                inject_payload = {
                    "portal_id": portal_id,
                    "video_url": video_url,
                    "schema_data": schema_data,
                    "post_status": "draft"  # REGUŁA BEZWZGLĘDNA: ZAWSZE draft
                }

                try:
                    resp_inj = requests.post(
                        f"{self.vse_url}/v1/inject",
                        headers=headers,
                        json=inject_payload,
                        timeout=120
                    )
                    if resp_inj.status_code == 200:
                        inj_json = resp_inj.json()
                        wp_post_id = inj_json.get("wp_post_id") or inj_json.get("post_id")
                        wp_post_url = inj_json.get("post_url") or inj_json.get("url") or ""
                        result["step2_inject"] = {
                            "status": "ok",
                            "status_code": resp_inj.status_code,
                            "wp_post_id": wp_post_id,
                            "post_url": wp_post_url
                        }
                    else:
                        result["step2_inject"] = {
                            "status": "error",
                            "status_code": resp_inj.status_code,
                            "error": resp_inj.text[:500]
                        }
                        result["status"] = "error"
                except Exception as e:
                    result["step2_inject"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    result["status"] = "error"

        # =========================================================================
        # KROK 3: Update YouTube metadata (ZAWSZE privacyStatus='unlisted')
        # =========================================================================
        if 3 in steps:
            logger.info(f"[3/4] Update YouTube metadata dla {video_id} (privacyStatus='unlisted')...")
            yt_payload = {
                "channel_id": channel_id,
                "video_id": video_id,
                "wp_post_url": wp_post_url or "",
                "schema_data": schema_data
            }
            b64_yt_payload = base64.b64encode(
                json.dumps(yt_payload, ensure_ascii=False).encode("utf-8")
            ).decode("ascii")

            yt_update_script = f"""
import asyncio
import base64
import json
import sys
from api.db import AsyncSessionLocal
from api.models.youtube_channel import YouTubeChannel
from api.core.youtube_publish import _build_credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy.future import select

async def main():
    raw_payload = base64.b64decode("{b64_yt_payload}").decode("utf-8")
    payload = json.loads(raw_payload)

    target_channel_id = payload.get("channel_id")
    video_id = payload.get("video_id")
    wp_url = payload.get("wp_post_url", "")
    schema = payload.get("schema_data", {{}})

    async with AsyncSessionLocal() as db:
        # 1. Pobierz kanał z DB
        ch = None
        if target_channel_id:
            res = await db.execute(select(YouTubeChannel).where(YouTubeChannel.youtube_channel_id == target_channel_id))
            ch = res.scalars().first()
        if not ch:
            res_active = await db.execute(select(YouTubeChannel).where(YouTubeChannel.is_active == True))
            ch = res_active.scalars().first()

        if not ch:
            print(json.dumps({{"error": "Brak aktywnego rekordu YouTubeChannel w bazie VSE"}}))
            return

        creds = _build_credentials(ch)
        creds.refresh(Request())
        yt = build('youtube', 'v3', credentials=creds)

        # 2. Buduj opis filmu
        desc_parts = []
        hook = schema.get('youtube_description_hook', '')
        body = schema.get('youtube_description_body', '')
        if hook:
            desc_parts.append(hook)
        if body:
            desc_parts.append(body)

        if wp_url:
            desc_parts.append(f"🔗 Pełny artykuł: {{wp_url}}")

        mid_cta = schema.get('youtube_mid_cta', '')
        if mid_cta:
            desc_parts.append(mid_cta)

        chapters = schema.get('chapters', [])
        if chapters:
            ch_lines = []
            for item in chapters:
                t = item.get('time', 0)
                mins = int(t // 60)
                secs = int(t % 60)
                ch_lines.append(f"{{mins:02d}}:{{secs:02d}} {{item.get('label', '')}}")
            desc_parts.append("ROZDZIAŁY:\\n" + "\\n".join(ch_lines))

        credits = schema.get('youtube_credits', {{}})
        if credits:
            cr_lines = []
            if credits.get('host'):
                cr_lines.append(f"Prowadzący: {{credits.get('host')}}")
            if credits.get('guest'):
                cr_lines.append(f"Gość: {{credits.get('guest')}}")
            if credits.get('material_type'):
                cr_lines.append(f"Typ materiału: {{credits.get('material_type')}}")
            if cr_lines:
                desc_parts.append("\\n".join(cr_lines))

        tags = schema.get('tags', [])
        hashtags = schema.get('youtube_hashtags', [])
        if hashtags:
            desc_parts.append(" ".join(hashtags))
        elif tags:
            desc_parts.append(" ".join([f"#{{t.replace(' ', '')}}" for t in tags[:5]]))

        full_desc = "\\n\\n".join(desc_parts)
        title = schema.get('yt_title') or schema.get('seo_title') or schema.get('post_title') or ''
        if len(title) > 100:
            title = title[:97] + '...'

        vid_res = yt.videos().list(part='snippet,status', id=video_id).execute()
        if not vid_res.get('items'):
            print(json.dumps({{"error": f"Film {{video_id}} nie został znaleziony na YouTube"}}))
            return

        item = vid_res['items'][0]
        cat_id = item['snippet'].get('categoryId', '25')

        update_body = {{
            'id': video_id,
            'snippet': {{
                'title': title or item['snippet'].get('title', ''),
                'description': full_desc,
                'tags': tags,
                'categoryId': cat_id,
                'defaultLanguage': 'pl',
                'defaultAudioLanguage': 'pl'
            }},
            'status': {{
                'privacyStatus': 'unlisted',  # REGUŁA BEZWZGLĘDNA: ZAWSZE unlisted!
                'selfDeclaredMadeForKids': False
            }}
        }}

        update_res = yt.videos().update(part='snippet,status', body=update_body).execute()
        print(json.dumps({{
            "status": "ok",
            "title": update_res['snippet']['title'],
            "privacyStatus": update_res['status']['privacyStatus']
        }}))

asyncio.run(main())
"""
            try:
                res_yt = self._exec_container_script(yt_update_script, timeout=60)
                parsed_yt = None
                for line in res_yt.stdout.strip().splitlines():
                    try:
                        parsed_candidate = json.loads(line)
                        if isinstance(parsed_candidate, dict) and ("status" in parsed_candidate or "error" in parsed_candidate):
                            parsed_yt = parsed_candidate
                            break
                    except json.JSONDecodeError:
                        continue

                if parsed_yt and parsed_yt.get("status") == "ok":
                    result["step3_yt_update"] = {
                        "status": "ok",
                        "title": parsed_yt.get("title"),
                        "privacyStatus": parsed_yt.get("privacyStatus", "unlisted")
                    }
                else:
                    err = (parsed_yt.get("error") if parsed_yt else None) or res_yt.stderr.strip() or res_yt.stdout.strip()
                    result["step3_yt_update"] = {
                        "status": "error",
                        "error": err or "Błąd aktualizacji metadanych YouTube"
                    }
                    result["status"] = "error"
            except Exception as e:
                result["step3_yt_update"] = {
                    "status": "error",
                    "error": str(e)
                }
                result["status"] = "error"

        # =========================================================================
        # KROK 4: POST /v1/shorts/candidates & POST /v1/shorts/render
        # =========================================================================
        if 4 in steps:
            logger.info(f"[4/4] Propozycje Shortów i render jobs dla {video_id}...")
            cand_payload = {
                "youtube_id": video_id,
                "youtube_url": video_url,
                "count_emotional": task.get("count_emotional", 5),
                "count_professional": task.get("count_professional", 5),
                "provider": provider,
                "portal_id": portal_id
            }

            candidates_list: List[Dict[str, Any]] = []
            render_jobs: List[Dict[str, Any]] = []

            try:
                resp_cand = requests.post(
                    f"{self.vse_url}/v1/shorts/candidates",
                    headers=headers,
                    json=cand_payload,
                    timeout=300
                )
                if resp_cand.status_code == 200:
                    cand_json = resp_cand.json()
                    candidates_list = cand_json.get("candidates", [])
                else:
                    result["step4_shorts"] = {
                        "status": "error",
                        "status_code": resp_cand.status_code,
                        "error": resp_cand.text[:500],
                        "candidates": [],
                        "render_jobs": []
                    }
                    result["status"] = "error"
            except Exception as e:
                result["step4_shorts"] = {
                    "status": "error",
                    "error": str(e),
                    "candidates": [],
                    "render_jobs": []
                }
                result["status"] = "error"

            if candidates_list:
                if local_path:
                    for idx, c in enumerate(candidates_list[:5]):
                        render_payload = {
                            "youtube_id": video_id,
                            "youtube_url": video_url,
                            "local_path": local_path,
                            "start_sec": float(c.get("start_sec", 0)),
                            "end_sec": float(c.get("end_sec", 0)),
                            "candidate_data": c,
                            "render_format": "9:16",
                            "subtitles": "srt",
                            "output_dir": output_dir,
                            "portal_id": portal_id
                        }
                        try:
                            resp_render = requests.post(
                                f"{self.vse_url}/v1/shorts/render",
                                headers=headers,
                                json=render_payload,
                                timeout=60
                            )
                            if resp_render.status_code == 200:
                                r_res = resp_render.json()
                                job_id = r_res.get("job_id") or r_res.get("id")
                                render_jobs.append({
                                    "job_id": job_id,
                                    "title": c.get("title"),
                                    "start_sec": c.get("start_sec"),
                                    "end_sec": c.get("end_sec"),
                                    "local_path": local_path,
                                    "status": "submitted"
                                })
                            else:
                                render_jobs.append({
                                    "title": c.get("title"),
                                    "status": "error",
                                    "status_code": resp_render.status_code,
                                    "error": resp_render.text[:200]
                                })
                        except Exception as re:
                            render_jobs.append({
                                "title": c.get("title"),
                                "status": "error",
                                "error": str(re)
                            })
                else:
                    render_jobs.append({
                        "status": "skipped",
                        "message": "Brak parametru local_path — zadania renderowania pominięte."
                    })

                result["step4_shorts"] = {
                    "status": "ok" if any(j.get("status") in ("submitted", "skipped") for j in render_jobs) else "error",
                    "candidates": candidates_list,
                    "render_jobs": render_jobs
                }

        self.last_task = task
        self.last_result = result
        return result
