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

If any of the three is missing, `login()` falls back to the legacy
browser-style cookie-session login instead (see
[docs/browser-login-flow](browser-login-flow/)), so supplying them is
optional but recommended — OAuth2 is the preferred login method going
forward.

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

Note that these values track the app build: they can rotate with an app update.
A token endpoint answering `invalid_client` is the usual symptom, and means the
credentials have to be captured again.

## Please do not redistribute

Do not commit the values into this repository, into an integration, or into any
other publicly shared configuration. Keep them in an environment variable, a
secret store, or a config entry that the user fills in themselves.
