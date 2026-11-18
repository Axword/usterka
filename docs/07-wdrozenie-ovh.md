# Wdrożenie na VPS w OVH pod usterka.axword.pl

Aplikacja działa na **osobnej subdomenie** `usterka.axword.pl` na tym samym VPS, na którym stoi już `lol-kontra.axword.pl` (Next.js za Caddy). Główna domena `axword.pl` jest na Vercelu i nie jest ruszana. **Istniejące strony zostają bez zmian**: do Twojego Caddy dopisujemy tylko jeden blok.

## Jak to działa

```
Przeglądarka ──HTTPS──▶ Twój istniejący Caddy (80/443, certyfikaty Let's Encrypt)
                          ├── lol-kontra.axword.pl  → Next.js (jak dotąd)
                          └── usterka.axword.pl     → 127.0.0.1:8081
                                                          │
                          kontener „web” (wewnętrzny Caddy): frontend + proxy do API
                                                          │
                          kontener „backend” (gunicorn) ──▶ PostgreSQL + pliki
```

Usterka ma własne kontenery i wolumeny (`usterka_*`), nie dzieli niczego z lol-kontra poza zewnętrznym Caddy. Publicznie wystawiony jest tylko jeden lokalny port **8081**.

## 1. DNS w OVH (zrobione)

W strefie `axword.pl` jest rekord **A `usterka` → 15.235.90.35** (adres VPS). Sprawdzenie: `nslookup usterka.axword.pl` zwraca ten adres.

## 2. Sprawdź, jak działa Twój obecny Caddy (SSH na VPS)

```bash
ssh ubuntu@15.235.90.35
sudo ss -tlnp | grep -E ':80|:443|:8081'      # kto słucha; 8081 powinno być wolne
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}'   # czy Caddy jest w Dockerze
systemctl status caddy --no-pager | head -5               # albo jako usługa systemowa
```

Dalej są dwa warianty, zależnie od wyniku.

## 3. Docker i uruchomienie usterki

```bash
# Docker (pomiń, jeśli już jest)
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER   # potem wyloguj się i wróć

git clone https://github.com/Axword/usterka.git && cd usterka
cp deploy/.env.production.example .env
nano .env        # uzupełnij DJANGO_SECRET_KEY i POSTGRES_PASSWORD (openssl rand -base64 48)

docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build
curl -sI http://127.0.0.1:8081 | head -1     # ma zwrócić HTTP/1.1 200 OK
```

Na tym etapie usterka działa tylko lokalnie na serwerze, więc nic nie może popsuć innych stron.

## 4. Dopisz usterkę do istniejącego Caddy

Dodaj ten blok do Twojego Caddyfile (obok bloku `lol-kontra.axword.pl`):

**Wariant A: Caddy działa na hoście** (usługa systemowa, zwykle `/etc/caddy/Caddyfile`):

```
usterka.axword.pl {
	reverse_proxy 127.0.0.1:8081
}
```

**Wariant B: Caddy działa w Dockerze.** Z kontenera `127.0.0.1` to on sam, więc użyj adresu hosta:

```
usterka.axword.pl {
	reverse_proxy host.docker.internal:8081
}
```

i upewnij się, że kontener Caddy ma `extra_hosts: ["host.docker.internal:host-gateway"]` (dopisz w jego compose i odtwórz kontener). Alternatywnie dołącz kontener Caddy do sieci docker usterki i użyj `web:80`.

Potem zweryfikuj i przeładuj **bez przerwy dla innych stron**:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile      # wariant A
sudo systemctl reload caddy                            # wariant A
docker exec <nazwa_caddy> caddy reload --config /etc/caddy/Caddyfile   # wariant B
```

Caddy sam pobierze certyfikat dla `usterka.axword.pl` (DNS już wskazuje na serwer). Otwórz <https://usterka.axword.pl> i sprawdź też, że <https://lol-kontra.axword.pl> działa jak wcześniej.

Konto administratora panelu Django:

```bash
docker compose -f deploy/docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## Wycofanie zmian (gdyby coś nie działało)

```bash
# usuń blok usterka.axword.pl z Caddyfile i przeładuj Caddy
docker compose -f deploy/docker-compose.prod.yml down        # zatrzymuje usterkę, dane zostają w wolumenach
```

Inne strony nie są w żaden sposób zależne od usterki.

## 5. Aktualizacja po zmianach w kodzie

```bash
cd usterka && git pull
docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build
```

Migracje bazy uruchamiają się automatycznie przy starcie backendu.

## 6. Kopie zapasowe (nie pomijaj)

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T db pg_dump -U usterka usterka | gzip > backup-$(date +%F).sql.gz
docker run --rm -v usterka_media:/data -v "$PWD":/out alpine tar czf /out/media-$(date +%F).tgz -C /data .
```

W panelu OVH masz „Automated backup: Standard” dla całego VPS, ale pg_dump jest pewniejszy dla bazy. Nazwę wolumenu sprawdź przez `docker volume ls`.

## 7. Stripe na produkcji

1. W `.env` wpisz klucze **live** i identyfikatory cen (patrz [06-subskrypcje-stripe.md](06-subskrypcje-stripe.md)).
2. W panelu Stripe dodaj webhook `https://usterka.axword.pl/api/billing/webhook` ze zdarzeniami `checkout.session.completed` i `customer.subscription.*`, a jego sekret wpisz jako `STRIPE_WEBHOOK_SECRET`.
3. Po zmianie `.env`: `docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d`.

## Uwagi

* Zasoby: VPS-1 ma 2 vCPU i 4 GB RAM. Next.js, PostgreSQL i Django mieszczą się, ale to niewiele zapasu. Gunicorn ma 3 procesy; w razie braku pamięci zmniejsz `--workers` w `deploy/docker-compose.prod.yml`.
* Produkcja ma wyłączone logowanie „dev” (sam e-mail) i wymaga `DJANGO_SECRET_KEY`. Logowanie hasłem działa.
* Adres IP klienta (limit prób logowania) pochodzi z `X-Forwarded-For` ustawianego przez zewnętrzny Caddy. Wewnętrzny Caddy ufa mu tylko z sieci prywatnych (`trusted_proxies`).
* Te pliki nie były jeszcze uruchomione na prawdziwym serwerze. Konfigurację Compose sprawdziłem, ale pełny start wychodzi dopiero na VPS.

## Stan wdrożenia i trwałość konfiguracji Caddy

Usterka działa na VPS w `~/usterka` (kontenery `usterka-db-1`, `usterka-backend-1`, `usterka-web-1`), a `WEB_BIND=172.17.0.1` w `.env` wystawia ją na moście docker0 dla Caddy aplikacji `words-v`.

Blok z `deploy/caddy-block-for-words-v.txt` został dopisany ręcznie do Caddyfile **bieżącego wydania** `words-v`. Kolejne wydanie tej aplikacji nadpisze ten plik, więc dopisz ten sam blok w jej repozytorium (`infra/vps/Caddyfile`). Do tego czasu po każdym jej wdrożeniu usterka znika z internetu (kontenery działają dalej) i trzeba blok dopisać ponownie.
