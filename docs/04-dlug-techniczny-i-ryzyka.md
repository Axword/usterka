# 04. Dług techniczny i ryzyka

## 1. Naprawić od razu (w obecnym pliku)

| # | Problem | Gdzie | Skutek | Poprawka |
|---|---|---|---|---|
| 1 | Martwy kod `act==='logo-unused'` z `const f=null` | `openProjectForm` | Nic nie robi, myli przy czytaniu | Usunąć gałąź |
| 2 | Biblioteki z CDN bez cache offline | `LIB`, `loadScript` | Bez zasięgu: nie da się dodać planu z PDF ani zrobić raportu | Service Worker lub wbudowanie bibliotek lokalnie |
| 3 | Brak SRI (`integrity`) przy skryptach z CDN | `loadScript` | Podmieniony skrypt na CDN ma dostęp do wszystkich danych | Dodać `integrity` + `crossorigin` lub hostować lokalnie |
| 4 | Logowanie demo wygląda jak prawdziwe | `AUTH`, `renderLogin` | Ktoś może uznać, że dane są chronione | Jest baner „Tryb demonstracyjny” – zostawić, dopóki nie ma MSAL |
| 5 | Kopia zapasowa = cały JSON z base64 w pamięci | `exportBackup` | Przy 500 zdjęciach × 300 KB ≈ 200 MB → crash na telefonie | Eksport do ZIP strumieniowo (np. `fflate`/`client-zip`) |
| 6 | Import kopii bez walidacji struktury | `importBackup` | Uszkodzony plik może zapisać śmieci | Sprawdzić wersję i wymagane pola przed zapisem |
| 7 | Usuwanie w pętli sekwencyjnie, każda operacja = osobna transakcja | `deleteProject`, `planMenu` | Wolne przy dużych projektach, niespójność przy przerwaniu | Jedna transakcja na wiele store’ów |
| 8 | Tylko jeden szkic (`meta/draft`) | `openDefectForm` | Otwarcie drugiej usterki nadpisuje szkic pierwszej | Klucz szkicu per usterka |

## 2. Ograniczenia architektury prototypu

1. **Jeden plik 170 KB** – brak modułów, testów, typów. Dalszy rozwój = rosnące ryzyko regresji.
2. **Brak schematu migracji** – `onupgradeneeded` tylko tworzy store’y. Zmiana struktury rekordów wymaga ręcznej migracji.
3. **Dane tylko na jednym urządzeniu** – zgubiony/zresetowany telefon = utrata protokołów (jeśli nie było kopii).
4. **Numeracja `nextNo` lokalna** – blokuje pracę wielu osób (patrz 02, sekcja 5).
5. **Status = „ma zdjęcie po”** – nie ma etapu weryfikacji przez inspektora.
6. **Raport generowany w pamięci telefonu** – przy dużych projektach ryzyko braku pamięci (szczególnie iOS Safari, limit ~1–2 GB na kartę).
7. **Plany jako rastrowy JPEG** (maks. 13 MPx) – na dużych arkuszach A0 małe opisy mogą być nieczytelne przy zoomie.

## 3. Ryzyka produktowe

| Ryzyko | Prawdopodobieństwo | Wpływ | Jak ograniczyć |
|---|---|---|---|
| iOS Safari czyści IndexedDB po 7 dniach nieużywania (gdy nie zainstalowano PWA) | Średnie | Wysoki | Instalacja PWA na ekranie głównym + `storage.persist()` + sync z chmurą |
| Konflikty synchronizacji | Wysokie przy zespołach | Średni | Blokada przeglądu, LWW per pole, historia zmian |
| Rozmiar zdjęć i transfer na budowie (LTE) | Wysokie | Średni | Kompresja na urządzeniu (jest: 1600 px, JPEG 0.82), upload w tle, wznawianie |
| Wymagania formalne protokołu (prawo budowlane, umowy) | Średnie | Wysoki | Konsultacja z 2–3 inspektorami nadzoru, konfigurowalne szablony |
| Zgoda działu IT klienta na aplikację w Entra ID | Średnie | Wysoki | Minimalne uprawnienia (`Sites.Selected`), dokumentacja bezpieczeństwa, hosting w UE |
| Konkurencja z dużym budżetem | Wysokie | Średni | Nisza: polski rynek, M365, prostota, cena |

## 4. Co jest dobrze i warto zachować

- Współrzędne pinezek **znormalizowane (0..1)** – niezależne od rozdzielczości, gotowe pod wersje planów.
- Escapowanie HTML (`esc()`) wszędzie przy wstawianiu danych → brak oczywistego XSS.
- Autosave szkicu i odzyskiwanie po zamknięciu karty.
- Kompresja zdjęć przed zapisem.
- Ten sam układ raportu w PDF i DOCX, DOCX do edycji.
- Dostępność: `aria-*`, `focus-visible`, `prefers-reduced-motion`, duże przyciski (min. 44–46 px) pod rękawice.
- Ciemny motyw, `safe-area-inset` dla iPhone’ów z notchem.
