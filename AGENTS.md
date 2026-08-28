# media-dispatch - AGENTS.md

Reguly specyficzne dla workspace media-dispatch.
Uzupelnia RULE[user_global] - nie zastepuje.

## Cel workspace

media-dispatch to autonomiczne centrum zarzadzania contentem.
System agentow AI ktory zbiera tematy, produkuje tresci i dystrybuuje je
na wiele platform bez recznej pracy redakcyjnej.

Platformy docelowe: WordPress portale, YouTube, TikTok, Telegram.
Systemy produkcji: VSE (Video SEO Engine), pressAI, Shorts Machine.

## Mapa workspace

| Workspace | Repo | Branch | Owner |
|---|---|---|---|
| media-dispatch | media-dispatch | main | gitomwtyczka |

## Callsigny

- media-strateg - Supervisor / Redaktor Naczelny
- media-dev-XX - Implementacja workerow
- media-analyst - Analiza, raportowanie
- media-deploy - Deploy workerow

## Architektura

### Warstwa 1 - Intelligence
- feed-crawler-worker - RSS monitoring
- content-radar-worker - Google Trends + social

### Warstwa 2 - Editorial
- redaktor-naczelny - meta-agent syntetyzujacy wywiad

### Warstwa 3 - Production
- vse-worker - video -> SEO + shorty + draft WP
- pressai-worker - tekst/link/mail -> artykul

### Warstwa 4 - Distribution
- youtube-worker, wp-publisher, tiktok-worker, telegram-worker

## Infrastruktura

| Element | Wartosc |
|---------|---------|
| VPS | oracle-crimson 147.224.162.100 |
| VSE URL | https://vse.impresjapr.pl |
| SSH key | ~/.ssh/oracle-crimson.key |

## Reguly implementacyjne

1. Kazdy worker implementuje: health_check(), process(task), get_status()
2. Stan per content item w shared/state/
3. Zadania przez task queue: shared/tasks/queue.json
4. Raporty do .agents/reports/ + dual-write do sonic-void inbox
5. Heartbeat na starcie sesji

*Inicjacja: media-dev-01 | 28.08.2026*