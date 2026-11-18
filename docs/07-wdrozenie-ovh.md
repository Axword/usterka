# Wdrożenie na VPS w OVH pod usterka.axword.pl

Aplikacja działa na **subdomenie** `usterka.axword.pl`. Główna domena `axword.pl` zostaje bez zmian.

## Jak to działa

```
Przeglądarka ──HTTPS──▶ Caddy (porty 80/443, certyfikat Let's Encrypt automatycznie)
                          ├── /            → pliki frontendu
                          ├── /api, /admin → backend (gunicorn)
                          └── /static      → pliki panelu admina
                       backend ──▶ PostgreSQL (wolumen pgdata) + pliki (wolumen media)
```

Wszystko to trzy kontenery z `deploy/docker-compose.prod.yml`. Frontend i API są pod jednym adresem, więc nie ma problemów z CORS.

## 1. DNS w OVH (zrobisz Ty)

Manager OVH → Domeny → `axword.pl` → **Strefa DNS** → Dodaj wpis:

| Typ | Subdomena | Cel |
|---|---|---|
| A | `usterka` | adres IPv4 Twojego VPS (z panelu OVH → VPS) |
| AAAA | `usterka` | adres IPv6 VPS (opcjonalnie; pomiń, jeśli nie używasz) |

TTL zostaw domyślny. Nie ruszaj istniejących wpisów `@` i `www`. Propagacja trwa od kilku minut do godziny. Sprawdzenie: `nslookup usterka.axword.pl` ma zwrócić adres VPS.

Ważne: bez poprawnego wpisu A Caddy nie pobierze certyfikatu HTTPS.

## 2. Przygotowanie VPS (jednorazowo)

Zaloguj się: `ssh <użytkownik>@<IP VPS>` (dla obrazów Ubuntu OVH to zwykle `ubuntu`).

```bash
# Docker + Compose
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER      # potem wyloguj się i zaloguj ponownie

# Zapora: tylko SSH i WWW
sudo ufw allow OpenSSH && sudo ufw allow 80,443/tcp && sudo ufw allow 443/udp && sudo ufw enable
```

Zalecane: logowanie do SSH kluczem zamiast hasłem i regularne `sudo apt update && sudo apt upgrade`.

## 3. Pierwsze uruchomienie

```bash
git clone https://github.com/Axword/usterka.git && cd usterka
cp deploy/.env.production.example .env
nano .env        # uzupełnij DJANGO_SECRET_KEY i POSTGRES_PASSWORD
```

Hasła wygenerujesz poleceniem `openssl rand -base64 48` (osobno dla każdego). Potem:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build
docker compose -f deploy/docker-compose.prod.yml logs -f web backend   # podgląd; Ctrl+C wychodzi
```

Wejdź na <https://usterka.axword.pl>. Konto administratora panelu Django:

```bash
docker compose -f deploy/docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## 4. Aktualizacja po zmianach w kodzie

```bash
cd usterka && git pull
docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build
```

Migracje bazy uruchamiają się automatycznie przy starcie backendu.

## 5. Kopie zapasowe (nie pomijaj)

Dane to baza i pliki użytkowników. Przykład ręcznej kopii:

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T db pg_dump -U usterka usterka | gzip > backup-$(date +%F).sql.gz
docker run --rm -v usterka_media:/data -v "$PWD":/out alpine tar czf /out/media-$(date +%F).tgz -C /data .
```

Włącz też automatyczne kopie VPS w panelu OVH. Nazwa wolumenu może mieć inny prefiks (sprawdź `docker volume ls`).

## 6. Stripe na produkcji

1. W `.env` wpisz klucze **live** i identyfikatory cen (patrz [06-subskrypcje-stripe.md](06-subskrypcje-stripe.md)).
2. W panelu Stripe dodaj webhook na `https://usterka.axword.pl/api/billing/webhook` ze zdarzeniami `checkout.session.completed` i `customer.subscription.*`, a jego sekret wpisz jako `STRIPE_WEBHOOK_SECRET`.
3. Po zmianie `.env` uruchom ponownie: `docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d`.

## Uwagi

* Produkcja ma wyłączone logowanie „dev” (sam e-mail) i wymaga `DJANGO_SECRET_KEY`. Logowanie hasłem działa.
* Limit prób logowania liczy się w pamięci procesu, a gunicorn ma 3 procesy, więc efektywny limit jest nieco luźniejszy. Pełna dokładność wymaga wspólnego cache (Redis).
* Pliki `deploy/*` nie były jeszcze uruchomione na prawdziwym serwerze. Konfigurację Compose sprawdziłem, ale pełny start (w tym certyfikat) wychodzi dopiero po ustawieniu DNS na VPS.
