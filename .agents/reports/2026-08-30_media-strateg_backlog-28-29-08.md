# Raport: Backlog Biblia 28.08 + 29.08.2026

> Data: 2026-08-30 | media-strateg | media-dispatch

## Wyniki

| Film | Status | WP Post ID | URL | YT ID | YT Status |
|------|--------|-----------|-----|-------|----------|
| Biblia 28.08.2026 | ✅ OK | #125317 | https://prawy.pl/przypowiesc-o-dziesieciu-pannach-mateusz-25-1-13/ | S69T_H-DJy4 | Public + SEO |
| Biblia 29.08.2026 | ✅ OK | #125322 | https://prawy.pl/przypowiesc-o-talentach-znaczenie-biblijnej-opowiesci-o-slugach/ | HaY1VnzG_3o | Public + SEO |

## Szczegóły

- Whisper: VTT z cache VPS (nie powtarzano renderowania)
- Napisy YT: wgrane przez captions.insert na kanał Prawy TV
- WP antydatowanie: 28.08.2026 00:00 CEST / 29.08.2026 00:00 CEST
- Playlista Ewangelia: oba filmy zweryfikowane

## Wiedza odkryta (4 nowe pułapki — zapisane do konstytucji v2)

1. `llm_provider="gemini"` nie działa → używać `"claude"` (VPS ma tylko ANTHROPIC_API_KEY)
2. `publication_type="film"` → HTTP 422, używać `"full_analysis"`
3. `portal_id="prawy"` nie działa → UUID: `2b047d7d-15a1-4d2f-8463-f89c2275bb73`
4. `/v1/youtube/channels` nie zwraca access_token → SSH + `_build_credentials(ch).refresh()`

## Commity

- Konstytucja v2: `9faf113`
- biblia_backlog_pipeline.py v2: `c988796`
- AGENTS.md Dispatch Protocol: `56b691d`
- CURRENT_BRIEF update: w tym commicie

## Następne zadania

- [ ] QA: weryfikacja schema VideoObject na prawy.pl (7 postów + 2 backlog)
- [ ] Implementacja Pipeline B (Prawy TV, bez Whispera)
- [ ] Update biblia_full_pipeline.py do v2 (claude/full_analysis/UUID)
