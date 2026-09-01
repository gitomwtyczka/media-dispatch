# Discord Editorial Center — Redaktor Naczelny

## Cel
Kanał decyzyjny dla Redaktora Naczelnego. Każdy kandydat do publikacji
przechodzi przez Discord zanim trafi do PressAI/VSE.

## Architektura

Discord Interactions API (webhook-based, bez WebSocket bota)

### Flow kandydata
1. Worker (kurier365/biznesciti/prawy) tworzy ContentCandidate
2. Worker wysyła Rich Embed do odpowiedniego kanału Discord
3. Redaktor klika przycisk w ciągu X minut/godzin
4. Discord wysyła POST do /api/v1/discord/interactions (FastAPI)
5. Endpoint dispatchuje do odpowiedniego workera
6. Worker generuje draft WP przez PressAI
7. Bot edytuje oryginalną wiadomość z linkiem do draftu

## Struktura embed

**Tytuł:** [KANDYDAT] Tytuł artykułu
**Kolor:** żółty (nowy) / zielony (zaakceptowany) / czerwony (odrzucony)
**Pola:**
- 📰 Źródło: [nazwa] | Priorytet: P0/P1/P2
- 📝 Resume: max 300 znaków
- 🔗 Oryginał: [link]
- 📅 Data: [timestamp]
- 📈 Trend Score: [X.XX] (z Content Radar)

**Przyciski (Action Row):**
[✅ Akceptuj] [❌ Odrzuć] [⏰ Odrocz D+1] [⏰ Odrocz D+7] [💬 Uwagi]

## Kanały Discord

| Kanał | Portal | Kto decyduje |
|---|---|---|
| #editorial-prawy | prawy.pl | Redaktor/właściciel |
| #editorial-kurier365 | kurier365.pl | Redaktor kurier365 |
| #editorial-biznesciti | biznesciti.com | Redaktor biznesciti |
| #pressai-production | wszystkie | Log wygenerowanych draftów |

## Konfiguracja techniczna

### Zmienne środowiskowe
```
DISCORD_WEBHOOK_PRAWY=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_KURIER365=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_BIZNESCITI=https://discord.com/api/webhooks/...
DISCORD_APPLICATION_ID=...
DISCORD_PUBLIC_KEY=...  # do weryfikacji ed25519
DISCORD_BOT_TOKEN=...   # do edycji wiadomości
```

### FastAPI endpoint (do zaimplementowania)
```python
POST /api/v1/discord/interactions
- Weryfikacja: nacl.signing.VerifyKey (ed25519)
- Obsługuje: PING (type=1) i MESSAGE_COMPONENT (type=3)
- custom_id format: {action}_{candidate_id}_{portal}
  np. accept_abc12345_kurier365
      reject_abc12345_biznesciti
      postpone_d1_abc12345_kurier365
```

## Integracja z istniejącą infrastrukturą

Discord webhook już istnieje w crimson-void:
- `backend/discord_notifier.py` — webhook DISCORD_WEBHOOK_URL
- Rozszerzamy o: interactions endpoint + przyciski + modale

## Status implementacji
- [ ] Stworzyć Discord Application (developer.discord.com)
- [ ] Zarejestrować kanały #editorial-* na serwerze Impresja
- [ ] Dodać endpoint /api/v1/discord/interactions do crimson-void FastAPI
- [ ] Zaktualizować WorkerBase.notify_editor() → Discord embed zamiast Telegram
- [ ] Skonfigurować zmienne środowiskowe na VPS
