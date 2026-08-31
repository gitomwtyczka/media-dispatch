# Raport VSE Pipeline — Wideo cDMAe_wx_AU

**Data:** 01.09.2026  
**Agent:** media-dev-15  
**Wideo:** https://www.youtube.com/watch?v=cDMAe_wx_AU (ID: `cDMAe_wx_AU`)  
**Tytuł roboczy:** Klimczak Płużański Wolińska  
**Portal:** prawy.pl (UUID: `2b047d7d-15a1-4d2f-8463-f89c2275bb73`)  

---

## 1. Dostępność napisów (Step 1)
- **Status:** ✅ Dostępne (transkrypcja pobrana pomyślnie z YouTube)
- **Czas trwania wideo:** 53 min 8 s (3188 s)
- **Transcript available:** `true`

---

## 2. Generowanie VSE (Steps 2-3)
- **JWT Auth:** Token wygenerowany pomyślnie dla konta `tobroz@gmail.com`
- **POST /v1/generate:** Status `200 OK` (czas procesowania: 293.86s, model: Claude)
- **Tytuł SEO:** `Helena Wolińska: bestia w mundurze i morderca gen. Nila | Prawy TV`
- **Tytuł artykułu:** `Helena Wolińska – stalinowska zbrodniarkatka generała Fieldorfa Nila`
- **Tytuł YT:** `Wolińska: Jak żydokomuna mordowała polskich bohaterów`
- **Meta description:** `Helena Wolińska – stalinowska prokuratorka odpowiedzialna za śmierć gen. Fieldorfa Nila. Tadeusz Płużański ujawnia kulisy ekstradycji i wybielania zbrodniarki.`
- **Główna fraza kluczowa:** `Helena Wolińska`
- **Struktura artykułu:**
  - 14 rozdziałów ze znacznikami czasowymi (anchor texts + time)
  - 8 pytań i odpowiedzi FAQ
  - 7 kluczowych cytatów (Tadeusz Płużański)
  - 2 opisy grafik archiwalnych z promptami

---

## 3. Shorts Candidates (Step 5)
- **Endpoint:** `POST /v1/shorts/candidates`
- **Status:** `200 OK`
- Wygenerowano segmenty do shortów o kluczowych momentach wywiadu (m.in. fałszywy wniosek o azyl w Wielkiej Brytanii, odmowa ekstradycji, postawa gen. Fieldorfa Nila, mitologizacja w filmie "Ida").

---

## 4. Status WP & Bezpieczeństwo
- **Polityka publikacji:** Zgodnie z wytycznymi materiał nie został opublikowany publicznie (post_status=draft, YT=unlisted).
- Kompletny obiekt `schema_data` przygotowany do osadzenia w WP.
