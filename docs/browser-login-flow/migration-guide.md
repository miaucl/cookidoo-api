# Token Auth vs Cookie Auth — API Migration Guide

This document explains the differences between the old (deprecated) token-based authentication and the new cookie-based authentication, specifically regarding API request URLs and headers.

## Authentication Methods

### Old: Password Grant (Token Auth) — DEPRECATED

- **Login**: `POST https://{cc}.tmmobile.vorwerk-digital.com/ciam/auth/token` with `grant_type=password`
- **API base URL**: `https://{cc}.tmmobile.vorwerk-digital.com`
- **Auth header**: `Authorization: Bearer {access_token}`
- **Refresh**: Explicit `POST` with `grant_type=refresh_token`

### New: Browser OAuth2 (Cookie Auth)

- **Login**: Browser redirect chain through `cookidoo.{tld}` → CIAM → callback (see [browser-login-flow/README.md](browser-login-flow/README.md))
- **API base URL**: `https://cookidoo.{tld}`
- **Auth header**: None — cookies are sent automatically (`_oauth2_proxy`, `v-authenticated`, `v-is-authenticated`)
- **Refresh**: Automatic — the OAuth2 proxy handles token refresh transparently

## URL Mapping

The API paths are identical between old and new. Only the base URL (host) changes:

| Old Base URL | New Base URL | Country |
| --- | --- | --- |
| `https://ch.tmmobile.vorwerk-digital.com` | `https://cookidoo.ch` | Switzerland |
| `https://de.tmmobile.vorwerk-digital.com` | `https://cookidoo.de` | Germany |
| `https://it.tmmobile.vorwerk-digital.com` | `https://cookidoo.it` | Italy |
| `https://pl.tmmobile.vorwerk-digital.com` | `https://cookidoo.pl` | Poland |
| `https://ie.tmmobile.vorwerk-digital.com` | `https://cookidoo.co.uk` | Ireland/UK |
| `https://ma.tmmobile.vorwerk-digital.com` | `https://cookidoo.international` | International |

**Note:** The old URLs used two-letter country codes as subdomains (`ch.tmmobile...`, `de.tmmobile...`). The new URLs use country-specific TLDs (`cookidoo.ch`, `cookidoo.de`) or special domains (`cookidoo.co.uk`, `cookidoo.international`). The correct domain for each tenant is available in the localization data (`localization.url`).

## Request Comparison

### Example: Get Subscriptions

**Old (Token Auth):**

```http
GET https://ch.tmmobile.vorwerk-digital.com/ownership/subscriptions
Authorization: Bearer eyJhbGciOiJ...
Accept: application/json
```

**New (Cookie Auth):**

```http
GET https://cookidoo.ch/ownership/subscriptions
Cookie: _oauth2_proxy=...; v-authenticated=...; v-is-authenticated=true
Accept: application/json
```

### Example: Get Recipe Details

**Old (Token Auth):**

```http
GET https://ch.tmmobile.vorwerk-digital.com/recipes/recipe/de-CH/r907015
Authorization: Bearer eyJhbGciOiJ...
Accept: application/vnd.vorwerk.recipe.embedded.hal+json
```

**New (Cookie Auth):**

```http
GET https://cookidoo.ch/recipes/recipe/de-CH/r907015
Cookie: _oauth2_proxy=...; v-authenticated=...; v-is-authenticated=true
Accept: application/vnd.vorwerk.recipe.embedded.hal+json
```

### Example: Shopping List

**Old (Token Auth):**

```http
GET https://ch.tmmobile.vorwerk-digital.com/shopping/de-CH
Authorization: Bearer eyJhbGciOiJ...
```

**New (Cookie Auth):**

```http
GET https://cookidoo.ch/shopping/de-CH
Cookie: _oauth2_proxy=...; v-authenticated=...; v-is-authenticated=true
```

## What Changes, What Stays the Same

| Aspect | Changes? | Details |
| -------- | ---------- | ------- |
| API paths | ❌ No | `/ownership/subscriptions`, `/recipes/recipe/{lang}/{id}`, `/shopping/{lang}`, etc. — all identical |
| Base URL / host | ✅ Yes | `{cc}.tmmobile.vorwerk-digital.com` → `cookidoo.{tld}` |
| Authentication mechanism | ✅ Yes | `Authorization: Bearer` header → session cookies |
| Login flow | ✅ Yes | Single POST with password → multi-step browser redirect chain |
| Token refresh | ✅ Yes | Explicit refresh_token grant → automatic (proxy-managed) |
| Response format | ❌ No | Same JSON responses from the backend API |
| Accept headers | ❌ No | Same content types |

## Why the Change

The `tmmobile.vorwerk-digital.com` endpoint is the mobile app API that requires a Bearer token obtained via the password grant. This grant type is being deprecated.

The `cookidoo.{tld}` endpoint is the web application, which sits behind an OAuth2 proxy. The proxy:

1. Accepts session cookies from the client
2. Translates them into Bearer tokens internally
3. Forwards the authenticated request to the same backend API

This means the backend API is the same — only the entry point and authentication mechanism differ.
