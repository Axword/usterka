# 05. Logowanie Microsoft i SharePoint

## Jak to działa

1. Osoba klika „Zaloguj kontem Microsoft” → MSAL przekierowuje do Microsoft → wraca z tokenem dla naszego API.
2. Frontend wysyła ten token w każdym żądaniu (`Authorization: Bearer ...`).
3. Backend sprawdza podpis tokenu (klucze Microsoft), odbiorcę (`api://<client-id>`) i dzierżawę.
4. Pierwsze logowanie: tworzy się konto. Pierwsza osoba z danej firmy zakłada organizację i zostaje administratorem. Kolejne dołączają jako inspektorzy.
5. Zapis raportu do SharePoint: backend wymienia token osoby na token Microsoft Graph (**On-Behalf-Of**). Plik zapisuje się z uprawnieniami tej osoby. Bez prawa zapisu w bibliotece – błąd, raport zostaje w archiwum aplikacji.

## Rejestracja aplikacji (raz, ok. 15 minut)

Portal: <https://entra.microsoft.com> → **Applications → App registrations → New registration**.

1. **Name:** `Usterki na planie`.
2. **Supported account types:**
   - jedna firma → *Accounts in this organizational directory only*,
   - wiele firm (SaaS) → *Accounts in any organizational directory*.
3. **Redirect URI:** platforma **Single-page application (SPA)**, adres `http://localhost:5173`. Później dodaj adres produkcyjny.
4. Zapisz **Application (client) ID** → `ENTRA_CLIENT_ID` w `.env`.
5. Przy jednej firmie zapisz **Directory (tenant) ID** → `ENTRA_TENANT`. Przy wielu: `ENTRA_TENANT=organizations`.

### Udostępnienie API

1. **Expose an API → Application ID URI → Set** → zostaw `api://<client-id>`.
2. **Add a scope:**
   - Scope name: `access_as_user`
   - Who can consent: *Admins and users*
   - Opis: „Dostęp do Usterki na planie w Twoim imieniu”.

### Uprawnienia do SharePoint

1. **API permissions → Add a permission → Microsoft Graph → Delegated permissions**.
2. Zaznacz `Sites.ReadWrite.All` (zapis w witrynach, do których osoba ma dostęp).
3. **Grant admin consent** (wymaga administratora Microsoft 365 firmy).

### Sekret dla backendu (potrzebny do On-Behalf-Of)

1. **Certificates & secrets → New client secret**, ważność np. 12 miesięcy.
2. Skopiuj **Value** od razu → `ENTRA_CLIENT_SECRET` w `.env`.
3. Wpisz w kalendarz datę wygaśnięcia – po niej zapis do SharePoint przestanie działać.

### Wersja tokenu

**Manifest** → ustaw `"requestedAccessTokenVersion": 2` (w nowym edytorze: `api.requestedAccessTokenVersion`). Backend obsługuje v1 i v2, ale v2 jest zalecana.

## `.env` – przykład

```ini
AUTH_DEV_LOGIN=1          # na produkcji 0
ENTRA_CLIENT_ID=11111111-2222-3333-4444-555555555555
ENTRA_CLIENT_SECRET=***
ENTRA_TENANT=organizations
ENTRA_API_AUDIENCE=       # puste = api://<ENTRA_CLIENT_ID>
ENTRA_ALLOW_ORG_SIGNUP=1  # 0 = tylko firmy dodane ręcznie w adminie
```

Po restarcie backendu na ekranie logowania pojawi się przycisk Microsoft.

## Ustawienia SharePoint w aplikacji

Administrator organizacji: **Ustawienia → SharePoint**.

| Pole | Przykład |
|---|---|
| Adres witryny | `https://firma.sharepoint.com/sites/Odbiory` |
| Biblioteka | `Dokumenty` (nazwa wyświetlana lub z adresu, np. `Shared Documents`) |
| Folder | `Usterki/{inwestycja}` – brakujące foldery tworzą się same |

## Najczęstsze błędy

| Komunikat | Przyczyna | Rozwiązanie |
|---|---|---|
| „Brak zgody na dostęp do SharePoint” | Brak admin consent | Punkt „Uprawnienia do SharePoint”, krok 3 |
| „Nie masz uprawnień do zapisu…” | Osoba nie ma prawa edycji biblioteki | Dodaj ją do grupy Członkowie witryny |
| „Nie znaleziono biblioteki” | Zła nazwa | Komunikat podaje dostępne nazwy |
| „Zapis do SharePoint wymaga logowania kontem Microsoft” | Zalogowano w trybie dev | Zaloguj się przez Microsoft |
| 401 przy każdym żądaniu | Zły `ENTRA_API_AUDIENCE` lub brak scope `access_as_user` | Sprawdź „Udostępnienie API” |
