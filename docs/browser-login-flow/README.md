# Browser OAuth2 Login Flow

This documents the browser-based OAuth2 Authorization Code flow used by the Cookidoo web application. This flow replaced the deprecated password grant (`grant_type=password`) used by the mobile API.

The flow was reverse-engineered from a HAR (HTTP Archive) recording of a browser login session against `cookidoo.ch`.

## Overview

The login is a multi-step redirect chain across three domains:

1. **cookidoo.{tld}** — the application domain (e.g. `cookidoo.ch`, `cookidoo.de`)
2. **ciam.prod.cookidoo.vorwerk-digital.com** — the OAuth2/CIAM authorization server
3. **eu.login.vorwerk.com** — the login UI (renders the credential form)

After successful authentication, session cookies are set on the `cookidoo.{tld}` domain and all subsequent API calls are authenticated via those cookies.

## Redirect Chain

```http
GET cookidoo.ch/profile/{lang}/login?redirectAfterLogin=...
  → 302 → cookidoo.ch/oauth2/start?market={cc}&ui_locales={lang}&rd=...
  → 302 → ciam.prod.cookidoo.vorwerk-digital.com/authz-srv/authz?client_id=tmde2-live-v1&code_challenge=...&redirect_uri=...
  → 302 → eu.login.vorwerk.com/ciam/login?requestId={REQUEST_ID}&view_type=login&market={cc}&ui_locales={lang}
  → 200   (HTML login page with form)
```

## Step-by-Step

### Step 1: Initiate Login

```http
GET https://cookidoo.ch/profile/de-CH/login?redirectAfterLogin=%2Ffoundation%2Fde-CH%2Ffor-you
```

The client follows all redirects. The OAuth2 proxy at `cookidoo.ch/oauth2/start` generates a PKCE code challenge and sets a `_oauth2_proxy_csrf` cookie. The CIAM authorization server issues a `requestId` and redirects to the login page.

### Step 2: Extract `requestId`

The final page at `eu.login.vorwerk.com/ciam/login` returns HTML containing a form with a hidden `requestId` field:

```html
<input type="hidden" name="requestId" value="4814594a-fe30-4c74-aad9-eaf750b3b4a3">
```

This `requestId` is required for the credential POST.

### Step 3: POST Credentials

```http
POST https://ciam.prod.cookidoo.vorwerk-digital.com/login-srv/login
Content-Type: application/x-www-form-urlencoded

requestId={REQUEST_ID}&username={EMAIL}&password={PASSWORD}
```

On success, the server responds with `302` and sets CIAM session cookies:

| Cookie | Domain | Purpose |
| -------- | -------- | ------- |
| `cidaas_sid` | `ciam.prod.cookidoo.vorwerk-digital.com` | CIAM session ID (~1 year) |
| `cidaas_sso` | `ciam.prod.cookidoo.vorwerk-digital.com` | SSO token (~14 days) |
| `cidaas_rl` | `ciam.prod.cookidoo.vorwerk-digital.com` | Remember login (~14 days) |

The `Location` header redirects to `cookidoo.ch/oauth2/callback?code={AUTH_CODE}&state=...`

### Step 4: OAuth2 Callback

```http
GET https://cookidoo.ch/oauth2/callback?code={AUTH_CODE}&state={STATE}
```

The OAuth2 proxy exchanges the authorization code for tokens and sets the application session cookies:

| Cookie | Domain | Max-Age | Purpose |
| -------- | -------- | ------- | ------- |
| `_oauth2_proxy` | `cookidoo.ch` | session | Encrypted session containing access/refresh tokens |
| `v-authenticated` | `cookidoo.ch` | ~30 days | Authentication signature |
| `v-is-authenticated` | `cookidoo.ch` | ~30 days | Boolean flag (`true`) |

The `_oauth2_proxy_csrf` cookie is cleared (set to empty, `max-age=0`).

### Step 5: Final Redirect

```http
GET https://cookidoo.ch/profile/de-CH/login?redirectAfterLogin=...
  → 307 → /foundation/de-CH/for-you
```

The user is now authenticated and redirected to the app.

## Authenticated API Calls

After login, all API calls use cookies automatically:

```http
GET https://cookidoo.ch/ownership/subscriptions
Cookie: _oauth2_proxy=...; v-authenticated=...; v-is-authenticated=true
```

The OAuth2 proxy translates the session cookies into a Bearer token internally before forwarding to the backend API.

## Token Refresh

Token refresh is handled **transparently** by the OAuth2 proxy. The client does not need to explicitly refresh tokens. The proxy intercepts requests, checks if the access token is still valid, and refreshes it using the stored refresh token if needed.

There are three expiry tiers:

- **Access token**: ~10 minutes (auto-refreshed by proxy)
- **SSO / remember-login cookies**: ~14 days
- **Session cookies** (`v-authenticated`): ~30 days

## Cross-Domain Cookies

The login flow crosses multiple domains. When using `aiohttp`, a `CookieJar(unsafe=True)` is required to allow cookies to be sent across domains during the redirect chain.

## Multi-Tenant Support

The login flow is identical across all tenants. Only the domain and language change:

| Tenant | Domain | Example Language |
| -------- | -------- | ----------------- |
| CH | `cookidoo.ch` | `de-CH` |
| DE | `cookidoo.de` | `de-DE` |
| IT | `cookidoo.it` | `it-IT` |
| IE | `cookidoo.co.uk` | `en-GB` |
| PL | `cookidoo.pl` | `pl-PL` |

The CIAM login server (`eu.login.vorwerk.com`) and login-srv (`ciam.prod.cookidoo.vorwerk-digital.com`) are universal across all tenants.
