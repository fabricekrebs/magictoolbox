"""
User models for authentication.

Extends Django's User model with additional fields and functionality.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """
    Custom user model extending Django's AbstractUser.

    Adds email as required field and usage tracking.
    """

    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)

    # Usage tracking
    storage_used = models.BigIntegerField(default=0, help_text="Storage used in bytes")
    api_calls_count = models.IntegerField(default=0)

    # Preferences
    timezone = models.CharField(max_length=50, default="UTC")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return self.email
