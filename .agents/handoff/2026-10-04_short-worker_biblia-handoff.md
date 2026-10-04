# HANDOFF — short-worker / biblia-worker | media-dispatch | 04.10.2026 19:00

> Zapisany LOKALNIE w workspace, bo GitHub MCP zwraca `Authentication Failed: Bad credentials` (od ok. 18:57).
> Po odnowieniu tokenu GitHub: wypchnij ten plik do `media-dispatch/.agents/handoff/` + dual-write kopii do `sonic-void/.agents/reports/inbox/`.

## 0. KROK 1 DLA NASTEPNEGO (obowiazkowy, przed jakakolwiek praca)
Porownaj **sformalizowanego biblia-workera** z tym, co wypracowano w tej sesji. Wynik: tabela `Element | Formalnie | Wypracowane tutaj | Luka / do dopisania`. Bez wdrazania — raport + decyzja usera.

Sformalizowany biblia-worker (znaleziony w workspace):
- `agents/biblia-worker/` — katalog workera (zawartosc nie zostala przeze mnie przejrzana; user odrzucil komende listujaca, patrz sekcja 6)
- `.agents/reports/2026-09-06_media-dev-30_biblia-worker.md`
- `.agents/reports/inbox/2026-09-16_sup01_biblia-pipeline-postmortem.md`
- `agents/vse-worker/scripts/biblia_backlog_pipeline.py`, `biblia_full_pipeline.py`, `biblia_schedule_pipeline.py`
- `.agents/knowledge/vse-worker-constitution.md` (lokalnie ostatnia zmiana 18.09 — klon NIEAKTUALNY; na GitHubu sa sekcje 16 [commit f7e56d2] i ewentualnie 17)
- UWAGA: `.agents/knowledge/` ma konstytucje tylko dla: editorial, transcribe, vse. **Brak osobnej konstytucji biblia-workera.** User chce konstytucje dla KAZDEGO sformalizowanego workera w workspace (nie tylko w repo) — do zaproponowania.

## 1. BRAIN DO PRZESKANOWANIA (ta sesja i subagenci)
Bazowa sciezka: `C:\Users\tomas2\.gemini\antigravity\brain\<id>\.system_generated\logs\transcript.jsonl` (najpierw compact, przy `truncated_fields` -> `transcript_full.jsonl`).
| Kto | conversation id |
|---|---|
| Sesja glowna (short-worker) | `9d26edcb-9160-41fa-be65-55baa7e5717b` |
| Worker biblia 20.09 (pipeline 13 filmow) | `060a6315-3934-42f2-bd08-24c211182d09` |
| Worker cleanup 20.09 (duplikaty + konstytucja s.16) | `829ceb55-2c10-463f-9ccf-906552e12c15` |
| Worker shorts 20.09 | `6682f62e-ff6a-43e5-94b5-83c33a4a3b3d` |
| Worker crontab pinned comments | `387dadd0-53f6-41b0-b00a-2c8ae4825d7d` |
| Analityk procesu 04.10 (raport usprawnien) | `de266e24-b86f-4877-9a61-a5edc988f70d` |
| Worker lookup 11 ID | `558f1464-780d-41f4-b5c3-0057784ae0c4` |
| **Worker biblia 04.10 (pipeline 7 filmow)** | `94950384-73eb-41d7-a99a-9aa8f8002dbd` |
| Worker rozbudowy o 3 kroki (przerwany, nic nie zapisal) | `f4587789-d3d5-43c0-8032-b3322ba17d36` |

## 2. STAN NA 04.10.2026
**ZROBIONE (potwierdzone logiem + user zweryfikowal na YT/WP):**
- Czytania 04–10.10 (7 filmow) na YT + prawy.pl: 04.10 `h2ncQhExDw4` publish-now; 05.10 `JTapGa_m6uc`; 06.10 `UU3QEIA6CBU`; 07.10 `h97hhEe_Dcw`; 08.10 `uirUFoX863w`; 09.10 `CQTjzmnFbHA` (WP #127502); 10.10 `ek0VxaoEIME` (WP #127507). 00:00+02:00, WP `future`, playlista Prawy Biblijny.
- Kategoria Biblia dodana przez usera zbiorczo (recznie).
- Wrzesien: 13 filmow 21.09–03.10 zaplanowane; duplikaty usuniete; sekcja 16 konstytucji.

**NIE ZROBIONE / OTWARTE:**
1. 3 brakujace kroki w pipeline (user: "zawsze brakuje"): WP kategoria **Biblia** (merge, nie nadpisywac), YT `status.embeddable=true`, `snippet.defaultLanguage=pl` + `defaultAudioLanguage=pl`. Lokalny `tmp\biblia_schedule_pipeline.py` (27464 B, 17:49) NIE zawiera ich. Do wdrozenia W ISTNIEJACYM skrypcie (jeden plik, bez nowych).
2. Bug konca skryptu: `print(json.dumps({{'status': 'err_{resp.status_code}'}}))` -> `NameError`, nie powstaje `oct_pipeline_results.json`. Stan naprawy w pliku lokalnym niepotwierdzony.
3. Pytanie do usera: czy dopatchowac 7 filmow (embeddable + jezyk PL przez API)? — bez odpowiedzi.
4. Duplikat `OsNlnRD0fKk` (10.10) — NIE usuniety, bez decyzji usera (usuwanie nieodwracalne).
5. Shorty `mPzouaKGFr4`, `XS7u6-wmpBo` — PORZUCONE na polecenie usera (404 na kanalach konta tobroz@gmail.com).
6. Sekcja 17 konstytucji (kroki obowiazkowe) — nie zapisana.
7. Analiza usprawnien (P0/P1/P2) — raport przyjety, wdrozenia czekaja na decyzje usera: fail-fast na 4xx, guard na „brak transkryptu" w 200 (w `retry_2_shorts.py` jest, w `prawy_shorts_full_schedule.py` nie), pre-flight tokenow, trwaly stan zamiast `/tmp`, retry pinned comments.

## 3. BLOKERY
- **GitHub MCP: Bad credentials** — zadnych zapisow do repo, dopoki user nie odnowi tokenu.
- OAuth: `VeriNarrMundo`, `Tomasz Brzozowski` -> `invalid_grant`. Uzywane: konto **tobroz@gmail.com** (`Prawy TV`, `Studio Prawy_PL`). Dla filmow biblijnych dziala przez `Prawy TV` (Studio Prawy_PL daje 403/400 i skrypt przechodzi dalej).
- Crony pinned comments (VPS, `0 20 21-26 9 *`) dotycza shortow 21–26.09 — historyczne.

## 4. LEKCJE (do konstytucji)
- `/v1/shorts/describe` WYMAGA `start_sec` i `end_sec`; 422 -> fail-fast, nie retry.
- HTTP 200 z tytulem „Brak transkryptu…" to NIE sukces — nie zapisywac na YT.
- Worker nie buduje nowych skryptow: istniejacy `biblia_schedule_pipeline.py` + podmiana `VIDEOS[]`. Dispatch: jeden samowystarczalny skrypt, max 1 poprawka, potem raport Failed.
- Cost-tier: supervisor nie robi serii `run_command`; unikaj heredoc przez SSH (write_to_file -> scp -> ssh bash).
- Python w tle buforuje stdout -> pusty log nie znaczy awarii; sprawdzaj proces i API.
- `subprocess`: `capture_output=True` + `decode('utf-8', errors='replace')`, nie `text=True`.
- Publikacja tylko na wyrazne polecenie usera (AGENTS.md). Dzis: tylko `h2ncQhExDw4` na wyrazne zlecenie.

## 5. KONFIGURACJA (nie szukac na nowo)
- VPS `ubuntu@147.224.162.100`, klucz `C:\Users\tomas2\.ssh\oracle-crimson.key`; VSE `:8085`; portal prawy.pl `2b047d7d-15a1-4d2f-8463-f89c2275bb73`; playlista `PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7`; LLM `claude`.
- AME log: `C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt` (UTF-16LE).
- MP4: `C:\Users\tomas2\Videos\Prawy\Biblia 04-10.10.2026\` (worker potwierdzil 7 plikow).
- Tytuly plikow w nowej partii: `YYYY-MM-DD_lk-X-Y-Z_opis_dzien` — zrodlo prawdy to tytul na YT (tabela z lookup), nie log.

## 6. UWAGA PROCESOWA
User odrzucil moja komende listujaca `agents/biblia-worker/` i wskazal: konstytucja ma byc **w workspace**, dla wszystkich sformalizowanych workerow — nie tylko w repo. Nastepny: zacznij od przegladu workspace (nie GitHuba) i zaproponuj spis konstytucji per worker.

## 7. WIADOMOSC DO NASTEPNEGO
Pracuj jednym samowystarczalnym skryptem, tanimi workerami, raportuj krotko. Nic nie wdrazaj bez decyzji usera (analiza -> raport -> decyzja -> wdrozenie). Vitals poprzednika: V1 55🔴, V6 🔴 (kontekst skrocony) — stad handoff.
