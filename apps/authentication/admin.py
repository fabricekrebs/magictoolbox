"""Admin configuration for Authentication app."""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""

    list_display = ["email", "username", "is_verified", "is_staff", "date_joined"]
    list_filter = ["is_staff", "is_superuser", "is_active", "is_verified"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Additional Info",
            {"fields": ("is_verified", "storage_used", "api_calls_count", "timezone")},
        ),
    )

    readonly_fields = ["date_joined", "last_login", "storage_used", "api_calls_count"]
