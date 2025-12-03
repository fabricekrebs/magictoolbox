#!/usr/bin/env python
"""
Create test user for MagicToolbox using Azure PostgreSQL database.
Usage: python create_test_user.py
"""
import os
import sys
import django
import getpass

# Prompt for database password
print("=== Create Test User on Azure PostgreSQL ===\n")
db_password = getpass.getpass("Enter Azure PostgreSQL password: ")

if not db_password:
    print("❌ Password is required")
    sys.exit(1)

# Set environment variables for Django
os.environ['DB_HOST'] = 'psql-westeurope-magictoolbox-dev-01.postgres.database.azure.com'
os.environ['DB_NAME'] = 'magictoolbox'
os.environ['DB_USER'] = 'magictoolbox'
os.environ['DB_PORT'] = '5432'
os.environ['DB_PASSWORD'] = db_password
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magictoolbox.settings.development')

print("\nConnecting to Azure PostgreSQL...")

try:
    # Setup Django
    django.setup()
    
    # Test database connection
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected to PostgreSQL")
        print(f"   Version: {version[0][:50]}...")
    
    # Create test user
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    email = "test@test.com"
    password = "test@test.com"
    
    print(f"\nCreating user: {email}")
    
    try:
        user = User.objects.get(email=email)
        print(f"✅ User already exists: {email}")
        print(f"   User ID: {user.id}")
        print(f"   Active: {user.is_active}")
    except User.DoesNotExist:
        user = User.objects.create_user(email=email, password=password)
        print(f"✅ Created new user: {email}")
        print(f"   User ID: {user.id}")
    
    print(f"\n=== Test Credentials ===")
    print(f"Email: {email}")
    print(f"Password: {password}")
    
    # Update .env file
    print(f"\n=== Updating .env file ===")
    
    env_content = f"""DEBUG=True
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstorageaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstorageaccount1;
USE_AZURE_FUNCTIONS_PDF_CONVERSION=True

# Azure PostgreSQL Database
DB_HOST=psql-westeurope-magictoolbox-dev-01.postgres.database.azure.com
DB_NAME=magictoolbox
DB_USER=magictoolbox
DB_PASSWORD={db_password}
DB_PORT=5432
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Updated .env file with Azure PostgreSQL credentials")
    print("\nYou can now test the PDF upload!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
