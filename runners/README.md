# Runners

There are a few possibilities to use as runners for this libraries, such as the playwright browser executables, natively installed browsers or headless and headful browsers in containers.

## Playwright browsers

To run the library using the playwright browser executables, make sure have it installed using `playwright`:

```bash
pip install --upgrade pip
pip install playwright
playwright install
```

Test this installation running following command, testing `chromium`, `firefox` and `webkit` in headless mode.

```bash
python ./runners/executable/test.py
```

See the output in `./out/executable/example-{browser_type.name}.png`

Learn more about it: <https://playwright.dev/docs/browsers>

## Docker containers

The docker containers usually expose the debug port `9222` to the browser running inside the container for automation. This is a good setup for testing and automation, as it does not interfere with your local setup. There are three options proposed to run such a docker container, two with GUI and a headless option.

Currently, only docker containers using the chromium browser are documented.

### kasmvnc

A good solution is the [kasmvnc](https://github.com/linuxserver/docker-baseimage-kasmvnc) technology and exposing the GUI inside the container via another browser window.

To use this setup for a [chromium browser on kasmvnc](https://docs.linuxserver.io/images/docker-chromium/) with [debug port](https://github.com/Truth1984/docker-chromium), build and up the docker compose file in `./runners/kasmvnc` and connect to `http://localhost:3000`. You will see a chromium browser to interact and a `debug` port open on `9222`.

Test this installation running following command.

```bash
python ./runners/kasmvnc/test.py
```

See the output in `./out/kasmvnc/example.png`

### novnc

Another solution is built on the [docker-baseimage-gui from jlesage](jlesage/baseimage-gui:alpine-3.20-v4), which relies on less constraints, requiring no additional privileges or hardware (such as gpu for rendering) and running purely on CPU, is using a `novnc` setup in combination with a gui framework (such as the X server/TigerVNC). Further, it is using `chromium-swiftshader` to purely render on CPU, even 3D for WebGL. Build and up the docker compose file in `./runners/novnc` and connect to `http://localhost:5800`. You will see a chromium browser to interact and a `debug` port open on `9222`.

Test this installation running following command.

```bash
python ./runners/novnc/test.py
```

See the output in `./out/novnc/example.png`

### headless

This is a solution, only requiring the minimum of tools for running a browser in headless mode for pure automation. No human interaction through a visualisation available. Further, it is using `chromium-swiftshader` to purely render on CPU, even 3D for WebGL.  Build and up the docker compose file in `./runners/headless`. You will get a headless chromium browser with a `debug` port open on `9222`.

Test this installation running following command.

```bash
python ./runners/headless/test.py
```

See the output in `./out/headless/example.png`

## Native browsers

The `chrome` and `firefox` both support the `debug` port (usually on `9222`) to control the browser externally. You can launch those browsers using a command as followed. Be aware, this might differ from setup to setup.

I currently only tested it using the native Chrome/Chromium browser, for other native setups, help yourself :)

### Chrome

For different OS you need different approaches.

```bash
# Windows
chrome.exe --remote-debugging-port=9222
# macOS
/Applications/Chromium.app/Contents/MacOS/Chromium --remote-debugging-port=9222
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
# linux
chromium-browser --remote-debugging-port=9222
```

Source: <https://www.chromium.org/developers/how-tos/run-chromium-with-flags/>

### Firefox

Interesting source: <https://embracethered.com/blog/posts/2020/cookies-on-firefox/>
