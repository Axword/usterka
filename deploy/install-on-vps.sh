#!/usr/bin/env bash
# Instalacja usterki na VPS jedną komendą (uruchom na serwerze jako zwykły użytkownik z sudo):
#   curl -fsSL https://raw.githubusercontent.com/Axword/usterka/main/deploy/install-on-vps.sh | bash
# Skrypt NIE zmienia Twojego Caddy ani innych stron: stawia tylko kontenery usterki na 127.0.0.1:8081
# i na końcu drukuje blok do dopisania w Caddyfile.
set -euo pipefail

DOMAIN="${DOMAIN:-usterka.axword.pl}"
DIR="${DIR:-$HOME/usterka}"

echo "==> Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi
DOCKER="docker"
docker ps >/dev/null 2>&1 || DOCKER="sudo docker"

echo "==> Port 8081 musi być wolny"
if sudo ss -tln | grep -q '127.0.0.1:8081\|0.0.0.0:8081\|\*:8081'; then
  if ! $DOCKER ps --format '{{.Names}}' | grep -q '^usterka-web-1'; then
    echo "Port 8081 jest już zajęty przez coś innego. Przerywam, nic nie zmieniono."; exit 1
  fi
fi

echo "==> Kod"
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull --ff-only; else git clone https://github.com/Axword/usterka.git "$DIR"; fi
cd "$DIR"

echo "==> Plik .env (sekrety generowane lokalnie, tylko jeśli go jeszcze nie ma)"
if [ ! -f .env ]; then
  cp deploy/.env.production.example .env
  sed -i "s|^DOMAIN=.*|DOMAIN=$DOMAIN|" .env
  sed -i "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n/+=' | cut -c1-64)|" .env
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n/+=' | cut -c1-32)|" .env
  chmod 600 .env
fi

echo "==> Budowa i start (kilka minut)"
$DOCKER compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build

echo "==> Test lokalny"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/ || true)
  [ "$code" = "200" ] && break; sleep 3
done
echo "Frontend: HTTP $code"
echo "API:      HTTP $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/api/billing/plans || true)"

cat <<EOF

==> GOTOWE. Usterka działa lokalnie na 127.0.0.1:8081. Nic publicznie jeszcze się nie zmieniło.
Teraz dopisz do SWOJEGO Caddyfile (obok lol-kontra) ten blok, wariant zależnie od tego, gdzie działa Caddy:

  # Caddy jako usługa na hoście:
  $DOMAIN {
      reverse_proxy 127.0.0.1:8081
  }

  # Caddy w Dockerze:
  $DOMAIN {
      reverse_proxy host.docker.internal:8081
  }

i przeładuj Caddy (bez przerwy dla innych stron). Szczegóły: docs/07-wdrozenie-ovh.md
EOF
