# Publication Flow — Kurier365 / BiznesCiti

## Flow standardowy
```
Kandydat wpływa (feed-crawler / Gmail)
    ↓
[Sheets: Status = nowy] — automatyczne
    ↓ [Redaktor zmienia na: zatwierdzony]
PressAI generate (Claude Sonnet, min 600 słów, SEO title z frazą)
    ↓
Artykul CZEKA w historii PressAI (nie publikowany)
    ↓ [Redaktor: dodaje obrazki w PressAI UI]
    ↓ [Redaktor: zatwierdza zmiany]
Publikacja -> WP draft
    ↓ [Redaktor: 1 klik -> WP live]
```

## Wyjątki (auto-draft od razu, maja wlasne ilustracje)
- Gmail od: Zabka biuro prasowe, Juchniewicz, Rudzinski
- Flow: generate -> WP draft automatycznie (nie czeka na obrazki)

## Prompty obrazów
- 2 propozycje AI promptów w Sheets (kolumny S, T)
- Generator: Midjourney / DALL-E / Flux (do implementacji: modul generatora)
- Infografiki automatyczne: zaplanowane w Fazie 4

## Routing portalu
- Gmail współpracownicy: Kurier365
- Nauka / Geostrategia: Kurier365
- Biznes / Gospodarka / Finanse: BiznesCiti
- Oba: na podstawie sekcji kandydata
