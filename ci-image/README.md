# Local STAT CI image

This Ubuntu image preinstalls the Pixi toolchain and STAT native dependencies in
`/opt/stat-deps`. It builds a pinned upstream STAT baseline in
`/opt/stat-baseline`; the Pixi environment is in `/opt/stat-pixi`. The checkout
under test can be mounted at `/workspace` and built into a separate prefix.

```sh
rdctl start --application.start-in-background --container-engine.name docker --kubernetes.enabled=false
export DOCKER_HOST="unix://$HOME/.rd/docker.sock"
docker buildx build --platform linux/arm64 --load -t stat-ci:arm64 -f ci-image/Dockerfile .
docker run --rm --platform linux/arm64 stat-ci:arm64 bash /opt/stat-ci/validate.sh
```

Build a checked-out commit without changing the baseline:

```sh
docker run --rm --platform linux/arm64 \
  -v "$PWD:/workspace:ro" stat-ci:arm64 \
  bash -c 'bash /opt/stat-ci/build-stat.sh /workspace /tmp/stat-under-test && bash /opt/stat-ci/validate.sh /tmp/stat-under-test'
```

`ci-image/revisions.env` records the source commits. The dependency manifest
comes from `scripts/install-stat-server.sh` in STAT-EMEA-MAIN-DEVEL. No image
publication or workflow update is part of this local experiment. ARM64 was
built and validated locally on 2026-11-05; AMD64 remains to be tested later.
