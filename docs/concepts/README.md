# Concepts

Core vocabulary you need before using any OCMO feature.

## In this section

| Page | What it explains |
|------|-----------------|
| [Namespaces](namespaces.md) | Isolated workspaces; how items are scoped; builtin configs |
| [Tree and items](tree-and-items.md) | Configs, templates, secrets, resolvers, folders — and how the tree path works |
| [Versions and tags](versions-and-tags.md) | Immutable versions, `latest`/`stable` reserved tags, custom tags, `@version` syntax |
| [The `_ocmo` metadata block](ocmo-metadata.md) | The `_ocmo:` key in a config file and every field it accepts |
| [Identities and access](identities-and-access.md) | OIDC users vs resolver tokens vs signed download URLs |

## Minimal mental model

```
Namespace
└── Tree (hierarchical paths)
    ├── config:   versioned YAML → resolved through pipeline → artifact
    ├── template: Jinja2 source referenced during render
    ├── secret:   encrypted YAML; values injected at resolve time
    ├── resolver: API token + config for automated consumers
    └── folder:   grouping node; can be resolved as a batch
```

A **resolve** call takes a config (or folder), runs it through the pipeline (extend → render parameters → cast → artifact), and returns a signed download URL. The pipeline is controlled by the `_ocmo` block in the config file.
