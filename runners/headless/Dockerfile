FROM alpine:3.20

# Installs latest Chromium package.
RUN apk upgrade --no-cache --available \
    && apk add --no-cache \
      chromium-swiftshader \
      ttf-freefont \
      font-noto-emoji \
      socat \
    && apk add --no-cache \
      --repository=https://dl-cdn.alpinelinux.org/alpine/edge/community \
      font-wqy-zenhei

COPY local.conf /etc/fonts/local.conf

# Add Chromium as a user
RUN mkdir -p /usr/src/app \
    && adduser -D chromium \
    && chown -R chromium:chromium /usr/src/app
# Run Chromium as non-privileged
USER chromium
WORKDIR /usr/src/app

ENV CHROME_BIN=/usr/bin/chromium-browser \
    CHROME_PATH=/usr/lib/chromium/


COPY ./entrypoint.sh /entrypoint.sh

ENTRYPOINT /entrypoint.sh
    