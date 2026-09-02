# OAuth2 client

The login uses the OAuth2 **authorization code** flow with **PKCE**, run as a
**public client**: there is no client secret, and nothing you need to obtain.
Your Cookidoo account is the only credential:

```python
from cookidoo_api import Cookidoo, CookidooConfig

cookidoo = Cookidoo(
    session,
    cfg=CookidooConfig(
        email=os.environ["EMAIL"],
        password=os.environ["PASSWORD"],
    ),
)
```

## Why there is no secret

An OAuth2 client is identified by a **client id** and a **redirect uri**, and
*may* additionally authenticate itself with a **client secret**. The Cookidoo
identity provider (CIAM, a cidaas deployment) does not require the third one
here: when the token request carries a PKCE `code_verifier`, the client secret
is not verified at all.

Observed against the production token endpoint, exchanging the same
authorization code:

| token request | result |
| --- | --- |
| `client_id` + `code_verifier`, no secret | `200` — token |
| `client_id` + `code_verifier` + *wrong* secret | `200` — token |
| `client_id` + `code_verifier` + correct secret | `200` — token |
| `client_id`, **no** `code_verifier`, no secret | `400 invalid_client` |
| `code_verifier`, no `client_id` | `400 invalid_client` |

A deliberately wrong secret being accepted is the decisive one: the secret is
not part of what the server checks. It is PKCE that binds the exchange to the
client instance that started the flow — which is exactly what PKCE exists for,
and why [RFC 8252][rfc8252] prescribes this shape for native apps, whose
"secrets" cannot stay secret in a distributed binary anyway.

So the library sends the client id in the token request body and no
`Authorization` header, and the resulting bearer token is indistinguishable
from one obtained with a secret — same audience, same scopes, same roles, and
the same access to both the Cookidoo API and the remote-monitoring (`iot-api`)
backend.

## What is shipped, and why that is not a secret

Two values are built in as defaults:

- `client_id` — `mobile-android`. A client id is a public identifier by
  definition. [RFC 6749 §2.2][rfc6749-2.2]: *"The client identifier is not a
  secret; it is exposed to the resource owner and MUST NOT be used alone for
  client authentication."*
- `redirect_uri` — `com.vorwerk.cookidoo://code-grant`. The app's URL scheme.
  It travels in the query string of every authorize request, is declared in the
  app manifest, and is registered with the provider precisely so it can be
  matched publicly.

Neither is a credential, so neither is withheld from you or from this
repository.

## Overriding them

They are still plain config fields, should the app's registration ever change
before this library catches up:

```python
CookidooConfig(
    email=...,
    password=...,
    client_id="mobile-ios",
    redirect_uri="com.vorwerk.cookidoo://code-grant",
)
```

Setting either to an empty string raises `CookidooConfigException` at `login()`
rather than producing a confusing `invalid_client` from the server.

If the authorize step starts rejecting the built-in client id, the app's
registration has changed. The current value can be read back out of a copy of
the app you own: the client id is a short kebab identifier and the redirect uri
a custom URI scheme, both plain strings in the APK's `classes*.dex` string
pools and its manifest. Please open an issue so the default can be updated for
everyone.

[rfc6749-2.2]: https://datatracker.ietf.org/doc/html/rfc6749#section-2.2
[rfc8252]: https://datatracker.ietf.org/doc/html/rfc8252#section-8.5
