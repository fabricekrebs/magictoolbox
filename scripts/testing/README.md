# Testing Scripts

This directory contains various testing and development helper scripts for MagicToolbox.

## Scripts

### Database & User Management
- **`create_test_user.py`** - Creates a test user in Azure PostgreSQL database
  - Usage: `python create_test_user.py`
  - Prompts for database password
  - Creates test user with email: test@test.com

### Azure Functions Testing
- **`test_azure_functions_pdf.py`** - Integration test for PDF to DOCX conversion via Azure Functions
  - Tests the complete async workflow: upload → Azure Function processing → result retrieval
  - Requires deployed Azure environment
  - Usage: `python test_azure_functions_pdf.py`

- **`test_upload_demo.py`** - Simple upload test for Django API
  - Tests PDF to DOCX conversion via Django API
  - Usage: `python test_upload_demo.py`

### Local Development Tools
- **`upload_to_azurite.py`** - Uploads files to local Azurite storage emulator for testing blob triggers
  - Usage: `python upload_to_azurite.py <source_file> [target_filename]`
  - Requires Azurite running locally

- **`setup_local_storage.py`** - Sets up blob storage containers in Azurite
  - Creates `uploads` and `processed` containers
  - Creates blob path structure (uploads/pdf/, processed/docx/)
  - Usage: `python setup_local_storage.py`

- **`function_app_simple_test.py`** - Simplified Azure Function for blob trigger testing
  - Minimal test to validate blob trigger functionality
  - Copy to `function_app/function_app.py` for testing

- **`validate_function.py`** - Static validation of Azure Function code
  - Checks syntax, imports, and structure without running
  - Usage: `python validate_function.py`

## Prerequisites

Most scripts require:
- Python 3.12+
- Virtual environment activated (`.venv`)
- Dependencies installed: `pip install -r requirements/development.txt`
- Azure credentials configured (for cloud testing)
- Azurite running (for local testing)

## Test Fixtures

Test files (like `demo_file.pdf`) are located in `tests/fixtures/`.
