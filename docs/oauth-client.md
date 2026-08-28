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
Two ways that work:

1. **From the app package.** Unpack the APK of the Cookidoo app installed on
   your own device (e.g. with `apktool`) and look through the decoded
   resources and smali for the OAuth configuration. The client id is a short
   identifier, the redirect uri is a custom scheme also declared as an intent
   filter in `AndroidManifest.xml`, and the client secret sits next to them.

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
