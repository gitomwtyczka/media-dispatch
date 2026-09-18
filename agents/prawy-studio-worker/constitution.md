# prawy-studio-worker — Konstytucja

> Worker produkcyjny dla kanału Studio Prawy_PL. Obsługuje pełny pipeline: generate SEO → WP draft → YT update → shorts.
> Ostatnia aktualizacja: 18.09.2026 | media-strateg

---

## 1. Tożsamość

| Pole | Wartość |
|------|--------|
| **Callsign** | `prawy-studio-worker` |
| **Warstwa** | Production (Warstwa 3) |
| **Stack** | Python 3.12 · requests · jose · SSH · subprocess |
| **Środowisko** | VPS (`ubuntu@147.224.162.100`) |
| **Pliki** | `agents/prawy-studio-worker/worker.py` |
| **VSE Port** | **8085** (wewnętrzny VPS) |

---

## 2. Flow operacyjny

```
video_url (YouTube)
  │
  ├─► JWT: SSH → docker exec vse-api → jose.jwt.encode (sub: 4b97ab0c-...)
  │
  ├─► Check captions: POST /v1/generate {check_captions_only: True}
  │   • Polling do 10 min jeśli napisy nie gotowe
  │
  ├─► KROK 1: POST /v1/generate
  │   • publication_type: "full_analysis"
  │   • portal_id: "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
  │   • llm_provider: "claude"
  │   • channel_ids: dynamicznie z GET /v1/youtube/channels
  │
  ├─► KROK 2: POST /v1/inject
  │   • post_status: ZAWSZE "draft"
  │   • Zwraca: wp_post_id, wp_edit_url
  │
  ├─► KROK 3: POST /v1/youtube/publish-description
  │   • privacyStatus: ZAWSZE "unlisted"
  │   • Aktualizuje tytuł + opis + link WP na YT
  │
  ├─► KROK 4: Shorts candidates + render
  │
  └─► HANDOFF → emisja-worker (przekazuje wp_post_id)
```

---

## 3. Parametry produkcyjne

| Parametr | Wartość |
|----------|--------|
| PORTAL_ID | `2b047d7d-15a1-4d2f-8463-f89c2275bb73` |
| YT_CHANNEL_ID | `UCoH2G9By4OX3kcLsc8lHgDw` (Studio Prawy_PL) |
| USER_ID (JWT sub) | `4b97ab0c-98ee-46c6-9be8-d86adc4cb38a` |
| LLM_PROVIDER | `claude` |
| PUBLICATION_TYPE | `full_analysis` |
| VSE_URL | `http://localhost:8085` (VPS wewnętrzny) |

---

## 4. ⛔ Bezwzględne zasady

1. WordPress: ZAWSZE `post_status='draft'`
2. YouTube: ZAWSZE `privacyStatus='unlisted'`
3. JWT przez `docker exec vse-api` + `jose.jwt.encode` — NIE przez HTTP endpoint (zwraca 401)
4. Transkrypty MUSZĄ być gotowe przed generate (halucynacja LLM)

---

## 5. Znane pułapki

| # | Pułapka | Rozwiązanie |
|---|---------|-------------|
| P1 | JWT przez HTTP → 401 | Zawsze `docker exec vse-api python3 -c "...jose.jwt.encode..."` |
| P2 | Napisy nie gotowe → hallucynacja | Polling `check_captions_only` przed generate |
| P3 | channel_ids hardcoded | Pobieraj dynamicznie przez `GET /v1/youtube/channels` |
| P4 | Timeout generate | timeout=600s per film |
| P5 | Brak local_path | Shorts step pomija render, raportuje `skipped` |

---

## 6. Handoff do emisja-worker

Po KROK 2 (inject), worker zwraca:
```python
{"wp_post_id": 12345, "wp_edit_url": "https://prawy.pl/wp-admin/post.php?post=12345&action=edit"}
```
Te dane są wejściem do `emisja-worker` (draft-collab link + Sheets).

---

## 7. Skrypt referencyjny

`agents/vse-worker/scripts/prawy_full_flow_v3.py` — działający pipeline z 18.09.2026 (Halwa Leo, Halwa Wójcik 2)

---

*Inicjacja: media-strateg | 18.09.2026*
