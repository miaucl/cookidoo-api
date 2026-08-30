# OAuth2 client credentials

Since the switch to OAuth2, the login flow authenticates as an OAuth2 client:
it needs a **client id**, a **client secret** and the **redirect uri** that is
registered for that client.

These are *not* user credentials, they identify the application performing the
login. This library does **not** ship them, and there is no default — you have
to supply your own via `CookidooConfig`:

```python
from cookidoo_api import Cookidoo, CookidooConfig

cookidoo = Cookidoo(
    session,
    cfg=CookidooConfig(
        email=os.environ["EMAIL"],
        password=os.environ["PASSWORD"],
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
        redirect_uri=os.environ["REDIRECT_URI"],
    ),
)
```

If any of the three is missing, `login()` raises a `CookidooConfigException`
before performing any request.

## Obtaining the values

The credentials belong to the official Cookidoo mobile app, so they can be read
out of a copy of the app you own, or observed on the wire while it logs in.

### With the helper script

[`scripts/extract-oauth-client.py`](https://github.com/miaucl/cookidoo-api/blob/master/scripts/extract-oauth-client.py)
reads an APK you supply and reports the credential candidates it finds. It only
uses the standard library, no `apktool` or other tooling needed:

```bash
./scripts/extract-oauth-client.py cookidoo.apk

# or write the best candidates straight into your .env
./scripts/extract-oauth-client.py cookidoo.apk --env >> .env
```

It collects the string constants the APK carries (the `classes*.dex` string
pools, the `resources.arsc` and binary XML string pools, and plain text assets)
and then, first of all, looks for the ready made HTTP Basic header the app uses
against the token endpoint. That header is a base64 of `client_id:client_secret`,
so decoding it recovers both halves exactly rather than by guesswork. The
redirect uri and any leftover field are ranked heuristically on top.

An app ships one client per environment it can reach, so expect several pairs
in the report:

```text
client credentials (decoded from a Basic auth header):
  kupferwerk-client-nwot:...
  mobile-android:...  <-- selected
  mobile-ios:...
```

Pick the one matching the flow you want with `--client-id`. If the token
endpoint answers `invalid_client`, try another secret for the same id. When
nothing plausible shows up at all, search the extracted strings yourself:

```bash
./scripts/extract-oauth-client.py cookidoo.apk --grep 'grant|secret|client'
```

The script does not download anything: bring your own APK, e.g. pulled off a
device you own with `adb shell pm path com.vorwerk.cookidoo` followed by
`adb pull <path>`.

### By hand

1. **From the app package.** Unpack the APK (e.g. with `apktool`) and look
   through the decoded resources and smali for the OAuth configuration. The
   client id is a short identifier, the redirect uri is a custom scheme also
   declared as an intent filter in `AndroidManifest.xml`, and the client secret
   sits next to them.

2. **From the network traffic.** Run the app through an intercepting proxy
   (e.g. mitmproxy) with the proxy CA trusted on the device, and log in. The
   authorize request carries `client_id` and `redirect_uri` as query
   parameters; the token request sends the client id and secret as an HTTP
   Basic `Authorization` header, which is a base64 of `client_id:client_secret`.

A single APK can carry more than one client. This one, for example, ships a
`mobile-android` client (two secrets for it, in different code paths), a
`mobile-ios` client, and a `kupferwerk-client-nwot` client. Use the
`mobile-android` values for this library. If a token endpoint ever answers
`invalid_client`, try another secret for the same client id, or re-capture from
a current app build.

## Please do not redistribute

Do not commit the values into this repository, into an integration, or into any
other publicly shared configuration. Keep them in an environment variable, a
secret store, or a config entry that the user fills in themselves.
