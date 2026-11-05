# syntax=docker/dockerfile:1.7
FROM ubuntu:24.04

ARG TARGETARCH
ARG JOBS=4
ENV DEBIAN_FRONTEND=noninteractive \
    PIXI_HOME=/opt/pixi \
    PIXI_NO_PATH_UPDATE=1 \
    PIXI_CACHE_DIR=/opt/cache/pixi \
    PIP_CACHE_DIR=/opt/cache/pip \
    CARGO_HOME=/opt/cache/cargo \
    STAT_PIXI=/opt/stat-pixi \
    STAT_DEPS=/opt/stat-deps \
    STAT_BASELINE=/opt/stat-baseline \
    PATH=/opt/pixi/bin:/opt/stat-deps/bin:/opt/stat-pixi/.pixi/envs/default/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git xz-utils bzip2 tar gzip file binutils \
    && rm -rf /var/lib/apt/lists/*

COPY ci-image/pixi.toml /opt/stat-pixi/pixi.toml
COPY ci-image/pixi.lock /opt/stat-pixi/pixi.lock
RUN curl -fsSL https://pixi.sh/install.sh | sh \
    && pixi install --locked --manifest-path /opt/stat-pixi/pixi.toml

COPY ci-image/revisions.env ci-image/install-deps.sh ci-image/stat-env.sh /opt/stat-ci/
RUN --mount=type=cache,target=/opt/stat-downloads \
    JOBS="$JOBS" bash /opt/stat-ci/install-deps.sh sources
RUN JOBS="$JOBS" bash /opt/stat-ci/install-deps.sh libiberty
RUN JOBS="$JOBS" bash /opt/stat-ci/install-deps.sh python-tools
RUN JOBS="$JOBS" bash /opt/stat-ci/install-deps.sh pystack
RUN JOBS="$JOBS" bash /opt/stat-ci/install-deps.sh dyninst
RUN JOBS="$JOBS" bash /opt/stat-ci/install-deps.sh graphlib
RUN JOBS="$JOBS" bash /opt/stat-ci/install-deps.sh mrnet
RUN JOBS="$JOBS" bash /opt/stat-ci/install-deps.sh launchmon
COPY ci-image/build-stat.sh /opt/stat-ci/build-stat.sh
RUN JOBS="$JOBS" bash /opt/stat-ci/build-stat.sh /opt/stat-sources/STAT /opt/stat-baseline
COPY ci-image/validate.sh /opt/stat-ci/validate.sh
RUN bash /opt/stat-ci/validate.sh /opt/stat-baseline

ENV BASH_ENV=/opt/stat-ci/stat-env.sh
WORKDIR /workspace
CMD ["bash"]
