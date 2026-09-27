# syntax=docker/dockerfile:1.7
FROM golang:1.26.6-alpine@sha256:3889b425f035be855a72fb4755265311293b6d414521f0a519d819df32222d83 AS builder
WORKDIR /src
ENV CGO_ENABLED=0 \
    GOTOOLCHAIN=local
COPY go.mod main.go ./
RUN go mod tidy \
    && go build -mod=readonly -trimpath \
        -ldflags='-s -w -X github.com/caddyserver/caddy/v2.CustomVersion=v2.11.4' \
        -o /out/caddy . \
    && /out/caddy version | grep -F 'v2.11.4'

# Preserve the official v2.11.4 Alpine entrypoint, command, filesystem layout,
# and non-root runtime contract while replacing only the rebuilt executable.
FROM caddy:2-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648
RUN apk upgrade --no-cache
COPY --from=builder /out/caddy /usr/bin/caddy
RUN caddy version | grep -F 'v2.11.4'
