# Changelog

## [0.2.0](https://github.com/damupi/gaad-cli/compare/v0.1.0...v0.2.0) (2026-11-01)


### Features

* add --version and ship the skill and agent with an install prompt ([#12](https://github.com/damupi/gaad-cli/issues/12)) ([f868d31](https://github.com/damupi/gaad-cli/commit/f868d31433684f88b8f9dead603de73ae7765945))
* notify when a newer gaad release is available ([#14](https://github.com/damupi/gaad-cli/issues/14)) ([6e18e1f](https://github.com/damupi/gaad-cli/commit/6e18e1fc3347c14dfd9e3f424933d5154e5151b3))

## 0.1.0 (2026-11-01)


### Features

* add accounts get, delete, get-data-sharing-settings, and patch commands ([9888548](https://github.com/damupi/gaad-cli/commit/9888548fb93a65c64f463e61d6c44eed5504d2c3))
* add annotations command group via GA4 Admin API v1alpha ([1d57d73](https://github.com/damupi/gaad-cli/commit/1d57d73eb5cac46b4594f819e2b38672ca45ef51))
* add BigQuery link management commands ([5750d81](https://github.com/damupi/gaad-cli/commit/5750d81bda1e89352563cc5a47fb1b04b19f2540))
* add channel-groups command group via GA4 Admin API v1alpha ([fc4a8ea](https://github.com/damupi/gaad-cli/commit/fc4a8ea69208e777e0002b425f34fccc50fbf661))
* add custom-dimensions and custom-metrics command groups with list, get, create, patch, and archive ([7e27250](https://github.com/damupi/gaad-cli/commit/7e27250273af154eda76b8f83d328860639ccaa5))
* add data-streams command group with list, get, create, patch, and delete ([57ba24b](https://github.com/damupi/gaad-cli/commit/57ba24bc7de5a9b91430f3cc93ae77b14dab22a8))
* add key-events command group with list, get, create, patch, and delete ([6dfc4c0](https://github.com/damupi/gaad-cli/commit/6dfc4c0edb3f1ed348738b1eda1f5df854f1f842))
* add properties create, delete, patch, get-data-retention-settings, and update-data-retention-settings commands ([a75c37f](https://github.com/damupi/gaad-cli/commit/a75c37fc7957e28e0a7cc3e21eae6e25c485ec4f))
* initial gaad-cli scaffold with auth, accounts, and properties ([06142e4](https://github.com/damupi/gaad-cli/commit/06142e45269beead6f6585a01b770fb76521a49f))


### Bug Fixes

* avoid 404 traceback after archiving custom dimensions and metrics ([#9](https://github.com/damupi/gaad-cli/issues/9)) ([ce96271](https://github.com/damupi/gaad-cli/commit/ce962716c0b20c33f36086fe40dc59f6f90334b2))
* copy credentials into config dir on login, handle same-file and naive datetime ([9a437c7](https://github.com/damupi/gaad-cli/commit/9a437c7b6cd941b355493547ab5b746f338c1856))
* support parent:properties filter in properties list for subproperty listing ([c57a7e0](https://github.com/damupi/gaad-cli/commit/c57a7e024634b13af9ae68114658434ad3d1128b))


### Documentation

* add annotations and channel-groups commands to README and CLAUDE.md ([ea923ae](https://github.com/damupi/gaad-cli/commit/ea923ae8941d48fa8101b168beb2e25261b8f03f))
* add README, CLAUDE.md and expand .gitignore ([1014377](https://github.com/damupi/gaad-cli/commit/10143770c368abeb9d2a45765b9f721ab910dd90))

## Changelog
