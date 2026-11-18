# Uruchomienie i wdrożenie

## Zmienne środowiskowe (`.env` w katalogu głównym)

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `DJANGO_DEBUG` | `true` | Na produkcji `false` |
| `DJANGO_SECRET_KEY` | dev-klucz | Wymagany przy `DEBUG=false` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Domeny backendu |
| `DATABASE_URL` | `application/sqlite3.db` | np. `postgres://user:pass@host:5432/usterka` |
| `MEDIA_ROOT` | `application/media` | Katalog plików (plany, zdjęcia, raporty) |
| `FRONTEND_ORIGINS` | `http://localhost:5173,…` | CORS / CSRF |
| `AUTH_DEV_LOGIN` | `=DEBUG` | Logowanie e-mailem; blokowane przy `DEBUG=false` |
| `ENTRA_*` | – | Patrz [05-konfiguracja-microsoft.md](05-konfiguracja-microsoft.md) |

Frontend: `usterka_frontend/.env.local` → `VITE_API_BASE_URL=https://api.twoja-domena.pl/api/`.

## PostgreSQL lokalnie

1. `docker compose up -d`
2. W `.env`: `DATABASE_URL=postgres://usterka:usterka@localhost:5432/usterka`
3. `.venv/Scripts/python application/manage.py migrate`

## Wdrożenie (minimum)

1. Backend: `gunicorn config.wsgi` za reverse proxy z HTTPS (Azure App Service / Railway / Render).
2. `python manage.py migrate` i `collectstatic` przy każdym wdrożeniu.
3. Trwały dysk na `MEDIA_ROOT` (albo Azure Blob – do zrobienia przez `django-storages`).
4. Frontend: `npm run build` → katalog `dist/` na hosting statyczny (Azure Static Web Apps / Netlify). Ustaw przekierowanie wszystkich ścieżek na `index.html`.
5. Dodaj adres produkcyjny frontendu: do `FRONTEND_ORIGINS` i do Redirect URI w Entra ID.
6. `AUTH_DEV_LOGIN=0`, `DJANGO_DEBUG=false`.
