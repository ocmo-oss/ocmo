# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) from `1.0.0` onward.
Before `1.0.0`, minor releases may include breaking API or behavior changes.

## [0.8.20] - Unreleased

### Added

- **Tutorial:** end-to-end guide for installing cert-manager on Kubernetes with OCMO (`docs/tutorials/install-k8s-application/`).
- **API:** topological ordering when copying subtrees with `_ocmo` cross-references; `skip_reference_validation` on copy.
- **CLI:** `resolve --mark-stable`; tag-to-version resolution for `get version` / `tag item`; operations metadata helper.
- **Frontend:** folder `describe` support in tree UI (FolderView, LocationDialog).
- **Docs:** extend/parameters clarifications, product comparison note, README/tutorial index updates.

### Fixed

- **API:** config save-time reference validation and deep-merge list-index handling; resolver auth response includes hook commands.
- **CLI:** dry-run confirmation for namespace delete; non-interactive `copy item` documented with `--yes` in tutorial.
- **Tutorial:** `copy item --yes` for CI shells; unset OIDC env vars before resolver `OCMO_TOKEN`.

## [0.8.19] - 2026-08-29

### Added

- Initial open-source monorepo publication: API, SDK, CLI, frontend, gateway, and documentation.
- Apache 2.0 license, contributor guidelines, and security policy.

[0.8.20]: https://github.com/ocmo-oss/ocmo/compare/v0.8.19...v0.8.20
[0.8.19]: https://github.com/ocmo-oss/ocmo/releases/tag/v0.8.19
