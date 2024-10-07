# Cookidoo API

[![PyPI version](https://badge.fury.io/py/cookidoo-api.svg)](https://pypi.org/p/cookidoo-api)

An unofficial python package to access Cookidoo.

[![Lint](https://github.com/miaucl/ha-addons/actions/workflows/lint.yaml/badge.svg)](https://github.com/miaucl/ha-addons/actions/workflows/lint.yaml)

[![GitHub](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA)](https://github.com/sponsors/miaucl)
[![Patreon](https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white)](https://patreon.com/miaucl)
[![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/miaucl)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/sponsormiaucl)

## Disclaimer

The developers of this module are in no way endorsed by or affiliated with Cookidoo or Vorwerk, or any associated subsidiaries, logos or trademarks.

## Installation

**Disclaimer: This library needs a runner to execute the calls through web automation. Make sure to have it correctly setup using one of the following options before proceeding.**

[Setup runner](https://github.com/cookidoo-api/blob/main/runners)

Once you have tested your runner, install the library and use it with your runner.

`pip install cookidoo-api`

## Documentation

See below for usage examples. See [Exceptions](#exceptions) for API-specific exceptions and mitigation strategies for common exceptions.

## Usage Example

The API is based on the async HTTP library `aiohttp`.

```python
import aiohttp
import asyncio
import logging
import sys

from bring_api import Bring

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

async def main():
  async with aiohttp.ClientSession() as session:
    # Create Bring instance with email and password
    bring = Bring(session, "MAIL", "PASSWORD")
    # Login
    await bring.login()

    # Get information about all available shopping lists
    lists = (await bring.load_lists())["lists"]

    # Save an item with specifications to a certain shopping list
    await bring.save_item(lists[0]['listUuid'], 'Milk', 'low fat')

    # Save another item
    await bring.save_item(lists[0]['listUuid'], 'Carrots')

    # Get all the items of a list
    items = await bring.get_list(lists[0]['listUuid'])
    print(items)

    # Check off an item
    await bring.complete_item(lists[0]['listUuid'], 'Carrots')

    # Remove an item from a list
    await bring.remove_item(lists[0]['listUuid'], 'Milk')

asyncio.run(main())
```

TODO

## Exceptions

In case something goes wrong during a request, several exceptions can be thrown.
They will either be BringRequestException, BringParseException, or BringAuthException, depending on the context. All inherit from BringException.

### Another asyncio event loop is

With the async calls, you might encounter an error that another asyncio event loop is already running on the same thread. This is expected behavior according to the asyncio.run() [documentation](https://docs.python.org/3/library/asyncio-runner.html#asyncio.run). You cannot use more than one aiohttp session per thread, reuse the existing one!

### Exception ignored: RuntimeError: Event loop is closed

Due to a known issue in some versions of aiohttp when using Windows, you might encounter a similar error to this:

```python
Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x00000000>
Traceback (most recent call last):
  File "C:\...\py38\lib\asyncio\proactor_events.py", line 116, in __del__
    self.close()
  File "C:\...\py38\lib\asyncio\proactor_events.py", line 108, in close
    self._loop.call_soon(self._call_connection_lost, None)
  File "C:\...\py38\lib\asyncio\base_events.py", line 719, in call_soon
    self._check_closed()
  File "C:\...\py38\lib\asyncio\base_events.py", line 508, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed
```

You can fix this according to [this](https://stackoverflow.com/questions/68123296/asyncio-throws-runtime-error-with-exception-ignored) StackOverflow answer by adding the following line of code before executing the library:

```python
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

## Bot detection and captcha problems

There is an inbuilt bot detection on cookidoo which can block the login process. There is a clear error message, when that happens. The tokens are valid for a fixed duration and therefore the library tries to minimize the amount of logins required to avoid the captcha process. Unfortunately, this is not always possible when developing or debugging a setup, and you might run into it. To continue, either wait a day or switch to a runner with a gui and enable `captcha` mode to manually solve the captcha during the login or a service such as [`capsolver`](https://www.capsolver.com/).

It is generally advised, to first try the login in `fail` mode and only activate a recovery mode on a `CookidooAuthBotDetectionException` raised.

### Captcha recovery mode `user_input`

```python
cookidoo = Cookidoo(<your headful browser setup>)
await cookidoo.login(captcha_recovery_mode="user_input")
```

_Be aware, using this option with a headless browser will indefinitely block the process in login, as it is waiting for user action._

### Captcha recovery mode `recaptcha`

This requires the `capsolver` to be installed.

```bash
pip install capsolver
```

```python
cookidoo = Cookidoo(<your browser setup>)
await cookidoo.login(captcha_recovery_mode="capsolver")
```

**This is not yet implemented.**

Alternatively, they also provide a [browser extension](https://docs.capsolver.com/en/guide/extension/introductions/), which might be a cleaner way.

## Dev

Setup the dev environment using VSCode, is is highly recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_dev.txt
```

Install [pre-commit](https://pre-commit.com)

```bash
pre-commit install

# Run the commit hooks manually
pre-commit run --all-files
```

Following VSCode integrations may be helpful:

- [ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)
- [mypy](https://marketplace.visualstudio.com/items?itemName=matangover.mypy)
- [markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint)
