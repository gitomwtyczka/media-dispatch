# Handoff — media-strateg | 15.09.2026

## Status sesji
✅ Thumbnail generator v9 gotowy i zatwierdzony przez użytkownika  
🟡 Batch thumbnails dla 23 shortów — wymaga poprawnego mapowania MP4  
🟡 Czyszczenie @naszkanal — quota YouTube wyczerpana, retry rano  

## Co zostało zrobione

### Thumbnail Generator v9 (finalny)
- Layout 1:1 z PSD użytkownika (`wzorzec mój v5_thumbnail.psd`)
- Commit: `4fbba22b` — `agents/shorts-agent/thumbnail_generator.py`
- Commit: `7175c39b` — `agents/shorts-agent/constitution.md` +Thumbnail Pipeline
- Zatwierdzone screeny: Bruksela, Antify — "te dwie są zrobione świetnie"

### Współrzędne PSD (nie zmieniaj!):
```
BADGE  = (92,  76, 498, 288)
CTA    = (131, 211, 913, 394)
APLA   = (0,   664, 1080, 1759)
REDBAR = (105, 664, 116,  1759)
TITLE  = (151, 739, 1017, 1508)
GUEST  = (151, 1629, 942, 1699)
```

### Pliki lokalne
- Skrypt v9: `C:\Users\tomas2\.gemini\antigravity\brain\52e6ce60-4c80-4fc4-85cf-3d58b36a288b\scratch\test_thumb_v9.py`
- Thumbnaile testowe: `C:\VSE\Shorts\thumbnails\*_v9_thumbnail.jpg`
- Mapowanie (częściowe): `C:\VSE\Shorts\thumbnails\mp4_mapping.json`
- YT titles: `C:\VSE\Shorts\thumbnails\yt_titles.json`

## Problem do rozwiązania: Mapowanie video_id → MP4

### Root cause
W folderze `C:\VSE\Shorts\Jurek 2 Wołyn 18.07.2026_YouTube_2026-08-24\` jest 50+ MP4.  
Nie mają tagów title w metadata (ffprobe zwraca puste).  
Fuzzy match po nazwach pliku — błędny, tylko 5/23 pewnych.  

### Prawidłowe podejście: mapowanie po sesji nagraniowej

23 shorty pochodzą z **3 sesji nagraniowych**. Dla każdej sesji — ten sam zestaw MP4.

| Sesja | video_ids | MP4 wzorzec (glob) |
|---|---|---|
| Wiedeń/Pomnik/Antifa | `kqby7mJZhuA`, `GLRHMx-A-lE`, `VpOQRrHWR0Q`, `DuWGHfRmkXA`, `etW9qE9O2LQ`, `jT4xLEC-_fw`, `MplQERzDdQk`, `hde4weDkpJU`, `ZpfLMoEcHJU`, `0Q5EzAHn9i4` | `*Antify*`, `*pomnik*`, `*Kalenberg*`, `*Wiedniu*`, `*Odsiecz*`, `*Mlodzie*`, `*Mniejszosc*` |
| Dieta/Nowacka | `Ud39NRwg6bc`, `9Tkv8ue2l-0`, `wpijwznWNbQ`, `9Djd9bAalQg`, `tAvFCPB5edo`, `NSgYkAqMSWU`, `otu-Wl0hSAk`, `pnBGXd3-fpQ`, `Ub6IU_qzzSA`, `8U31DNanCxM` | `P*u*anski*Lisiecki*dieta*`, `*Dieta*`, `*Nowacka*`, `*weganska*`, `*liwka*`, `*drobiarskiej*` |
| Reprywatyzacja | `vykiY72rCLE`, `fdNWzWOrI94`, `7PnGnQeZGow` | `Klimczak*Schrimer*`, `Komisja*`, `*Kobiecie*`, `*Odzyska*` |

### Następne kroki dla nowego agenta
1. Dla każdej sesji: wybierz 1-2 reprezentatywne MP4 (najlepszy kadr z osobami)
2. Wyciągnij klatkę z t=5s (nie t=3s — SubMachine intro)
3. Wygeneruj thumbnails v9 dla każdej grupy z tym samym tłem
4. Dla Wiedeń-grupy: MP4 `Prawie_50_aktywistow_Antify...` lub `Gotowy_pomnik_Jana_III...`
5. Dla Dieta-grupy: MP4 `P*u*anski Lisiecki dieta platentarna*`
6. Dla Reprywatyzacja-grupy: `Klimczak*Schrimer*` lub `Komisja_weryfikacyjna*`

## Czyszczenie @naszkanal

- Skrypt gotowy: `/app/clean_descriptions.py` w kontenerze `vse-api` na VPS
- Quota wyczerpana (prawdopodobnie 15.09)
- Uruchom po resecie: `ssh ... "docker exec -w /app vse-api python3 /app/clean_descriptions.py 2>&1"`
- Reset quota: 09:00 CEST codziennie

## Infrastruktura
- VPS: `ubuntu@147.224.162.100`, klucz: `C:\Users\tomas2\.ssh\oracle-crimson.key`
- VSE API: `https://vse.impresjapr.pl`
- Branding kit: `D:\Biblioteki\prawy video\!_shortsy identyfikacja 9x16\prawy-shorts-kit\`
- Font: `NimbusSansNarrow-Bold.otf` w branding kicie