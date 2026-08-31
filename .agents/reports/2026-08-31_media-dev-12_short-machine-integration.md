# Raport: Integracja i aktualizacja dokumentacji Short Machine API

> **Callsign**: `media-dev-12`  
> **Workspace**: `media-dispatch`  
> **Data**: 2026-08-31 23:07 CEST  
> **Status**: Kompletny (100% zrealizowane)

---

## 1. Cel zadania

Aktualizacja konstytucji operacyjnej, specyfikacji `shorts-agent` oraz roadmapy projektu `media-dispatch` po oficjalnym wdrożeniu produkcyjnym endpointu **Short Machine API** (`POST /v1/shorts/describe`) w silniku VSE na VPS.

---

## 2. Podsumowanie Wdrożonych Zmian

### A. `.agents/knowledge/vse-worker-constitution.md` (Commit: `8a7c9b1`)
- Dodano dedykowaną sekcję `## 7. Short Machine API (produkcja od 31.08.2026)` z pełnym kontraktem I/O i pułapkami.
- Zaktualizowano listę tras API o `/v1/shorts/describe`.
- Dodano wzorzec zapytania Python z timeoutem 60s.
- Wzbogacono tabelę *Znane Pułapki* o pozycje 15–18 (brak `#Shorts`, brak URL w opisach, limit 45 zn dla tytułów, Comments API do przypinania komentarzy).

### B. `agents/shorts-agent/README.md` (Commit: `2ef7ca2`)
- Dodano sekcję `## Integracja Short Machine`:
  - Status produkcyjny od 31.08.2026
  - Endpoint `POST /v1/shorts/describe` z Bearer JWT auth
  - JSON input (`youtube_id`, `portal_id`) i output (`optimized_title`, `description`, `hashtags`, `pinned_comment`, `related_video_id`)
  - Przepływ algorytmiczny audytu i wzbogacania metadanych
  - Reguła wykrywania braku opisu SM: `description.length < 50` lub tytuł tożsamy z nazwą pliku `.mp4`.
- Zsynchronizowano pozostałe sekcje (usunięto nieaktualne odniesienia do starych szkiców endpointów i tagu `#Shorts` w tytule).

### C. `ROADMAP.md` (Commit: `70fd02d`)
- Zaktualizowano Fazę 1b: `shorts-agent + Short Machine Integration (API gotowe na produkcji od 31.08.2026. Implementacja workers: Q1 09.2026)`.
- Zaktualizowano Priorytety MVP o status gotowości produkcyjnej API.

### D. `docs/shorts-pipeline-architecture.md` (Commit: `eaf9211`)
- Zaktualizowano architekturę pipeline'u i diagramy o endpoint `POST /v1/shorts/describe` oraz nowe wytyczne SEO 2026.

---

## 3. Specyfikacja Produkcyjna Short Machine API

```http
POST /v1/shorts/describe HTTP/1.1
Host: vse.impresjapr.pl
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "youtube_id": "ABC123defGH",
  "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
}
```

**Odpowiedź JSON:**
```json
{
  "optimized_title": "max 45 znaków, front-loaded",
  "description": "150-350 znaków, bez URL, słowa kluczowe z transkrypcji",
  "hashtags": ["#tag1", "#tag2"],
  "pinned_comment": "Pytanie polaryzujące do pinowania",
  "related_video_id": "YT ID powiązanego materiału"
}
```

---

## 4. Wykaz Commitów

1. `76cdc2e` — `heartbeat: media-dev-12 start [media-dev-12]`
2. `8a7c9b1` — `docs: add Short Machine API section to vse-worker-constitution.md [media-dev-12]`
3. `2ef7ca2` — `docs: update agents/shorts-agent/README.md with Short Machine API integration [media-dev-12]`
4. `70fd02d` — `docs: update ROADMAP.md with Short Machine production API status [media-dev-12]`
5. `eaf9211` — `docs: update shorts-pipeline-architecture.md with production Short Machine API [media-dev-12]`

---

*[media-dev-12 | media-dispatch 31.08.2026]*
