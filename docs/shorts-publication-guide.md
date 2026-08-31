# Przewodnik Publikacji Shortsów — dla Zarządzających

> Wersja: 1.0 | 2026-08-31  
> 谊尊地: na podstawie analizy algorytmu YouTube Shorts 2025/2026

Ten dokument opisuje jak poprawnie publikować Shorty na YouTube korzystając z outputów Short Machine. Short Machine generuje gotowy kontent — Twoim zadaniem jest wiedzieć jak go użyć.

---

## Co dostajesz z Short Machine

Dla każdego Shorta Short Machine generuje:

| Pole | Co to | Gdzie trafia |
|------|-------|-------------|
| `optimized_title` | Tytuł Shorta, max 45 znaków | YouTube: pole Title |
| `description` | Opis z CTA i hashtagami | YouTube: pole Description |
| `hashtags` | 3–5 hashtagów | Załączone w `description` |
| `pinned_comment` | Pytanie + CTA do powiązanego filmu | Publikujesz ręcznie jako pierwszy komentarz i przypinasz |
| `related_video_id` | ID długiego odcinka, z którego pochodzi Short | YouTube Studio: Powiązany film |

---

## Zasady które MUSISZ znać

### 1. Linki w opisach i komentarzach NIE DZIAŁAJĄ

Od 31.08.2023 YouTube wyłączył klikalnosc URLów w Shortach (opis + komentarze). Wklejony link wygląda jak zwykły tekst — użytkownik nie może go kliknąć.

**Co robimy zamiast linków:**
- Nie wklejaj URLa do opisu ani komentarza
- Zamiast tego: w YouTube Studio ustaw **Powiązany film** (`related_video_id` z outputu Short Machine)
- W przypiętym komentarzu piszemy: *„całą rozmowę znajdziesz w powiązanym filmie poniżej”*

### 2. `#Shorts` w tytule — NIE dodawaj

YouTube od 2024 automatycznie klasyfikuje materiał jako Short po proporcjach (9:16) i czasie trwania (≤60s). Dodawanie `#Shorts` w tytule:
- Marnuje 8 cennych znaków z ~40 widocznych na telefonie
- Wygląda jak spam i obniża CTR

Short Machine **nie generuje** `#Shorts` w tytule — jeśli zobaczysz to w starym kontencie, popraw.

### 3. Tytuł — co jest widoczne na telefonie

Na smartfonie widoczne jest **40–50 znaków** tytułu (reszta ucina się wielokropkiem). Short Machine generuje tytuły w tym limicie. Nie edytuj tytułu bez potrzeby — jeśli musisz, nie przekraczaj 45 znaków.

### 4. Hashtagi — limit 15

YouTube: jeśli Short ma **więcej niż 15 hashtagów**, algorytm ignoruje WSZYSTKIE. Short Machine generuje 3–5. Nie dodawaj ręcznie więcej.

### 5. Przypięty komentarz — dlaczego to ważne

Gdy widz otwiera komentarze (bo widzi pytanie w przypiętym), Short kontynuuje odtwarzanie w tle. To podnosi wskaźnik *Average Percentage Viewed* (APV) powyżej 100%, co jest jednym z najsilniejszych sygnałów rankingowych.

**Jak to zrobić:**
1. Opublikuj Short
2. Sam skomentuj (z konta kanału) treścią z pola `pinned_comment`
3. Przypiń ten komentarz (3 kropki → Przypiń)

---

## Checklist publikacji — krok po kroku

```
[ ] 1. Wgraj plik _gotowy.mp4 na YouTube
[ ] 2. Wklej optimized_title — NIE edytuj, max 45 zn
[ ] 3. Wklej description (zawiera hashtagi)
[ ] 4. YouTube Studio > Powiązany film > wklej related_video_id
[ ] 5. Ustaw harmonogram (slots: 07:00 / 12:00 / 18:00 / 21:00 CEST)
[ ] 6. Opublikuj
[ ] 7. Skomentuj treścią pinned_comment i PRZYPNIJ komentarz
[ ] 8. Zaznacz Short jako opublikowany w shorts_schedule.json
```

---

## Przykładowy output Short Machine

```json
{
  "optimized_title": "Mocne słowa o podatkach! Zapłacimy więcej?",
  "description": "Gorąca dyskusja w Studio Prawy_PL o nowych regulacjach podatkowych i ich skutkach dla Polaków.\n\n🔔 Subskrybuj @StudioPrawy_PL!\n\n#PrawyPL #Podatki #Gospodarka #Polska #Wiadomości",
  "hashtags": ["#PrawyPL", "#Podatki", "#Gospodarka", "#Polska", "#Wiadomości"],
  "pinned_comment": "💬 Czy Twoim zdaniem nowe regulacje uderzą w Twój portel? Napisz poniżej! 👇\n\n🎥 Całą rozmowę znajdziesz w powiązanym filmie!",
  "related_video_id": "xyz789longId"
}
```

---

## Częste błędy

| Błąd | Efekt | Poprawka |
|-------|-------|----------|
| Wklejenie URL do komentarza | Martwy tekst, widz nie kliknie | Użyj Powiązanego Filmu |
| Dodanie `#Shorts` do tytułu | Utrata ~8 zn widocznego tekstu, spam feel | Usuń |
| Edycja tytułu powyżej 45 zn | Ucina się na mobile, utrata hooka | Max 45 zn |
| Dodanie >15 hashtagów | YouTube ignoruje wszystkie | Max 5 |
| Brak przypiętego komentarza | Utrata loopa retencji | Zawsze przypnij |

---

*Analiza: vse-analyst-01 | youtube-seo | 2026-08-31*  
*Dokument: vse-strateg-01 | media-dispatch | 2026-08-31*