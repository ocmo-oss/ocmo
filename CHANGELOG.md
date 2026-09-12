# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) from `1.0.0` onward.
Before `1.0.0`, minor releases may include breaking API or behavior changes.

## [0.8.23]

### Added

- **[feat] API:** `skip_missing` on extend config references — optional sources may be absent; replicate with a missing optional base yields empty outputs.
- **[feat] CLI:** exit code `10` when resolve produces empty output.
- **[feat] Frontend:** object-form extend completion snippets and narrowed URI reference scopes (configs for extend/validation/propagation, templates for render).
- **[feat] Frontend:** larger completion documentation panel for suggest items.

### Fixed

- **[fix] Frontend:** suppress `_ocmo` property suggestions when the typed key prefix is invalid on an empty document.
- **[fix] Frontend:** URI suggestions for scalar extend refs after an object-form array item.
- **[fix] Frontend:** do not suggest array items before typing `-`.
- **[fix] Frontend:** nested anchor warning in tree folder labels.
- **[fix] Docker/HMR:** gateway frontend upstream env for Vite dev server after container recreate.

### Changed

- **[chore] Docs:** extend `skip_missing`, CLI exit codes, and resolve troubleshooting notes.

## [0.8.22]

### Changed (breaking)

- **[feat] Output naming:** `_ocmo.name` is evaluated after extend merge using `{.selector}` placeholders (merged data + `{._ocmo.*}` metadata). `{!param}` in names is rejected. Extend `replicate` no longer auto-suffixes; dedup adds `-1`, `-2` only on name collisions.

### Added

- **[feat] API:** name-owner rules per extend mode (`stack`, `broadcast`, `zip`, `replicate`) and render precedence documented in `docs/features/resolving/output-naming.md`.
- **[feat] Frontend:** `_ocmo.name` metadata placeholder autocomplete in the YAML editor.
- **[feat] Frontend:** double-click the current tree item to collapse all branches except the path to it.
- **[feat] Frontend:** compact tree header with whole-tree reload control.
- **[chore] Smoke:** naming coverage for plain, extend, render, and extend+render scenarios.

### Fixed

- **[fix] API:** extend+render resolve uses extend-resolved `_ocmo.name` when the template has no `# ocmo.name:` header (instead of always using the template filename leaf).

## [0.8.21]

### Changed (breaking)

- **`_ocmo.extend.mode` renamed:** `accumulate` → `stack`, `distribute` → `broadcast`, `align` → `zip`. Added `replicate`.
- **`_ocmo.render.mode` renamed:** `distribute` → `broadcast`, `align` → `zip`. Added `replicate`.
- **Output naming:** `_ocmo.name` uses deferred `{.selector}` placeholders (merged data + `{._ocmo.*}` metadata). `{!param}` in names is rejected. Extend `replicate` no longer auto-suffixes; dedup adds `-1`, `-2` only on name collisions.

Legacy mode values are no longer accepted.

### Added

- **`extend.replicate`:** merge one base config with each element at `by` (1 × N outputs).
- **`render.replicate`:** render one template once per element at `by`.

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

[0.8.22]: https://github.com/ocmo-oss/ocmo/compare/v0.8.21...v0.8.22
[0.8.21]: https://github.com/ocmo-oss/ocmo/compare/v0.8.20...v0.8.21
[0.8.20]: https://github.com/ocmo-oss/ocmo/compare/v0.8.19...v0.8.20
[0.8.19]: https://github.com/ocmo-oss/ocmo/releases/tag/v0.8.19
