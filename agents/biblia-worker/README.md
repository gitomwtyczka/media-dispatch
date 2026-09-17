# Biblia Worker

Autonomiczny agent obsługujący pełny potok publikacji materiałów z playlisty biblijnej "Prawy Biblijny" do VSE i WordPressa (prawy.pl).

## Wymagania
```bash
pip install requests PyJWT
```

## Uruchomienie

**1. Health Check (Test JWT + VSE):**
```bash
python worker.py --health
```

**2. Pojedynczy film:**
```bash
python worker.py --video-id AMd9euz4dvM --publish-date "2026-09-17 00:00:01" --status future
```

**3. Batch z pliku JSON:**
```bash
python worker.py --batch batch.json
```
*(Format JSON: `[{"yt_id": "...", "publish_date_local": "...", "publish_date_gmt": "...", "status": "future"}]`)*

## Parametry CONFIG
Są na sztywno zaszyte w `config.py` aby worker nie musiał szukać parametrów podczas startu.
Zgodne ze stanem produkcyjnym na dzień 16.09.2026.
