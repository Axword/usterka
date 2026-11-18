# 03. Roadmapa: od prototypu do produktu

Szacunki dla **1–2 developerów** (full-stack, React + Django). Tydzień = ~35 h pracy.

## Etap 0 – Porządki w prototypie (1 tydzień)

Cel: obecna wersja nadaje się do pokazywania klientom i testów w terenie.

1. Naprawić błędy z [04-dlug-techniczny-i-ryzyka.md](04-dlug-techniczny-i-ryzyka.md), sekcja „Naprawić od razu”.
2. Dodać `manifest.json` + prosty Service Worker cache’ujący HTML i 3 biblioteki z CDN → raport działa offline.
3. Hosting statyczny (GitHub Pages / Netlify / Azure Static Web Apps) pod własną domeną z HTTPS.
4. Przetestować na 3 urządzeniach: iPhone (Safari), Android (Chrome), laptop. Test: 1 inwestycja, 3 plany, 50 usterek, 150 zdjęć, raport PDF i DOCX.
5. Zmierzyć: czas generowania raportu, rozmiar pliku, zużycie pamięci.

**Wynik:** działająca PWA, instalowalna na ekranie telefonu, dane dalej tylko lokalnie.

## Etap 1 – Walidacja z użytkownikami (2–4 tygodnie, równolegle z etapem 2)

1. Znaleźć 3–5 inspektorów / kierowników budowy, którzy przetestują na prawdziwych odbiorach.
2. Po każdym odbiorze 15 min rozmowy. Pytania:
   1. Ile trwał odbiór i przygotowanie protokołu przed / po?
   2. Czego brakowało w raporcie?
   3. Kto jeszcze musi zobaczyć usterki (wykonawca, inwestor, podwykonawcy)?
   4. Ile zapłaciłbyś miesięcznie?
3. Spisać 10 najczęstszych próśb, posortować wg częstości.

**Wynik:** lista priorytetów oparta na danych, nie na domysłach.

## Etap 2 – Fundament: frontend w TS + backend (6–8 tygodni)

| Tydz. | Zadania |
|---|---|
| 1 | Repo (monorepo: `frontend/`, `backend/`), Vite + React + TS, Django + DRF, Docker Compose (Postgres, Redis), CI (lint + testy) |
| 2 | Przeniesienie modułów bez UI: `images.ts`, `db.ts` (Dexie + migracja ze starej bazy `usterki-na-planie`), `reports/pdf`, `reports/docx` |
| 3 | Ekrany: lista inwestycji, inwestycja, formularz inwestycji |
| 4 | Dodawanie planu (PDF/JPG), przeglądarka planu z gestami |
| 5 | Formularz usterki, zdjęcia, autosave szkicu |
| 6 | Backend: modele, API, Entra ID (MSAL + walidacja JWT), presigned upload |
| 7 | Silnik synchronizacji (outbox, `/api/sync`), upload zdjęć w tle |
| 8 | Testy E2E (Playwright) najważniejszych ścieżek, poprawki, wdrożenie na staging |

**Wynik:** te same funkcje co prototyp, ale dane w chmurze, logowanie firmowe, wiele urządzeń.

**Ważne:** import starej kopii JSON (`app: 'usterki-na-planie', version: 1`) musi działać – to migracja danych pierwszych użytkowników.

## Etap 3 – Funkcje, za które klient płaci (6–10 tygodni)

Kolejność do potwierdzenia w etapie 1. Proponowana:

1. **Status z weryfikacją** (2 tyg.): `otwarta → w trakcie → zgłoszona do odbioru → usunięta / odrzucona`. Historia zmian.
2. **Odpowiedzialna firma + portal wykonawcy** (2–3 tyg.): link bez logowania, podwykonawca widzi swoje usterki, dodaje zdjęcie „po” i komentarz.
3. **SharePoint przez Graph** (1 tydz.): automatyczny zapis raportu, upload sesyjny dla dużych plików.
4. **Powiadomienia e-mail** (1 tydz.): nowa usterka dla firmy, zbliżający się termin, usterka zgłoszona do odbioru.
5. **Raport serwerowy + szablony firmowe** (2 tyg.): DOCX-szablon z logo i układem klienta.
6. **Filtrowanie i wyszukiwanie** (1 tydz.): po typie, firmie, statusie, planie, terminie, przeterminowane.
7. **Wersje planów** (1 tydz.): podmiana rysunku z zachowaniem pinezek.

## Etap 4 – SaaS (4–6 tygodni)

1. Multi-tenant: rejestracja organizacji, zaproszenia, role (`admin`, `inspektor`, `podgląd`).
2. Płatności: Stripe (subskrypcje, faktury VAT – sprawdzić integrację z polskim systemem faktur / KSeF).
3. Limity planu: liczba aktywnych inwestycji, użytkowników, GB zdjęć.
4. Panel admina, logi, monitoring (Sentry + metryki).
5. Regulamin, polityka prywatności, DPA (RODO).
6. Landing page + demo.

## Etap 5 – Później (wg popytu)

- Aplikacja natywna (Capacitor na bazie PWA) – lepszy aparat, push, praca w tle.
- Adnotacje na zdjęciach (strzałki, okręgi).
- Dyktowanie opisu (speech-to-text).
- AI: podpowiedź typu i opisu usterki ze zdjęcia.
- Eksport do Excel/CSV, integracje (Procore, Autodesk Construction Cloud).
- Checklisty odbiorowe (szablony wg branży).
- Wielojęzyczność (EN, UA – częste ekipy na budowach).

## Model biznesowy – punkty do decyzji

| Pytanie | Opcje |
|---|---|
| Kto płaci? | Generalny wykonawca / firma inspektorska / inwestor-deweloper |
| Za co? | Per użytkownik (inspektor), per aktywna inwestycja, per firma ryczałt |
| Kto korzysta za darmo? | Podwykonawcy przez portal (to napędza rozprzestrzenianie się produktu) |
| Rynek | Polska na start (język, format protokołu), potem CEE |

Konkurencja do przeanalizowania przed ustaleniem ceny: PlanRadar, Fieldwire, Archisnap, Snagmaster, LetsBuild. Wyróżnik do rozważenia: **polski format protokołu odbioru + natywna integracja z M365/SharePoint + działanie offline**.

## Kamienie milowe – podsumowanie

| # | Kamień | Ok. czasu od startu |
|---|---|---|
| 1 | PWA prototypu u testerów | 1 tydz. |
| 2 | Wersja chmurowa (multi-device, Entra ID) | 9 tydz. |
| 3 | Portal wykonawcy + SharePoint + statusy | 17 tydz. |
| 4 | Płatna wersja SaaS | 23 tydz. |
