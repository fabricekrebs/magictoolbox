# Data Model

**Feature**: Async Tool Framework & Plugin System  
**Date**: 2025-12-21  
**Status**: Complete

## Overview

This document defines the core entities, relationships, and validation rules for the plugin-based tool framework. The model supports both synchronous and asynchronous tool execution with comprehensive tracking and history management.

---

## Core Entities

### 1. BaseTool (Abstract Base Class)

**Description**: Abstract interface that all tool plugins must implement. Not stored in database - exists only in code.

**Attributes**:
| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| `name` | `str` | Yes | URL-safe identifier (e.g., "pdf-docx-converter") | Lowercase, hyphens only, 3-50 chars |
| `display_name` | `str` | Yes | Human-readable name (e.g., "PDF to DOCX Converter") | 3-100 chars |
| `description` | `str` | Yes | Brief tool description for UI | 10-500 chars |
| `category` | `ToolCategory` | Yes | Tool category enum | Must be valid ToolCategory |
| `supported_formats` | `list[str]` | Yes | Accepted file extensions | e.g., [".pdf", ".doc"] |
| `max_file_size` | `int` | Yes | Maximum upload size in bytes | 1KB - 500MB |
| `is_async` | `bool` | No | Whether tool uses async processing | Default: False |
| `icon` | `str` | No | CSS icon class (e.g., "bi-file-pdf") | Bootstrap Icons class |

**Methods**:
- `validate(input_data: Dict[str, Any]) -> bool`: Validates input before processing, raises `ValidationError` if invalid
- `process(input_data: Dict[str, Any]) -> Tuple[Any, Optional[str]]`: Processes input, returns `(result, None)` for sync or `(execution_id, None)` for async

**Constraints**:
- Tool names must be unique across all plugins
- At least one supported format required
- Max file size cannot exceed 500MB (platform limit)

---

### 2. ToolCategory (Enum)

**Description**: Enumeration of tool categories for organization and blob storage path standardization.

**Values**:
| Value | Display Name | Blob Path Prefix | Example Tools |
|-------|--------------|------------------|---------------|
| `DOCUMENT` | Document Processing | `document/` | PDF conversion, OCR |
| `IMAGE` | Image Tools | `image/` | Format conversion, EXIF extraction |
| `VIDEO` | Video Tools | `video/` | Rotation, format conversion |
| `GPS` | GPS & Fitness | `gps/` | GPX analyzer, GPX/KML converter |
| `TEXT` | Text Utilities | `text/` | Base64 encoder, hash generator |
| `CONVERSION` | Unit Conversion | `conversion/` | Temperature, distance, weight |

**Usage**: Determines blob storage path structure and UI grouping.

---

### 3. ToolExecution (Database Model)

**Description**: Tracks execution history for all tools (sync and async). Primary entity for status tracking and history display.

**Schema**:
```python
class ToolExecution(models.Model):
    # Primary Key
    execution_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tool Identification
    tool_name = models.CharField(max_length=100, db_index=True)
    
    # User Association (optional - anonymous users allowed)
    user = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='tool_executions')
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    
    # File Information
    input_file_name = models.CharField(max_length=255)
    input_blob_path = models.CharField(max_length=500, blank=True)  # Empty for sync tools
    output_file_name = models.CharField(max_length=255, blank=True)
    output_blob_path = models.CharField(max_length=500, blank=True)
    
    # Parameters & Results
    parameters = models.JSONField(default=dict, blank=True)  # Tool-specific input params
    result_data = models.JSONField(null=True, blank=True)  # For sync tools, stores result
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    processing_time_seconds = models.FloatField(null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'tool_executions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tool_name', 'status', '-created_at']),  # History queries
            models.Index(fields=['user', '-created_at']),  # User history
        ]
```

**Status Lifecycle**:
```
PENDING → PROCESSING → COMPLETED
                    → FAILED
                    → CANCELLED
```

**Status Values**:
| Status | Description | Terminal | User Actions Available |
|--------|-------------|----------|------------------------|
| `PENDING` | Queued for processing | No | Cancel |
| `PROCESSING` | Currently being processed | No | Cancel (best effort) |
| `COMPLETED` | Successfully completed | Yes | Download, Delete, Re-run |
| `FAILED` | Processing failed | Yes | View error, Delete, Retry |
| `CANCELLED` | User cancelled | Yes | Delete, Re-run |

**Validation Rules**:
- `execution_id`: Auto-generated UUID, immutable
- `tool_name`: Must match a registered tool's `name` attribute
- `status`: Can only transition forward (no COMPLETED → PENDING)
- `output_blob_path`: Required when status is COMPLETED (for async tools)
- `error_message`: Required when status is FAILED
- `completed_at`: Must be set when status becomes terminal (COMPLETED/FAILED/CANCELLED)
- `processing_time_seconds`: Calculated as `completed_at - created_at`

**Relationships**:
- **User → ToolExecution**: One-to-Many (optional, user can be null for anonymous)
- **ToolExecution → BaseTool**: Logical relationship via `tool_name` (not FK since tools are code, not DB)

---

### 4. ToolRegistry (Singleton Service)

**Description**: In-memory registry of all discovered tool instances. Not a database model - exists only at runtime.

**Attributes**:
```python
class ToolRegistry:
    _instance = None
    _tools: Dict[str, BaseTool] = {}  # {tool_name: tool_instance}
    _initialized: bool = False
```

**Methods**:
- `register(tool: BaseTool) -> None`: Adds tool to registry, validates uniqueness
- `get_tool(name: str) -> Optional[BaseTool]`: Retrieves tool by name
- `get_all_tools() -> List[BaseTool]`: Returns all registered tools
- `get_tools_by_category(category: ToolCategory) -> List[BaseTool]`: Filters by category
- `is_registered(name: str) -> bool`: Checks if tool exists

**Initialization**: Populated during Django's `AppConfig.ready()` phase via metaclass auto-discovery.

---

## Relationships

```
┌─────────────────┐
│     User        │
│  (auth.User)    │
└────────┬────────┘
         │ 0..*
         │ (optional)
         ▼
┌─────────────────┐         ┌──────────────┐
│ ToolExecution   │◀───────▶│  BaseTool    │
│   (Database)    │ logical │   (Code)     │
└────────┬────────┘  via    └──────────────┘
         │          tool_name
         │
         ▼
┌─────────────────┐
│  Blob Storage   │
│   (Azure)       │
│  - uploads/     │
│  - processed/   │
│  - temp/        │
└─────────────────┘
```

**Cardinalities**:
- User : ToolExecution = 1:N (one user can have many executions)
- ToolExecution : BlobFiles = 1:2 (one input, one output for async tools)
- BaseTool : ToolExecution = 1:N (one tool definition, many executions)

---

## State Transitions

### ToolExecution Status State Machine

```
                  ┌──────────┐
            ┌─────│ PENDING  │◀─────┐
            │     └──────────┘      │
            │           │           │
            │           │ Azure     │
            │           │ Function  │
            │           │ triggered │
            │           ▼           │
     User   │     ┌───────────┐    │ Retry
     Cancel │     │PROCESSING │    │
            │     └───────────┘    │
            │           │           │
            │     ┌─────┴─────┐    │
            │     │           │    │
            │     ▼           ▼    │
            │  ┌─────────┐ ┌────────┐
            └─▶│CANCELLED│ │ FAILED │──┘
               └─────────┘ └────────┘
                           (terminal)
                    │
                    │ Success
                    ▼
              ┌───────────┐
              │ COMPLETED │
              └───────────┘
               (terminal)
```

**Transition Validation**:
- PENDING → PROCESSING: Only by Azure Function trigger
- PENDING → CANCELLED: Only by user action
- PROCESSING → COMPLETED: Only by Azure Function on success
- PROCESSING → FAILED: Only by Azure Function on error or timeout
- PROCESSING → CANCELLED: Best effort (may still complete)
- FAILED → PENDING: Only via explicit retry action (creates new execution)

---

## Blob Storage Path Conventions

### Path Structure

**Input Files (Uploads)**:
```
uploads/{category}/{execution_id}{original_extension}

Examples:
uploads/document/550e8400-e29b-41d4-a716-446655440000.pdf
uploads/video/123e4567-e89b-12d3-a456-426614174000.mp4
uploads/image/7c9e6679-7425-40de-944b-e07fc1f90ae7.jpg
```

**Output Files (Processed)**:
```
processed/{category}/{execution_id}{output_extension}

Examples:
processed/document/550e8400-e29b-41d4-a716-446655440000.docx
processed/video/123e4567-e89b-12d3-a456-426614174000.mp4
processed/image/7c9e6679-7425-40de-944b-e07fc1f90ae7.png
```

**Temporary Files** (Azure Function working directory):
```
temp/{execution_id}/{filename}

Examples:
temp/550e8400-e29b-41d4-a716-446655440000/intermediate.tmp
temp/550e8400-e29b-41d4-a716-446655440000/processing.log
```

**Lifecycle Policies**:
- `uploads/`: 7 days retention (auto-delete after 7 days)
- `processed/`: 30 days retention
- `temp/`: 24 hours retention

---

## Validation Rules Summary

### Input Validation (BaseTool.validate)

**File Upload Validation**:
1. File size ≤ tool's `max_file_size` attribute
2. File extension in tool's `supported_formats` list
3. File content type matches extension (MIME type check)
4. File is not empty (size > 0 bytes)
5. Filename is valid (no path traversal characters)

**Parameter Validation** (tool-specific):
- Example (Video Rotation): `rotation` in [90, 180, 270, -90]
- Example (Image Resize): `width` and `height` must be > 0 and < 10000
- Example (PDF Converter): `preserve_layout` must be boolean

**Error Response Format**:
```json
{
  "error": "Validation failed",
  "details": [
    {
      "field": "file",
      "message": "File size exceeds maximum allowed (50MB)"
    },
    {
      "field": "rotation",
      "message": "Rotation must be one of: 90, 180, 270, -90"
    }
  ]
}
```

### Database Constraints

**ToolExecution Model**:
```python
class ToolExecution(models.Model):
    # Constraints
    class Meta:
        constraints = [
            # Status must be valid
            models.CheckConstraint(
                check=models.Q(status__in=['pending', 'processing', 'completed', 'failed', 'cancelled']),
                name='valid_status'
            ),
            # Completed executions must have completed_at timestamp
            models.CheckConstraint(
                check=~models.Q(status__in=['completed', 'failed', 'cancelled']) | models.Q(completed_at__isnull=False),
                name='terminal_status_has_completed_at'
            ),
            # Failed executions must have error message
            models.CheckConstraint(
                check=~models.Q(status='failed') | models.Q(error_message__gt=''),
                name='failed_status_has_error'
            ),
        ]
```

---

## Indexing Strategy

### Performance-Critical Queries

**1. User History Query** (most frequent):
```sql
SELECT * FROM tool_executions 
WHERE user_id = ? AND tool_name = ? 
ORDER BY created_at DESC 
LIMIT 10;
```
Index: `(user_id, tool_name, created_at DESC)`

**2. Status Polling** (high frequency during async processing):
```sql
SELECT status, output_blob_path, error_message, completed_at 
FROM tool_executions 
WHERE execution_id = ?;
```
Index: Primary key `(execution_id)` - already indexed

**3. Admin Tool Filter**:
```sql
SELECT * FROM tool_executions 
WHERE tool_name = ? AND status = ? 
ORDER BY created_at DESC;
```
Index: `(tool_name, status, created_at DESC)`

**4. Cleanup Query** (background task):
```sql
SELECT execution_id, input_blob_path, output_blob_path 
FROM tool_executions 
WHERE created_at < ? AND status IN ('completed', 'failed');
```
Index: `(created_at, status)`

### Composite Indexes

```python
class Meta:
    indexes = [
        # Primary history query optimization
        models.Index(fields=['user', 'tool_name', '-created_at'], name='idx_user_tool_history'),
        
        # Admin dashboard filtering
        models.Index(fields=['tool_name', 'status', '-created_at'], name='idx_tool_status_time'),
        
        # Cleanup job optimization
        models.Index(fields=['created_at', 'status'], name='idx_cleanup_candidates'),
        
        # Individual field indexes (for general queries)
        models.Index(fields=['tool_name'], name='idx_tool_name'),
        models.Index(fields=['status'], name='idx_status'),
    ]
```

---

## Data Migration Strategy

### Initial Migration

**File**: `apps/tools/migrations/0001_initial.py`

Creates:
- `tool_executions` table with all fields
- Composite indexes
- Check constraints
- Foreign key to `auth_user` (nullable)

### Schema Evolution

**Adding New Fields** (backward compatible):
```python
# Example: Adding progress_percentage field
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='toolexecution',
            name='progress_percentage',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
```

**Modifying Enums** (requires data migration):
```python
# Example: Adding new status value
class Migration(migrations.Migration):
    operations = [
        # Step 1: Add new status to choices (doesn't affect DB)
        # Step 2: Update check constraint to include new status
        migrations.RemoveConstraint(
            model_name='toolexecution',
            name='valid_status',
        ),
        migrations.AddConstraint(
            model_name='toolexecution',
            constraint=models.CheckConstraint(
                check=models.Q(status__in=['pending', 'processing', 'completed', 'failed', 'cancelled', 'retrying']),
                name='valid_status'
            ),
        ),
    ]
```

---

## Summary

**Key Entities**:
1. **BaseTool** (Abstract Class) - Tool plugin interface
2. **ToolCategory** (Enum) - Organization and path structure
3. **ToolExecution** (Model) - Execution tracking and history
4. **ToolRegistry** (Singleton) - Runtime tool discovery

**Core Relationships**:
- User ➔ ToolExecution (1:N, optional)
- ToolExecution ➔ BaseTool (logical via tool_name)
- ToolExecution ➔ Blob Storage (file paths)

**Critical Validation**:
- File size and format validation
- Status transition enforcement
- Path convention compliance
- Index optimization for performance

**Next Steps**:
- ✅ Data model complete
- ⏭️ Generate API contracts (OpenAPI spec)
- ⏭️ Write quickstart guide for developers
