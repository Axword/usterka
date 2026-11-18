# CI/CD i testy

## Co robi pipeline (`.github/workflows/ci.yml`)

| Zadanie | Kiedy | Co sprawdza |
|---|---|---|
| **backend** | każdy push i PR | `ruff check`, zgodność migracji z modelami, `pytest` z **progiem 100% pokrycia** (instrukcje i gałęzie) |
| **frontend** | każdy push i PR | TypeScript (`tsc`), testy `vitest`, build produkcyjny |
| **docker** | każdy push i PR | poprawność `docker-compose.prod.yml` i budowa obrazów produkcyjnych |
| **audit** | każdy push i PR | `pip-audit` i `npm audit` (informacyjnie, nie blokuje) |
| **deploy** | tylko push do `main`, po zielonych powyższych | wdrożenie na VPS przez SSH i test dymny |

Nowy push do tej samej gałęzi anuluje trwający przebieg PR-a. Wdrożenia nie są anulowane w trakcie.

## Testy backendu

```bash
cd application
pytest                      # pełny zestaw; zawiera pokrycie, próg 100% (pyproject.toml)
pytest tests/test_auth.py -k lockout --no-cov   # pojedynczy test, bez progu pokrycia
```

Zasady przyjęte w testach:

* **Jeden plik na moduł** (`test_auth.py`, `test_defects.py`, `test_billing.py`…), wspólne fixtures w `conftest.py`, fabryki danych w `tests/helpers.py`.
* **Izolacja:** każdy test ma czystą bazę, pusty cache (liczniki blokad) i własny katalog plików (`tmp_path`). Testy nie zależą od kolejności: uruchamia je losowo `pytest-randomly`.
* **Zachowania, nie implementacja:** testy wywołują prawdziwe API (`Client`), a mocki są tylko na granicach (Stripe, Microsoft Graph, MSAL, JWKS). Sygnatury webhooków Stripe i tokeny JWT są liczone prawdziwymi algorytmami.
* **Parametryzacja** (`@pytest.mark.parametrize`) dla warunków brzegowych i walidacji.
* **Ścisła konfiguracja:** `--strict-markers`, `--strict-config`, ostrzeżenia `RuntimeWarning` jako błędy.
* **100% to instrukcje i gałęzie.** Pominięte są tylko pliki bez logiki: `manage.py`, migracje, same testy.
* Strumienie plików z API trzeba zamykać (`response.close()`), inaczej Windows nie pozwoli usunąć pliku.

Frontend: `npm test` (vitest) obejmuje na razie funkcje pomocnicze (daty, usterki, szkic). Testów komponentów jeszcze nie ma.

## Wdrożenie automatyczne (CD)

Po zielonym CI na `main` GitHub łączy się z VPS-em kluczem SSH i uruchamia `deploy/deploy.sh`: pobiera kod, przebudowuje kontenery, czeka aż aplikacja odpowie i sprawdza adres publiczny.

**Bezpieczeństwo:** klucz CI jest zapisany w `~ubuntu/.ssh/authorized_keys` z ograniczeniem `command="bash …/deploy.sh"`. Może uruchomić tylko ten jeden skrypt: nie dostaje powłoki, tunelowania ani agenta. Adres serwera jest przypięty kluczem hosta (`StrictHostKeyChecking=yes`).

### Jednorazowa konfiguracja w GitHubie

Repozytorium → **Settings → Secrets and variables → Actions**:

| Typ | Nazwa | Wartość |
|---|---|---|
| Secret | `VPS_HOST` | `15.235.90.35` |
| Secret | `VPS_USER` | `ubuntu` |
| Secret | `VPS_SSH_KEY` | cała zawartość pliku `~/.ssh/usterka_deploy_ci` z komputera, na którym wygenerowano klucz (z liniami BEGIN/END) |
| Secret | `VPS_HOST_KEY` | zawartość pliku `~/.ssh/usterka_vps_hostkey.txt` (jedna linia `15.235.90.35 ssh-ed25519 …`) |
| Variable | `DEPLOY_ENABLED` | `true` (dopiero po dodaniu czterech sekretów) |

Dodatkowo (zalecane) **Settings → Environments → production**: włącz „Required reviewers”, jeśli chcesz zatwierdzać każde wdrożenie ręcznie, oraz **Settings → Branches**: reguła dla `main` wymagająca zielonych zadań `backend`, `frontend` i `docker`.

### Ręczne wdrożenie / wycofanie

```bash
ssh ubuntu@15.235.90.35 'cd ~/usterka && bash deploy/deploy.sh'      # wdrożenie z main
ssh ubuntu@15.235.90.35 'cd ~/usterka && git checkout <stary-commit> && sudo docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build'  # powrót do wersji
```

Uwaga: deploy.sh robi `git reset --hard origin/main`, więc na serwerze nie edytuj śledzonych plików (plik `.env` jest ignorowany przez git i bezpieczny).

### Cofnięcie dostępu CI

Usuń linię z `github-actions-usterka-deploy` z `~/.ssh/authorized_keys` na serwerze i sekret `VPS_SSH_KEY` w GitHubie.
