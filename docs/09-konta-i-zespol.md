# Konta, e-maile i zespół

## Reset hasła
1. `/login` → „Nie pamiętasz hasła?” → `/forgot`: wpisujesz e-mail.
2. Zawsze widzisz ten sam komunikat („jeśli konto istnieje, wysłaliśmy link”), więc nie da się sprawdzać, kto ma konto.
3. Link (`/reset-password?uid=…&token=…`) jest ważny **2 godziny** i działa **jednorazowo** (po zmianie hasła przestaje być ważny). Ustawienie: `PASSWORD_RESET_TIMEOUT`.
4. Po zmianie hasła użytkownik jest od razu zalogowany, jego licznik błędnych prób jest zerowany, a adres e-mail uznany za potwierdzony.
5. **Wszystkie wcześniejsze sesje tego konta przestają działać** (token sesji zawiera odcisk hasła). Chroni to przy kradzieży telefonu lub tokenu.
6. Reset nie dotyczy kont Microsoft ani kont bez własnego hasła.

Limity: 5 próśb na adres e-mail i 20 na adres IP w ciągu godziny (HTTP 429).

## Potwierdzanie adresu e-mail
* Rejestracja wysyła link ważny 3 dni. Do czasu potwierdzenia nad aplikacją widać pasek z przyciskiem „Wyślij ponownie”.
* Niepotwierdzony administrator **nie może kupić planu ani zapraszać osób** (zapobiega zakładaniu kont na cudze adresy w celu wysyłania zaproszeń).
* Konta Microsoft, konta z zaproszenia i konta po resecie hasła są potwierdzone od razu (dotarły na skrzynkę). Konta istniejące przed wdrożeniem tej funkcji oznaczyła migracja jako potwierdzone.

## Zaproszenia do zespołu
Administrator: **Ustawienia → Zaproszenia**: e-mail + rola (administrator / inspektor / podgląd).

* Zaproszona osoba dostaje mail z linkiem `/invite/<token>`, ustawia imię i hasło i od razu trafia do zespołu (konto potwierdzone). Zaproszenie ważne **7 dni**, jednorazowe (`INVITATION_DAYS`).
* W bazie jest tylko **skrót** tokenu, więc wyciek bazy nie ujawnia działających linków.
* Ponowne zaproszenie tego samego adresu zastępuje poprzednie. „Cofnij” unieważnia link.
* **Zaproszenia liczą się do limitu osób w planie** (Start: 2 osoby, Pro: 10, Business: bez limitu). Limit sprawdza się przy zapraszaniu i przy przyjęciu.
* Zapraszać można tylko adresy **bez konta**. Jedno konto należy dziś do jednej organizacji.
* Administrator może **usunąć osobę** z zespołu: konto powiązane tylko z tą organizacją jest kasowane (zwalnia adres), a dodane przez nią usterki zostają.

## Konfiguracja poczty (produkcja)
Bez `EMAIL_HOST` aplikacja nie wysyła maili, tylko zapisuje je w logu kontenera (`docker logs usterka-backend-1`), więc **na produkcji trzeba skonfigurować SMTP**. Dla poczty OVH (domena axword.pl ma rekordy MX OVH):

1. W manager.eu.ovhcloud.com → Emails (lub MX Plan) utwórz skrzynkę, np. `noreply@axword.pl`.
2. Na serwerze w `~/usterka/.env` dopisz:
   ```
   EMAIL_HOST=ssl0.ovh.net
   EMAIL_PORT=465
   EMAIL_USE_SSL=1
   EMAIL_HOST_USER=noreply@axword.pl
   EMAIL_HOST_PASSWORD=<hasło skrzynki>
   DEFAULT_FROM_EMAIL=Usterki na planie <noreply@axword.pl>
   ```
3. `cd ~/usterka && bash deploy/deploy.sh` (lub restart kontenera backendu).
4. Test: na stronie logowania „Nie pamiętasz hasła?” z adresem istniejącego konta.

Dostarczalność: w strefie DNS jest już rekord SPF OVH. Dla lepszej reputacji włącz też DKIM w panelu OVH dla skrzynki.

## API
| Metoda | Ścieżka | Opis |
|---|---|---|
| POST | `/auth/password-reset` | `{email}`, zawsze `ok` |
| POST | `/auth/password-reset/confirm` | `{uid, token, password}` → token sesji |
| POST | `/auth/verify-email` | `{token}` |
| POST | `/auth/resend-verification` | wymaga logowania |
| GET | `/auth/invitations/{token}` | dane zaproszenia dla strony przyjęcia |
| POST | `/auth/invitations/{token}/accept` | `{password, name}` → token sesji |
| GET/POST | `/organization/invitations` | lista oczekujących / nowe zaproszenie (admin) |
| DELETE | `/organization/invitations/{id}` | cofnięcie (admin) |
| DELETE | `/organization/members/{id}` | usunięcie osoby (admin) |

## Ekrany
`/forgot`, `/reset-password`, `/verify-email`, `/invite/:token` (pliki `usterka_frontend/src/pages/`), pasek `components/common/VerifyBanner.tsx`, panel zespołu w `pages/SettingsPage.tsx`. Screenshoty: `docs/screenshots/after/desktop-15…21`.
