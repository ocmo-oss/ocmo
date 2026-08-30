# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) from `1.0.0` onward.
Before `1.0.0`, minor releases may include breaking API or behavior changes.

## [0.8.20]

### Docs

- **Tutorial:** end-to-end guide for installing cert-manager on Kubernetes with OCMO (`docs/tutorials/install-k8s-application/`).
- Highlighted changes related to bugs fixes below

### Fixed

- **API:** Now on folder copy/move OCMO will try to built graph of nested elements and copy them in proper order to pass creation time items reference validation. Also separate `skip_reference_validation` API option was added to skip such validation entirely
- **API:** Fixed special syntax for list items extend on resolve actually replaced list item instead of merge
- **API:** Fixed resolver cast configuration fails to merge with cast configuration from other places
- **API:** Fixed dynamic parameters wasn't propagated to nested configs on resolve with extend configuration
- **CLI:** Fixed dry-run description for several commands
- **CLI:** Now OCMO CLI has missed `mark-stable` flag for `ocmo resolve` command to mark config with `stable` tag on successful resolve
- **CLI:** Fixed `ocmo tag item` command didn't set tag (but finished with succes) when target version is not explicitly defined. Now `latest` version is used as tag target
- **Frontend:** Fixed Resolve widget didn't close on switching to another config in element tree
- **Frontend:** Add support of new `skip_reference_validation` API configuration for copy/move feature in frontend


## [0.8.19] - 2026-08-29

### Added

- Initial open-source monorepo publication: API, SDK, CLI, frontend, gateway, and documentation.
- Apache 2.0 license, contributor guidelines, and security policy.

[0.8.20]: https://github.com/ocmo-oss/ocmo/compare/v0.8.19...v0.8.20
[0.8.19]: https://github.com/ocmo-oss/ocmo/releases/tag/v0.8.19
