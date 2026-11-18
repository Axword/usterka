#!/usr/bin/env bash
# Ustawia dostęp do SMTP (Brevo) w ~/usterka/.env. Klucz wpisujesz ukryty: nie ląduje w historii poleceń ani w logach.
# Użycie na serwerze:  bash ~/usterka/deploy/set-smtp.sh
set -euo pipefail
cd "$HOME/usterka"
[ -f .env ] || { echo "Brak pliku .env w ~/usterka"; exit 1; }

read -rp "Login SMTP z Brevo (np. 8a1b2c@smtp-brevo.com): " smtp_user
read -rsp "Klucz SMTP (nie będzie widoczny): " smtp_key; echo
read -rp "Adres nadawcy [noreply@axword.pl]: " from_addr
from_addr=${from_addr:-noreply@axword.pl}

set_var() {  # podmienia lub dopisuje zmienną w .env bez używania sed na wartości sekretnej
  local key=$1 value=$2 tmp
  tmp=$(mktemp)
  grep -v -E "^${key}=" .env > "$tmp" || true
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  cat "$tmp" > .env && rm -f "$tmp"
}
set_var EMAIL_HOST smtp-relay.brevo.com
set_var EMAIL_PORT 587
set_var EMAIL_USE_TLS 1
set_var EMAIL_USE_SSL 0
set_var EMAIL_HOST_USER "$smtp_user"
set_var EMAIL_HOST_PASSWORD "$smtp_key"
set_var DEFAULT_FROM_EMAIL "Usterki na planie <${from_addr}>"
chmod 600 .env
echo "Zapisano. Restartuję aplikację..."
bash deploy/deploy.sh
