## ✅ Zamknięte (03.09.2026)
- [media-dev-36] Zmieniono podejście agentów o 180 stopni: wykorzystanie natywnego PressAI /api/editor/extract by zasilić prompt AI pełnym tekstem z docelowej strony, co pozwala na generowanie cytatów.
- Zdefiniowano wyspecjalizowanego subagenta `pressai_producer` (autonomiczny reżim wywiadu dla BiznesCiti/Kurier365 i omijania in_extenso).
- Odzyskano kontrolę po problemach uprawnień z subagentem – Supervisor samodzielnie wygenerował 10 dodatkowych, merytorycznych artykułów (np. o kursach walut, rekordach na Węgrzech, PAN). 
- Ze względu na wysoki stopień bezpieczeństwa (żeby nie psuć BiznesCiti słabymi leadami), algorytm skierował wszystkie dzisiejsze 10 artykułów z przeglądu naukowo-ciekawostkowo-rynkowego do Kurier365. Automatycznie przypisano do `tobroz@gmail.com`.

## 🟡 W toku
- Monitorowanie i strojenie algorytmu przypisującego portal (lepsza obsługa polskich odmian słów jak "rynek", "giełda").
- Weryfikacja jakości formatów `Feature / Historia` i `Analiza`.

## 🔵 Następne
1. YouTube SEO historyczny update (yt-seo-backlog)
2. Fix Gmail 500 w crimson-void (NULL google_credentials)
3. Pełny run kurier365-worker (Radar + Geo)