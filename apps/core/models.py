"""
Base models for MagicToolbox.

Provides abstract base classes with common fields and behaviors.
"""

import uuid

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating created_at and updated_at fields.

    All models should inherit from this to maintain consistent timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class UUIDModel(models.Model):
    """
    Abstract base class that provides a UUID primary key.

    Use this for models that need globally unique identifiers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted objects by default."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    """
    Abstract base class that provides soft delete functionality.

    Objects are marked as deleted with a timestamp but not removed from database.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Include soft-deleted objects

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete the object by setting deleted_at timestamp."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self):
        """Permanently delete the object from database."""
        super().delete()

    def restore(self):
        """Restore a soft-deleted object."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self) -> bool:
        """Check if object is soft-deleted."""
        return self.deleted_at is not None
