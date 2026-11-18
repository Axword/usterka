# Usterki na planie

Aplikacja do odbiorów technicznych: plan (PDF/JPG) → pinezki z usterkami → zdjęcia przed/po → protokół PDF/Word → kopia w SharePoint.

- **Backend:** Django 5 + Django Ninja (`application/`)
- **Frontend:** React 19 + TypeScript + Vite + Zustand (`usterka_frontend/`)
- **Baza:** SQLite lokalnie, PostgreSQL na produkcji (`docker-compose.yml`)
- **Logowanie:** konto Microsoft każdej osoby (Entra ID). Lokalnie: logowanie samym e-mailem.
- **SharePoint:** raport zapisywany kontem zalogowanej osoby (On-Behalf-Of + Microsoft Graph).

Układ repozytorium wzorowany na `lol_spy`.

## Uruchomienie: Docker (najprościej)

1. Uruchom Docker Desktop.
2. W folderze projektu: `docker compose up --build` (albo dwuklik `URUCHOM.cmd`).
3. <http://localhost:5173/> – zaloguj się dowolnym e-mailem.

Stop: `docker compose down`. Dane (baza, zdjęcia) zostają w wolumenach.

## Uruchomienie lokalne bez Dockera (Windows)

1. Zainstaluj: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22.
2. `./scripts/install-local.ps1` – tworzy `.env`, `.venv`, instaluje zależności, migruje bazę.
3. `./scripts/start-local.ps1`
4. Otwórz <http://localhost:5173/>, zaloguj się dowolnym e-mailem (tryb dev).

Adresy: API + dokumentacja Swagger <http://127.0.0.1:8000/api/docs>, admin <http://127.0.0.1:8000/admin/> (konto: `.venv/Scripts/python application/manage.py createsuperuser`).

## Testy

```powershell
cd application; ../.venv/Scripts/python -m pytest -q; ../.venv/Scripts/ruff check .
cd ../usterka_frontend; npm run build
```

## Dokumentacja

| Plik | Zawartość |
|---|---|
| [docs/00-przewodnik-po-aplikacji.md](docs/00-przewodnik-po-aplikacji.md) | **Start tutaj:** ekrany ze screenshotami, logika, gdzie są dane |
| [docs/06-subskrypcje-stripe.md](docs/06-subskrypcje-stripe.md) | Logowanie hasłem, plany, Stripe (test i produkcja) |
| [docs/architecture.md](docs/architecture.md) | Moduły, model danych, przepływy, API |
| [docs/05-konfiguracja-microsoft.md](docs/05-konfiguracja-microsoft.md) | Rejestracja aplikacji w Entra ID, logowanie, SharePoint |
| [docs/running.md](docs/running.md) | Zmienne środowiskowe, PostgreSQL, wdrożenie |
| [docs/01-jak-to-dziala-teraz.md](docs/01-jak-to-dziala-teraz.md) – [04](docs/04-dlug-techniczny-i-ryzyka.md) | Analiza prototypu HTML i roadmapa (stan sprzed przepisania) |

Prototyp jednoplikowy: [legacy/usterki-na-planie.html](legacy/usterki-na-planie.html).
