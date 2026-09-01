# YT SEO Backlog — Studio Prawy_PL

> Wygenerowano: 01.09.2026 | media-dev worker

## Status
Rekonesans: 100 filmów z kanału Studio Prawy_PL

## Statystyki (kryterium: opis >200 zn LUB tagi >=3)
- Public: 80
- Unlisted: 11  
- Private: 9
- SEO OK: 77
- Do poprawy: 23

## Pełne dane
/tmp/yt_results.json na VPS (147.224.162.100)

## Zadanie dla następnego workera
- Przejrzeć wszystkie public filmy ze słabym SEO
- Zaproponować priorytety do update
- Uruchomić prawy-youtube-worker --update-seo dla top 20

## Uwaga kalibracja
Poprawne kryterium SEO:
- opis_ok = len(description) > 200
- hashtagi_ok = count(#hashtag w opisie) >= 3
- seo_ok = opis_ok AND (tagi_backendowe >= 5 OR hashtagi_ok)
