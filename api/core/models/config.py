from django.db import models, transaction
from django.db.models import Max

from .tree import TreeItem


class Config(TreeItem):
    """
    Config model - hierarchical configuration resource.

    Stores generic information and tags; version-specific data in ConfigVersion.
    """

    # Tags stored as JSONB: {tag_name: version_number}
    tags = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.namespace.name}:: Config:: {self.path}"


class Template(TreeItem):
    """
    Config model - hierarchical configuration resource.

    Stores generic information and tags; version-specific data in ConfigVersion.
    """

    # Tags stored as JSONB: {tag_name: version_number}
    tags = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.namespace.name}:: Template:: {self.path}"


class ConfigVersion(models.Model):
    """
    Immutable version snapshots.
    Each version preserves exact data and metadata at a point in time.
    All fields are immutable after creation - updates are prevented at the model level.
    """

    config = models.ForeignKey("Config", on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField(editable=False)
    data = models.TextField()  # YAML doc - immutable
    updater = models.TextField()
    updated_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("config", "version")]
        indexes = [
            models.Index(fields=["config", "version"]),
        ]
        ordering = ["config", "version"]

    def save(self, *args, **kwargs):
        """
        Override save to enforce immutability.

        ConfigVersion records are immutable after creation per Requirements 4.2.
        Only allow creation (when pk is None), prevent all updates.
        """
        if self.pk is not None:
            original = type(self).objects.get(pk=self.pk)
            if original.deleted_at is not None:
                raise ValueError("Deleted Config version can't be updated. Create a new version instead.")
            if not (self.deleted_at and self.data == ""):
                # This is an update attempt - prevent it
                raise ValueError(
                    "Config version records are immutable and cannot be updated. Create a new version instead."
                )
        else:  # Allow creation
            with transaction.atomic():
                # Get the current maximum version for THIS document
                last_version = self.__class__.objects.filter(config=self.config).aggregate(max_v=Max("version"))[
                    "max_v"
                ]
                self.version = (last_version or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.config.namespace.name}:: Config:: {self.config.path}@{self.version}"


class TemplateVersion(models.Model):
    """
    Immutable version snapshots.
    Each version preserves exact data and metadata at a point in time.
    All fields are immutable after creation - updates are prevented at the model level.
    """

    config = models.ForeignKey("Template", on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField(editable=False)
    data = models.TextField()  # Jinja2 template - immutable
    updater = models.TextField()
    updated_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("config", "version")]
        indexes = [
            models.Index(fields=["config", "version"]),
        ]
        ordering = ["config", "version"]

    def save(self, *args, **kwargs):
        """
        Override save to enforce immutability.

        ConfigVersion records are immutable after creation per Requirements 4.2.
        Only allow creation (when pk is None), prevent all updates.
        """
        if self.pk is not None:
            original = type(self).objects.get(pk=self.pk)
            if original.deleted_at is not None:
                raise ValueError("Deleted Template version can't be updated. Create a new version instead.")
            if not (self.deleted_at and self.data == ""):
                # This is an update attempt - prevent it
                raise ValueError(
                    "Template version records are immutable and cannot be updated. Create a new version instead."
                )
        else:  # Allow creation
            with transaction.atomic():
                # Get the current maximum version for THIS document
                last_version = self.__class__.objects.filter(config=self.config).aggregate(max_v=Max("version"))[
                    "max_v"
                ]
                self.version = (last_version or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.config.namespace.name}:: Template:: {self.config.path}@{self.version}"
