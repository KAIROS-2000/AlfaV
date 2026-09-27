# syntax=docker/dockerfile:1.7
FROM golang:1.26.6-alpine@sha256:3889b425f035be855a72fb4755265311293b6d414521f0a519d819df32222d83 AS gosu-builder

# gosu 1.19 tag resolves to this immutable upstream commit. Recompiling it
# removes inherited Go 1.24.6 standard-library findings without changing the
# official PostgreSQL entrypoint's privilege-drop behavior.
ENV CGO_ENABLED=0 \
    GOTOOLCHAIN=local
RUN go install -trimpath -ldflags='-d -w' \
        github.com/tianon/gosu@6456aaa0f3c854d199d0f037f068eb97515b7513 \
    && /go/bin/gosu --version \
    && /go/bin/gosu nobody true

# PostgreSQL 17.11 base, pinned to the reviewed multi-architecture digest.
FROM postgres:17@sha256:e38411452a464af89e5adadb8d223bf53b898d47d6ef918b2d58c08707350449

# The official image can lag Debian security uploads. Apply all currently
# published fixes (including util-linux) while retaining the upstream
# docker-entrypoint.sh, gosu privilege drop, CMD, and data-directory contract.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY --from=gosu-builder /go/bin/gosu /usr/local/bin/gosu
RUN gosu --version \
    && gosu nobody true \
    && postgres --version | grep -F '17.11'
