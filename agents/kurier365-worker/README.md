# kurier365-worker

> media-dispatch | media-dev-architect | 31.08.2026  
> Status: **v0.1 skeleton** — architektura gotowa, sources w placeholder mode

## Cel

Orkiestrator contentu dla portalu **kurier365.pl**.
Zbiera kandydatów z wielu źródeł, ocenia ich wirusowość przez Content Radar
i wysyła do Redaktora Naczelnego (Telegram bot) do zatwierdzenia.

## Uruchomienie

```bash
# Ustawienie zmiennych (opcjonalne w v0.1 — źródła są placeholder)
export CONTENT_RADAR_JWT=eyJ...   # JWT z radar.impresjapr.pl (wymagany plan Pro+)
export PRESSAI_JWT=eyJ...          # JWT PressAI (gdy Gmail/RSS aktywne)
export NEWSERIA_USER=login
export NEWSERIA_PASS=haslo

# Status
python agents/kurier365-worker/worker.py --health

# Zbierz kandydatów
python agents/kurier365-worker/worker.py --run

# Top-5 w JSON
python agents/kurier365-worker/worker.py --run --top 5 --json
```

## Architektura

```
Kurier365Worker
├── Sources (co zbierać)
│   ├── GmailSource        — tobroz@gmail.com (whitelist nadawców)
│   ├── RSSSource          — UOKiK, PAP, Nauka w Polsce, ISBNews
│   └── NewseriaSource     — agencja B2B z Eco-Bias Gate
└── Trend Signals (jak oceniać viralność)
    ├── ContentRadarSignal — ✅ LIVE (radar.impresjapr.pl)
    ├── GoogleTrendsSignal — fallback placeholder
    └── SocialTrendsSignal — fallback placeholder
```

## Biała lista nadawców Gmail

| Nadawca | Wzorzec | Wymaga review |
|---------|---------|---------------|
| Cezary Rudiński | `*rudzinski*` | ✅ Tak |
| Arkadiusz Bińczyk | `*binczyk*` | ❌ Nie |
| WEI | `*@wei.org.pl` | ❌ Nie |
| Biały Kruk | `*@bialykruk.pl` | ❌ Nie |

## Feedy RSS

| Feed | Kategoria | Priorytet |
|------|-----------|----------|
| UOKiK | prawo-konsumenta | 9 |
| PAP | kraj | 8 |
| Nauka w Polsce | nauka | 7 |
| ISBNews | finanse | 7 |

## Eco-Bias Gate (Newseria)

Filtr neutralności edytorskiej — blokuje depesze z silnym politycznym biasęm ekologicznym.
Lista słów kluczowych w `agents/base/sources/newseria_source.py`.

## Content Radar Integration

| Para | Wartość |
|------|--------|
| URL | `https://radar.impresjapr.pl` |
| Endpoint | `GET /api/v1/trending/global?limit=50` |
| Auth | JWT Bearer token |
| Wymagany plan | Pro lub Enterprise |

Viral Score formula:
```
views * 0.1 + likes * 1.0 + shares * 3.0 + comments * 2.0
+ Google Trends boost (+10 jeśli interest > 70)
```

## Status wdrożenia

| Komponent | Status | Do aktywacji |
|-----------|--------|--------------|
| `ContentRadarSignal` | ✅ LIVE (jak jest JWT) | `CONTENT_RADAR_JWT` |
| `GmailSource` | 🔴 Placeholder | PressAI Gmail API + `PRESSAI_JWT` |
| `RSSSource` | 🔴 Placeholder | Implementacja feed parsera (Faza 2) |
| `NewseriaSource` | 🔴 Placeholder | Konto Newseria + `NEWSERIA_USER/PASS` |
| `process()` (Telegram) | 🔴 Placeholder | Telegram bot API (Faza 2) |

## Architektura bazowa

Szczegółowa dokumentacja: [`agents/base/README.md`](../base/README.md)
