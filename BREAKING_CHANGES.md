# Breaking changes

This document tracks the breaking changes observed in the Cookidoo API.

## 20260830

- **Authentication switched to the OAuth2 authorization-code flow (with PKCE).** Requests are authenticated with a `Bearer` token again instead of session cookies. The bearer token also reaches the remote-monitoring backend, which the cookie session could not.
- **OAuth2 client credentials must be provided by the caller.** `CookidooConfig` gained the required `client_id`, `client_secret` and `redirect_uri` fields. They are not shipped with this library and have no defaults; `login()` raises a `CookidooConfigException` when they are missing. See [docs/oauth-client.md](docs/oauth-client.md).
- **Token persistence replaces cookie persistence.** Use `save_token(path)` / `load_token(path)` instead of `save_cookies(path)` / `load_cookies(path)`. The tokens are also exposed as a `CookidooAuthData` via the `auth_data` property and can be restored with `apply_auth_data()`.
- **`refresh()` added.** The access token is refreshed automatically before a request when it is about to expire, and can be refreshed explicitly.
- `CookieJar(unsafe=True)` is still required, the login redirect chain continues to rely on cookies.

## 20260508

- **Authentication method changed from password grant to browser OAuth2 flow.** The `grant_type=password` endpoint at `{cc}.tmmobile.vorwerk-digital.com/ciam/auth/token` is deprecated. Authentication now follows the Cookidoo web app's browser-based OAuth2 redirect chain and uses session cookies instead of Bearer tokens.
- **API base URL changed.** All API calls now go through `cookidoo.{tld}` (e.g. `cookidoo.ch`, `cookidoo.de`) instead of `{cc}.tmmobile.vorwerk-digital.com`. API paths remain the same.
- **`CookidooAuthResponse` removed.** The `auth_data` property, `refresh_token()` method, and `expires_in` property have been removed. Token refresh is now handled automatically by the OAuth2 proxy.
- **`CookieJar(unsafe=True)` required.** The `aiohttp.ClientSession` must be created with `CookieJar(unsafe=True)` to support cross-domain cookies during the login redirect chain.
- **Cookie persistence replaces token persistence.** Use `save_cookies(path)` / `load_cookies(path)` instead of the old token save/load pattern.

See [docs/browser-login-flow/migration-guide.md](docs/browser-login-flow/migration-guide.md) for full details.

## 20250811

- `serving_size` is now a _int_ instead of a _str_ and lacks therefore the unit information which was backed in prior.

## 20250624

- Collections (custom and managed) now require the correct `ACCEPT` header field.
