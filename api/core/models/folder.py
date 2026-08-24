from .tree import TreeItem


class Folder(TreeItem):
    """
    Folder model - hierarchical resource for grouping other resources.

    Stores generic information only.
    """

    def __str__(self):
        return f"{self.namespace.name}:: Folder:: {self.path}"
