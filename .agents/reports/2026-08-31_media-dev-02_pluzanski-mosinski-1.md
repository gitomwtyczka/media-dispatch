# Raport: Publikacja VSE — Płużański Mosiński 1

**Data:** 2026-08-31  
**Autor:** `media-dev-02`  
**Status:** ✅ Sukces (WP + YT)

---

## 1. Szczegóły publikacji

| Element | Wartość |
|---------|---------|
| **YouTube ID** | `s6aGNXdtKpA` |
| **YouTube URL** | https://www.youtube.com/watch?v=s6aGNXdtKpA |
| **Tytuł SEO** | *Porozumienia sierpniowe 1980 – Jan Mosiński o narodzinach Solidarności* |
| **Portal** | prawy.pl |
| **WP Post ID** | `125353` |
| **WP Post URL** | https://prawy.pl/porozumienia-sierpniowe-1980-jan-mosinski-o-narodzinach-solidarnosci/ |
| **Status wpisu WP** | `publish` |
| **Kanał YouTube** | Studio Prawy_PL (`UCoH2G9By4OX3kcLsc8lHgDw`) |
| **Status YouTube** | `public` (zaktualizowano z `unlisted`, zaktualizowany tytuł i opis SEO) |

---

## 2. Przebieg operacji

1. **Autoryzacja VSE:** Wygenerowano token JWT przez SSH z kontenera `vse-api`.
2. **Pobranie tokenów YT:** Pobrano aktywny token OAuth dla kanału `Studio Prawy_PL` bezpośrednio z bazy VSE (`_build_credentials`).
3. **Generowanie VSE (`POST /v1/generate`):**
   - Parametry: `publication_type=full_analysis`, `portal_id=2b047d7d-15a1-4d2f-8463-f89c2275bb73`, `llm_provider=claude`, `lang=pl`.
   - Wynik: 200 OK — wygenerowano pełną strukturę VideoObject schema, treść artykułu oraz opis SEO.
4. **Wstrzyknięcie do WordPress (`POST /v1/inject`):**
   - Utworzono post WP #125353 na prawy.pl z formatem video i opublikowano natychmiast (`status=publish`).
5. **Aktualizacja YouTube:**
   - Zaktualizowano tytuł, opis SEO i zmieniono widoczność na `public`.
