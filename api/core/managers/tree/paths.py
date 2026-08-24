from ._common import *


class TreePathMixin:
    def _validate_path_conflicts(self):
        query_filter = Q()
        for sub_path in self.breadcrumbs[:-1]:
            query_filter |= Q(namespace=self.namespace, path=sub_path) & ~Q(node_type="folder")
        query_filter |= Q(namespace=self.namespace, path=self.path)

        conflict_paths = TreeItem.objects.filter(query_filter)
        if conflict_paths:
            raise ConflictPathsDetected(
                "Item by path "
                f"{self.path} can't be created since it conflict with existing item(s): "
                f"{', '.join(str(el) for el in conflict_paths)}"
            )

    def _get_parent_by_path(self, path):
        path_segments = path.strip("/").split("/")
        if len(path_segments) <= 1:
            return None
        parent_path = "/".join(path_segments[:-1])
        try:
            return TreeItem.objects.get(namespace=self.namespace, path=parent_path)
        except TreeItem.DoesNotExist:
            raise ValidationError(f"Parent path {parent_path} does not exist.")

    def _make_sure_path_exists(self):
        parents = []
        parent = None
        actor = self._actor_identity()
        for sub_path in self.breadcrumbs[:-1]:
            try:
                parent, _ = Folder.objects.update_or_create(
                    namespace=self.namespace,
                    path=sub_path,
                    defaults={
                        "name": sub_path.split("/")[-1],
                        "parent": parent,
                        "node_type": "folder",
                        "author": actor,
                        "description": "",
                    },
                )
                parents.append(parent)
            except IntegrityError:
                pass
        return parents
