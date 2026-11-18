#!/usr/bin/env bash
# Wdrożenie na VPS. Uruchamiane z GitHub Actions przez SSH jako „forced command”:
# klucz CI w authorized_keys może uruchomić WYŁĄCZNIE ten skrypt (nie ma powłoki ani innych poleceń).
# Całość w funkcji main, bo git reset podmienia ten plik w trakcie działania.
set -euo pipefail

main() {
  cd "$HOME/usterka"
  echo "==> Pobieram kod"
  git fetch --quiet origin main
  git reset --hard origin/main
  git log --oneline -1

  echo "==> Budowa i start kontenerów"
  sudo docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build --remove-orphans

  echo "==> Sprawdzam, czy aplikacja odpowiada"
  bind=$(grep -E '^WEB_BIND=' .env | cut -d= -f2 || true)
  bind=${bind:-127.0.0.1}
  for _ in $(seq 1 40); do
    code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: usterka.axword.pl' -H 'X-Forwarded-Proto: https' "http://$bind:8081/api/billing/plans" || true)
    if [ "$code" = "200" ]; then echo "OK ($code)"; sudo docker image prune -f >/dev/null; return 0; fi
    sleep 3
  done
  echo "Aplikacja nie odpowiada po wdrożeniu. Logi:" >&2
  sudo docker compose -f deploy/docker-compose.prod.yml --env-file .env logs --tail 40 backend >&2
  return 1
}

main "$@"
exit $?
