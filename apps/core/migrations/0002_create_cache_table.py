"""
Custom migration to create database cache table.

This migration creates the cache table required for Django's database-backed cache.
It runs idempotently - won't fail if the table already exists.
"""

from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    """Create the database cache table using Django's management command."""
    try:
        call_command('createcachetable', verbosity=0)
    except Exception:
        # Table might already exist, which is fine
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_cache_table,
            reverse_code=migrations.RunPython.noop,
            hints={'target_db': 'default'},
        ),
    ]
