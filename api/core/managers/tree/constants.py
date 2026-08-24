from ...models import Config, Resolver, Secret, Template, TreeItem

_COPY_NODE_TYPES = frozenset({"config", "template", "resolver"})

_RESERVED_TAGS = {
    "config": frozenset({"latest", "stable"}),
    "template": frozenset({"latest"}),
    "secret": frozenset({"latest"}),
}

type TreeItemLike = TreeItem | Config | Template | Resolver | Secret
