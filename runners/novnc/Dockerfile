FROM jlesage/baseimage-gui:alpine-3.20-v4

# Install chromium and socat
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

# Copy the start script.
COPY startapp.sh /startapp.sh

# Set the name of the application.
RUN set-cont-env APP_NAME "Chromium"