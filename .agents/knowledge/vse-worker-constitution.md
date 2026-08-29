# VSE Worker Constitution (media-dispatch)

> Ostatnia aktualizacja: 2026-08-29 | media-strateg-01

Dokument opisujący zasady operacyjne dla workerów z rodziny `vse-worker` działających na rzecz VSE (Video SEO Engine).

## 1. Środowisko VSE

- **URL publiczny:** `https://vse.impresjapr.pl`
- **Port wewnętrzny:** `8085` (Uwaga: NIE 8000!)
- **Kontenery Docker:** `vse-api`, `vse-web`, `vse-postgres`
- **Baza danych:** `container=vse-postgres`, `user=vse`, `db=vse`
- **Serwer VPS:** Oracle ARM `ubuntu@147.224.162.100`
- **Klucz SSH:** `C:\Users\tomas2\.ssh\oracle-crimson.key` (Zawsze używaj pełnej ścieżki Windows dla `scp`)

## 2. Auth flow — Jak pobrać JWT Token

API VSE wymaga autoryzacji tokenem JWT.
Konto administratora: `tobroz@gmail.com`
Hasło można uzyskać odczytując zmienne środowiskowe na VPS:
```bash
# Odczyt hasła:
ssh -i C:\Users\tomas2\.ssh\oracle-crimson.key -o StrictHostKeyChecking=no ubuntu@147.224.162.100 "cat /home/ubuntu/video-seo-engine/.env | grep PASS"
```

Generowanie tokenu przez port wewnętrzny (8085):
```bash
ssh -i C:\Users\tomas2\.ssh\oracle-crimson.key -o StrictHostKeyChecking=no ubuntu@147.224.162.100 "curl -s -X POST http://localhost:8085/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{\"email\":\"tobroz@gmail.com\",\"password\":\"HASLO_Z_ENV\"}'"
```

## 3. Audio Pipeline

- **Endpoint:** `POST /v1/audio/generate`
- **Parametry:** `file` (MP3), `publication_type`, `portal_id`, `lang=pl`, `llm_provider=gemini`
- **Model transkrypcji:** `faster-whisper small` (uruchomiony na CPU, int8)
- **Timeout:** 600s (Przetworzenie 8-minutowego pliku audio zajmuje ok. 2-3 minuty)
- **Output:** Zwraca obiekt `GenerateResponse` zawierający m.in. `schema_data` (w tym transkrypt VTT)

## 4. YouTube OAuth

Kanały YouTube powiązane z kontem `tobroz@gmail.com` współdzielą OAuth (Prawy TV, Prawy Biblijny).
Tokeny odświeżające są przechowywane w bazie danych VSE lub poprzez konfigurację z `.env`.
Przy żądaniach zapisu (`videos.update`) sprawdzaj czy tokeny posiadają uprawnienie (scope) `https://www.googleapis.com/auth/youtube`.

## 5. Znane Pułapki

1. **403 Forbidden przy wysyłce na YouTube:** Brak pełnego scope `write` w odświeżonym tokenie. Zawsze sprawdzaj czy credentialse mają dodany scope `https://www.googleapis.com/auth/youtube`.
2. **Utrata danych podczas restartu kontenera:** Używaj pre-deploy backup (`/home/ubuntu/scripts/backup_pre_deploy.sh`).
3. **Plik 7865 linii:** Nie próbuj czytać całego kodu frontendu (np. `dashboard-inner.tsx`) jednym narzędziem, używaj `grep` i `sed` po SSH.
4. **Port binding na VPS:** VSE działa wewnątrz jako port `8085` dla API. Uważaj na bindingi `127.0.0.1`.
5. **Escape stringów w SSH via PowerShell:** Rozszerzone zapytania lub komendy zapisuj do pliku lokalnego, przesyłaj używając pełnych ścieżek przez `scp` i dopiero wykonuj `bash /tmp/skrypt.sh`.

## 6. Wzorce Kodu

**Prawidłowy SCP (Windows):**
```powershell
scp -i C:\Users\tomas2\.ssh\oracle-crimson.key -o StrictHostKeyChecking=no "C:\Users\tomas2\.gemini\antigravity\playground\media-dispatch\tmp\skrypt.sh" ubuntu@147.224.162.100:/tmp/skrypt.sh
```

**Odpytywanie DB o listę portali (przykład):**
```powershell
ssh -i C:\Users\tomas2\.ssh\oracle-crimson.key -o StrictHostKeyChecking=no ubuntu@147.224.162.100 "docker exec vse-postgres psql -U vse -d vse -c 'SELECT id, name FROM portals;'"
```

## 7. Kanały i profile w VSE

Zdefiniowane w `video-seo-engine/channels/`:
- `prawy-tv.yaml`
- `prawy.yaml`
- `prawy-biblijny.yaml` (współdzieli token OAuth z prawy-tv)
