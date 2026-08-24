from django.contrib.postgres.indexes import GistIndex
from django.db import models
from tree_queries.models import TreeNode


class TreeItem(TreeNode):
    """The 'Node' that holds the tree logic."""

    name = models.CharField(max_length=255)
    path = models.CharField(max_length=4096)
    namespace = models.ForeignKey("core.Namespace", on_delete=models.CASCADE, related_name="tree")
    description = models.TextField(max_length=4096)
    node_type = models.CharField(max_length=255)
    author = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("namespace", "path")]
        indexes = [
            GistIndex(
                fields=["namespace", "path"],
                name="treeitem_path_gist_idx",
                opclasses=["gist_int8_ops", "gist_text_ops"],
            ),
        ]
        ordering = ["path"]

    def __str__(self):
        return f"{self.namespace.name}:: {self.node_type.title()}:: {self.path}"
