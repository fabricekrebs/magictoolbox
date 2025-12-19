#!/usr/bin/env python
"""
Database Cache Table Migration Script

This script creates the database cache table required for Django's database-backed cache.
Run this after deploying the Redis removal changes.

Usage:
    python manage.py createcachetable

Or use this script directly:
    python scripts/create_cache_table.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import Django settings
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "magictoolbox.settings.production")

import django
django.setup()

from django.core.management import call_command
from django.db import connection

def create_cache_table():
    """Create the database cache table."""
    print("🔍 Checking for existing cache table...")
    
    # Check if table already exists
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'django_cache_table'
            );
        """)
        exists = cursor.fetchone()[0]
    
    if exists:
        print("✅ Cache table 'django_cache_table' already exists.")
        return
    
    print("📝 Creating cache table...")
    try:
        # Use Django's management command to create the cache table
        call_command('createcachetable', verbosity=2)
        print("✅ Successfully created cache table 'django_cache_table'")
        
        # Verify creation
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'django_cache_table'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            
            print("\n📊 Cache table structure:")
            for col_name, col_type in columns:
                print(f"   - {col_name}: {col_type}")
        
        print("\n✨ Migration complete!")
        
    except Exception as e:
        print(f"❌ Error creating cache table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Database Cache Table Migration")
    print("=" * 60)
    print()
    
    create_cache_table()
    
    print()
    print("=" * 60)
    print("Next steps:")
    print("1. Test cache functionality: python manage.py shell")
    print("   >>> from django.core.cache import cache")
    print("   >>> cache.set('test', 'value', 60)")
    print("   >>> cache.get('test')")
    print("2. Monitor Application Insights for any cache-related errors")
    print("=" * 60)
