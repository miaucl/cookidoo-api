# Cookidoo API

[![PyPI version](https://badge.fury.io/py/cookidoo-api.svg)](https://pypi.org/p/cookidoo-api)

An unofficial python package to access Cookidoo.

[![Unit tests](https://github.com/miaucl/cookidoo-api/actions/workflows/unit-tests.yaml/badge.svg)](https://github.com/miaucl/cookidoo-api/actions/workflows/unit-tests.yaml)
[![Smoke test](https://github.com/miaucl/cookidoo-api/actions/workflows/smoke-test.yaml/badge.svg)](https://github.com/miaucl/cookidoo-api/actions/workflows/smoke-test.yaml)
[![codecov](https://codecov.io/gh/miaucl/cookidoo-api/graph/badge.svg?token=743ZRO8FRT)](https://codecov.io/gh/miaucl/cookidoo-api)
[![Ruff](https://github.com/miaucl/cookidoo-api/actions/workflows/ruff.yml/badge.svg)](https://github.com/miaucl/cookidoo-api/actions/workflows/ruff.yml)
[![Mypy](https://github.com/miaucl/cookidoo-api/actions/workflows/mypy.yaml/badge.svg)](https://github.com/miaucl/cookidoo-api/actions/workflows/mypy.yaml)
[![Markdownlint](https://github.com/miaucl/cookidoo-api/actions/workflows/markdownlint.yml/badge.svg)](https://github.com/miaucl/cookidoo-api/actions/workflows/markdownlint.yml)

[![GitHub](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA)](https://github.com/sponsors/miaucl)
[![Patreon](https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white)](https://patreon.com/miaucl)
[![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/miaucl)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/sponsormiaucl)

## Disclaimer

The developers of this module are in no way endorsed by or affiliated with Cookidoo or Vorwerk, or any associated subsidiaries, logos or trademarks.

## Installation

`pip install cookidoo-api`

## Documentation

See below for usage examples.

## Usage Example

The API is based on the `aiohttp` library.

Make sure to have stored your credentials in the top-level file `.env` as such, to loaded by `dotenv`. Alternatively, provide the environment variables by any other `dotenv` compatible means.

```text
EMAIL=your@mail.com
PASSWORD=password
```

Run the [example script](https://github.com/miaucl/cookidoo-api/blob/master/example.py) and have a look at the inline comments for more explanation.

## Exceptions

In case something goes wrong during a request, several [exceptions](https://github.com/miaucl/cookidoo/blob/master/cookidoo_api/exceptions.py) can be thrown, all inheriting from `CookidooException`.

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

## Dev

Setup the dev environment using VSCode, it is highly recommended.

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

### Raw API Requests

The raw requests intercepted between the Cookidoo Android App and the backend can be found here `./docs/raw-api-requests`. They have been used to reconstruct the API which is implemented in this library.

## Testing

There is a set of tests based on the current behaviour of the API.

### Unit tests

The unit tests base on the recorded payloads captured between the server and the android app. They are a snapshot and might change.

### Smoke tests

The smoke tests implements a series of request querying the server. It tries to cover as much functionality as possible while not impacting the server too much (we want to stay nice and not get noticed ^^). Therefore, it still might be the case that something breaks without noticing. Further, as it is a github action, only **non-premium** are tested, as it is currently not deemed worth keeping premium subscription for this sole purpose (might change my mind with a few donations^^). Should something break for premium features, a temporary account with trial period is created easily.

### Releasing

A _final version_ can only be released from the `master` branch. To pass the gates of the `publish` workflow, the version must match in both the `tag` and `cookidoo_api/__init__.py`.

release a prerelease version, it must be done from a feature branch (**not** `master`). Prerelease versions are explicitly marked as such on the GitHub release page.

## Roadmap

- [x] Add custom recipes to calendar and shopping list
- [ ] Edit custom recipes
- [ ] Create blank custom recipes (not copy existing)
