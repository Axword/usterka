# Subskrypcje (Stripe) i logowanie hasłem

## Logowanie e-mail + hasło

* Ekran `/login` ma zakładki **Logowanie** / **Załóż konto**. Rejestracja podaje: imię i nazwisko, nazwę firmy, e-mail, hasło (min. 8 znaków, sprawdzane przez walidatory Django: długość, popularne hasła, same cyfry).
* Każda rejestracja **tworzy nową organizację** i robi z osoby jej administratora. Nie dołączamy automatycznie po domenie e-mail, bo adres nie jest zweryfikowany (inaczej obca osoba z adresem `x@twojafirma.pl` weszłaby do Waszych danych). Kolejne osoby dodaje się przez logowanie Microsoft (ta sama dzierżawa) albo w przyszłości przez zaproszenia.
* API: `POST /auth/register`, `POST /auth/login` → `{token}`. Token jest podpisany (prefiks `pwd.`, ważny 14 dni, `PASSWORD_TOKEN_MAX_AGE`). Hasła zapisuje Django (PBKDF2).
* Wyłączenie: `AUTH_PASSWORD_LOGIN=0`. W przeciwieństwie do logowania „dev” działa bezpiecznie na produkcji.
* Kod: `application/users/services.py` (`register_with_password`, `login_with_password`), `application/core/auth.py`, front: `pages/LoginPage.tsx`.

Nie ma jeszcze: resetu hasła ani potwierdzania e-mail (wymaga wysyłki maili).

## Plany i limity

| Plan | Cena (netto / mies.) | Inwestycje | Osoby |
|---|---|---|---|
| Start | 0 zł | 1 | 2 |
| Pro | 79 zł | 10 | 10 |
| Business | 199 zł | bez limitu | bez limitu |

Cennik i limity są w jednym miejscu: `application/billing/plans.py`. Limit inwestycji jest egzekwowany na serwerze (`POST /projects/` zwraca **402** z opisem). Limit osób jest przygotowany (`check_member_limit`), ale na razie nie ma ścieżki zapraszania, która by go użyła. Gdy plan wygaśnie lub zostanie anulowany, organizacja wraca do Start; istniejące dane zostają, ale nowych inwestycji ponad limit nie utworzy.

## Jak działa płatność

```
Przeglądarka ──POST /billing/checkout──▶ Django ──▶ Stripe Checkout (strona płatności Stripe)
                                                          │
Stripe ──webhook POST /billing/webhook (podpisany)──▶ Django: ustawia plan, status, datę odnowienia
```

* **Źródłem prawdy jest webhook**, nie powrót przeglądarki – dlatego po płatności plan zmienia się po kilku sekundach.
* Zdarzenia obsługiwane: `checkout.session.completed`, `customer.subscription.created/updated/deleted` (`billing/services.py: handle_event`). Podpis weryfikuje `STRIPE_WEBHOOK_SECRET`.
* Zarządzanie kartą, fakturami i anulowaniem: **portal klienta Stripe** (`POST /billing/portal`).
* Dane karty nigdy nie trafiają do naszego serwera.
* Tabela `billing_subscription` (jedna na organizację): plan, status, identyfikatory Stripe, data końca okresu, flaga `cancel_at_period_end`, flaga `is_demo`.

## Tryb demo (lokalnie)

Bez `STRIPE_SECRET_KEY` i przy `DJANGO_DEBUG=true` przycisk „Przejdź na Pro” **symuluje zakup** (plan zmienia się od razu, bez płatności, oznaczony jako demo). Przy `DEBUG=false` bez kluczy zakup jest zablokowany (503), więc produkcja nigdy nie da planu za darmo.

## Uruchomienie z prawdziwym Stripe (tryb testowy)

1. Konto na stripe.com, włączony **tryb testowy**.
2. Produkty: utwórz „Pro” (79 PLN / miesiąc) i „Business” (199 PLN / miesiąc), cykliczne. Skopiuj ID cen (`price_…`).
3. Włącz **Customer portal** w ustawieniach Stripe (Billing → Customer portal).
4. Webhook: lokalnie `stripe listen --forward-to localhost:8000/api/billing/webhook`, na serwerze dodaj endpoint `https://TWOJA-DOMENA/api/billing/webhook` ze zdarzeniami wyżej. Skopiuj sekret `whsec_…`.
5. W `.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_PRO=price_...
   STRIPE_PRICE_BUSINESS=price_...
   ```
6. Test: karta `4242 4242 4242 4242`, dowolna przyszła data i CVC.
7. Produkcja: te same kroki na kluczach „live”. Przed startem sprzedaży uzupełnij dane firmy, regulamin i politykę prywatności oraz skonfiguruj fakturowanie/VAT w Stripe – tego kodu nie zastępuje porady księgowej ani prawnej.

## API

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/billing/plans` | Publiczny cennik (strona startowa) |
| GET | `/billing/subscription` | Plan organizacji i zużycie limitu |
| POST | `/billing/checkout` | `{plan: "pro"\|"business"}` → adres płatności Stripe (admin) |
| POST | `/billing/portal` | Adres portalu klienta (admin) |
| POST | `/billing/downgrade` | Tylko demo: powrót do Start |
| POST | `/billing/webhook` | Zdarzenia Stripe (bez tokenu, podpis) |

## Frontend

| Ekran | Adres | Plik |
|---|---|---|
| Strona startowa (publiczna) | `/welcome` | `pages/LandingPage.tsx` |
| Subskrypcja (po zalogowaniu) | `/subscription` | `pages/SubscriptionPage.tsx` |
| Karty cennika | – | `components/billing/PricingCards.tsx` |

Niezalogowany użytkownik jest przekierowywany na `/welcome`. Wybór planu na stronie startowej prowadzi do rejestracji, a po niej do ekranu Subskrypcja.

## Bezpieczeństwo logowania

| Zabezpieczenie | Jak działa | Gdzie |
|---|---|---|
| Hasła: **Argon2id** | Zwycięzca Password Hashing Competition, odporny na ataki na kartach GPU. Stare skróty (PBKDF2) są po udanym logowaniu automatycznie podmieniane na Argon2 | `PASSWORD_HASHERS` w `config/settings/base.py` |
| Siła hasła | min. 8 znaków, nie z listy popularnych, nie same cyfry, nie podobne do e-maila/imienia, maks. 128 znaków (ochrona przed zasypaniem serwera ogromnym hasłem) | `AUTH_PASSWORD_VALIDATORS` |
| Blokada zgadywania | 5 błędnych prób na e-mail i 20 na adres IP → blokada 15 minut (HTTP 429), nawet z poprawnym hasłem. Udane logowanie zeruje licznik e-maila | `core/throttle.py` |
| Limit rejestracji | 10 kont na godzinę z jednego IP | `core/throttle.py` |
| Brak zdradzania kont | Ten sam komunikat „Nieprawidłowy e-mail lub hasło” i podobny czas odpowiedzi dla istniejącego i nieistniejącego konta | `users/services.py` |
| Tokeny sesji | Podpisane, ważne 14 dni, odrzucane przy zmianie podpisu | `core/auth.py` |
| Produkcja (`DEBUG=false`) | wymuszony HTTPS, HSTS na rok, ciasteczka tylko przez HTTPS, nosniff, `X-Frame-Options: DENY`, wymagany `DJANGO_SECRET_KEY` | `config/settings/base.py` |

Ograniczenia, o których warto wiedzieć:
* Liczniki prób są w pamięci procesu. Przy kilku procesach lub serwerach ustaw wspólny cache (Redis) w `CACHES`, inaczej limit liczy się osobno na każdym.
* Za reverse proxy (nginx, OVH) adres IP klienta bierzemy z `X-Forwarded-For`. Proxy musi go ustawiać i nie przyjmować od klienta, inaczej da się obejść limit IP.
* Nie ma jeszcze resetu hasła, potwierdzania e-maila ani logowania dwuskładnikowego (2FA).
