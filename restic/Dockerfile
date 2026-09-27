# syntax=docker/dockerfile:1.7
FROM golang:1.26.6-alpine@sha256:3889b425f035be855a72fb4755265311293b6d414521f0a519d819df32222d83 AS builder
ARG RESTIC_VERSION=0.19.1
ARG RESTIC_SOURCE_SHA256=bb9b1a19040744d26d8a79be029d4e6b189c45ccc9d8831d7fe367d3c33df725
WORKDIR /src
ENV CGO_ENABLED=0 \
    GOTOOLCHAIN=local
RUN wget -O /tmp/restic.tar.gz \
        "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic-${RESTIC_VERSION}.tar.gz" \
    && echo "${RESTIC_SOURCE_SHA256}  /tmp/restic.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/restic.tar.gz --strip-components=1 \
    && rm /tmp/restic.tar.gz \
    && go get \
        golang.org/x/net@v0.56.0 \
        golang.org/x/text@v0.39.0 \
        google.golang.org/grpc@v1.82.1 \
    && go mod tidy \
    && version="$(cat VERSION)" \
    && go build -mod=readonly -trimpath \
        -tags 'selfupdate,disable_grpc_modules' \
        -ldflags="-s -w -X main.version=${version}" \
        -o /out/restic ./cmd/restic \
    && /out/restic version | grep -F "restic ${RESTIC_VERSION} compiled with go1.26.6"

# Keep the official v0.19.1 runtime, entrypoint, helpers, certificates, and
# supported backend tooling; replace only the statically linked Go binary.
FROM restic/restic:0.19.1@sha256:9940e6c7421ab3a21ee9fdc4e91596d04c792b600d31b102696c75cbf3ac4481
COPY --from=builder /out/restic /usr/bin/restic
RUN restic version | grep -F 'restic 0.19.1 compiled with go1.26.6'
