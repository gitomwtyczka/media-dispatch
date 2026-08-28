# media-dispatch

Content Operating System — autonomiczne centrum zarządzania contentem.

## Architektura

```
[Wywiad] -> [Redaktor Naczelny] -> [Producenci] -> [Platformy]
RSS/Trends   meta-agent LLM      VSE/pressAI    YT/WP/TikTok
```

## Agenci

| Worker | Opis | Status |
|--------|------|--------|
| vse-worker | Video SEO Engine pipeline | MVP |
| pressai-worker | Publikacja przez pressAI | Planowany |
| feed-crawler-worker | RSS monitoring | Planowany |
| content-radar-worker | Trendy | Planowany |
| redaktor-naczelny | Meta-agent editorial | Planowany |

Dokumentacja: ROADMAP.md | AGENTS.md
