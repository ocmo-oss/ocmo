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

One of the main ideas of OCMO that we should separate config data from exact syntax to which it should be rendered. By this reason all OCMO configs items are defined exclusively in YAML (or JSON that is subset of YAML) and later it is possible to [resolve config](../features/resolving/README.md) to required format using [cast](../features/resolving/cast.md) (for formats the easily mapped from YAML) or [render](../features/resolving/render.md) features (for complex syntax cases. E.g. Nginx config).

Another core principle that configuration that define how config should be handled on resolve (parameters, extend, cast, render, name, propagation, etc) should leave right next to config data. Thats why config might have optional `_ocmo` block that define all this configuration.

As result we might create following items types in namespace:

```
Namespace
└── Tree (hierarchical paths)
    ├── config:   versioned YAML → resolved through pipeline → artifact
    ├── template: Jinja2 source referenced during render
    ├── secret:   encrypted YAML; values injected at resolve time
    ├── resolver: API token + config for automated consumers
    └── folder:   grouping node; can be resolved as a batch. Folder created and removed automatically
```

A **resolve** call takes a config (or folder), runs it through the pipeline (extend → evaluate parameters → cast/render tempate → artifact), and returns a signed download URL. 
