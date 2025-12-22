# Feature Specification: Async Tool Framework & Plugin System

**Feature Branch**: `001-async-tool-framework`  
**Created**: 2025-12-20  
**Status**: Draft  
**Input**: User description: "MagicToolbox is a modular web application that hosts multiple tools for file conversion, data transformation, and processing tasks, etc... It should support asynchronous task. It should be modular enough to easily add additionnal tool by keeping the same structure, layout."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Adds New Synchronous Tool (Priority: P1)

A developer needs to add a simple tool (e.g., hash generator, text formatter) that processes data instantly without heavy computation or file I/O.

**Why this priority**: This is the most common and simplest tool addition pattern. Many utility tools are synchronous and need minimal infrastructure.

**Independent Test**: Can be fully tested by creating a new tool plugin file, registering it, and verifying it appears in the tool list and processes requests correctly. Delivers immediate value without requiring async infrastructure.

**Acceptance Scenarios**:

1. **Given** a developer has a new tool concept (e.g., text case converter), **When** they create a plugin class inheriting from \`BaseTool\` with \`validate()\` and \`process()\` methods, **Then** the tool automatically registers and appears in the tools list
2. **Given** the tool is registered, **When** a user accesses the tool's URL, **Then** they see a consistent UI layout with the tool's form and instructions
3. **Given** a user submits valid input, **When** the tool processes it synchronously, **Then** results display immediately on the same page with consistent styling
4. **Given** a user submits invalid input, **When** validation runs, **Then** clear error messages appear without breaking the page layout

---

### User Story 2 - Developer Adds New Asynchronous Tool (Priority: P2)

A developer needs to add a tool that requires heavy processing (e.g., video conversion, large file manipulation, OCR) where users cannot wait for synchronous response.

**Why this priority**: While less common than simple tools, async tools are critical for file processing capabilities and require more infrastructure. This pattern enables the platform's most valuable features.

**Independent Test**: Can be tested by creating an async tool plugin, implementing Azure Function processing, and verifying the upload → process → poll → download workflow works end-to-end with status tracking.

**Acceptance Scenarios**:

1. **Given** a developer has a heavy-processing tool concept, **When** they create a tool plugin with \`process()\` returning \`(execution_id, None)\`, **Then** the system treats it as async and initiates background processing
2. **Given** an async tool is registered, **When** a user uploads a file, **Then** the file uploads to Azure Blob Storage with standardized path \`uploads/{category}/{execution_id}{ext}\`
3. **Given** a file is uploaded, **When** the system triggers the Azure Function, **Then** processing starts and database status updates from "pending" to "processing"
4. **Given** processing is in progress, **When** the user's browser polls the status endpoint every 2-3 seconds, **Then** they see real-time status updates with progress indicators
5. **Given** processing completes successfully, **When** the result is ready, **Then** user sees download button and can retrieve the processed file from \`processed/{category}/\` container
6. **Given** an async tool page loads, **When** the user views the right sidebar, **Then** they see their last 10 processing history items with download and delete actions

---

### User Story 3 - User Discovers and Uses Tools Consistently (Priority: P3)

A user wants to find available tools and use them without learning different interfaces for each tool.

**Why this priority**: User experience consistency is important but less critical than the core plugin infrastructure. However, it significantly improves user satisfaction and reduces support burden.

**Independent Test**: Can be tested by navigating through multiple tools and verifying all follow the same layout patterns, navigation structure, and interaction paradigms.

**Acceptance Scenarios**:

1. **Given** a user visits the homepage, **When** they browse available tools, **Then** they see tools organized by category (Document, Image, Video, GPS, Text, Unit Conversion)
2. **Given** a user selects any tool, **When** the page loads, **Then** they see a consistent layout: navigation bar (top), tool form (left 8 columns), history/info sidebar (right 4 columns), footer (bottom)
3. **Given** a user is on any tool page, **When** they interact with the form, **Then** all forms use Bootstrap 5 components with consistent validation feedback
4. **Given** a user completes an operation, **When** results are ready, **Then** success messages, error messages, and status indicators follow the same visual language across all tools
5. **Given** a user accesses the site from mobile, **When** viewing any tool, **Then** the responsive layout adapts appropriately (sidebar stacks below form, touch-friendly controls)

---

### Edge Cases

- What happens when a developer creates a tool with the same \`name\` as an existing tool? System should detect duplicate registration and raise a clear error during startup.
- How does the system handle if Azure Function processing times out? The database status should update to "failed" with timeout message, and user should see error notification.
- What if an async tool's Azure Function endpoint is unreachable? Upload succeeds but processing fails immediately, status shows "failed", user gets actionable error message.
- What if a user navigates away during async processing? When they return (via history or direct URL), status polling resumes automatically if execution is still processing.
- What if blob storage connection fails during upload? User receives immediate error before database record is created, can retry upload.
- How does the system prevent unauthorized access to another user's execution results? Execution IDs are UUIDs, and API endpoints validate user ownership before allowing downloads.
- What if a developer forgets to implement required methods? System raises clear error at registration time (during app startup) indicating which methods are missing.

## Requirements *(mandatory)*

### Functional Requirements

#### Core Plugin System

- **FR-001**: System MUST provide a \`BaseTool\` abstract base class that all tools inherit from
- **FR-002**: System MUST require each tool to implement \`name\`, \`display_name\`, \`description\`, \`category\`, \`supported_formats\`, \`max_file_size\` properties
- **FR-003**: System MUST require each tool to implement \`validate(input_data)\` method that returns boolean or raises ValidationError
- **FR-004**: System MUST require each tool to implement \`process(input_data)\` method that returns either \`(result_data, None)\` for sync or \`(execution_id, None)\` for async
- **FR-005**: System MUST automatically discover and register all tool plugins in \`apps/tools/plugins/\` directory at application startup
- **FR-006**: System MUST generate URL routes automatically for each registered tool following pattern \`/tools/{tool-name}/\`
- **FR-007**: System MUST generate API endpoints automatically for each tool following pattern \`/api/v1/tools/{tool-name}/process/\`
- **FR-008**: System MUST maintain a registry of all registered tools accessible via \`ToolRegistry.get_all_tools()\` and \`ToolRegistry.get_tool(name)\`

#### Asynchronous Processing

- **FR-009**: System MUST provide Azure Blob Storage integration for file uploads with containers: \`uploads\`, \`processed\`, \`temp\`
- **FR-010**: System MUST support both local development (Azurite connection string) and production (Managed Identity) blob authentication
- **FR-011**: System MUST use standardized blob naming: \`uploads/{category}/{execution_id}{ext}\` for inputs, \`processed/{category}/{execution_id}{output_ext}\` for outputs
- **FR-012**: System MUST track execution status in database with states: pending → processing → completed OR pending → processing → failed
- **FR-013**: System MUST provide status polling API endpoint \`/api/v1/executions/{execution_id}/status/\` returning JSON with status, progress, and result URL
- **FR-014**: System MUST trigger Azure Function processing via HTTP POST to \`{AZURE_FUNCTION_BASE_URL}/{category}/{action}\`
- **FR-015**: System MUST include execution metadata in Azure Function trigger: execution_id, input_blob_path, category, action, parameters
- **FR-016**: Azure Functions MUST download input from blob, process, upload result to \`processed/\` container, and update database status
- **FR-017**: Azure Functions MUST implement error handling with try/finally blocks to ensure temp file cleanup
- **FR-018**: System MUST support timeout configuration per tool category with reasonable defaults (5 min for images, 30 min for videos)

#### User Interface Consistency

- **FR-019**: System MUST use Django templates with consistent base template extending \`base.html\`
- **FR-020**: All tool pages MUST follow two-column layout: main content (8 cols), sidebar (4 cols) on desktop; stacked on mobile
- **FR-021**: All tool forms MUST use Bootstrap 5 components styled with django-crispy-forms and crispy-bootstrap5
- **FR-022**: All async tool pages MUST include history sidebar showing last 10 executions with download and delete actions
- **FR-023**: All async tool pages MUST implement status polling JavaScript that polls every 2-3 seconds while status is pending or processing
- **FR-024**: All tools MUST display consistent error messages using Django messages framework with Bootstrap alerts
- **FR-025**: System MUST provide reusable template fragments in \`templates/includes/\` for common components (navbar, footer, file upload widget, status display)
- **FR-026**: All pages MUST meet WCAG 2.1 Level AA accessibility standards with proper ARIA labels, semantic HTML, and keyboard navigation

#### Tool Discovery and Management

- **FR-027**: Homepage MUST display all registered tools organized by category with tool name, description, and icon
- **FR-028**: Each tool detail page MUST display tool description, supported formats, file size limits, and usage instructions
- **FR-029**: System MUST provide admin interface for viewing all tool executions with filtering by tool, status, and date
- **FR-030**: System MUST provide API endpoint \`/api/v1/tools/\` listing all available tools with metadata
- **FR-031**: System MUST log all tool executions with execution_id, tool_name, user, timestamp, status, and processing time
- **FR-032**: System MUST provide cleanup mechanism for old execution records and blob files (configurable retention period, default 30 days)

#### Developer Experience

- **FR-033**: System MUST provide comprehensive documentation in \`documentation/\` describing how to create new tools
- **FR-034**: System MUST provide tool template/scaffolding command to generate boilerplate for new tool
- **FR-035**: System MUST provide clear error messages when tool registration fails (missing methods, invalid configuration)
- **FR-036**: System MUST validate tool plugins at startup and refuse to start if any tool has configuration errors
- **FR-037**: System MUST support hot-reloading of tool plugins during development without server restart
- **FR-038**: System MUST provide test utilities and fixtures for testing tools in isolation

### Key Entities

- **BaseTool**: Abstract base class defining the interface all tools must implement. Contains properties (name, display_name, description, category, supported_formats, max_file_size) and methods (validate, process).

- **ToolRegistry**: Singleton registry that discovers, validates, and stores all tool instances at application startup. Provides methods to retrieve tools by name or list all tools.

- **ToolExecution**: Database model tracking async processing. Attributes include: execution_id (UUID), tool_name, user (optional), status (pending/processing/completed/failed), input_file_path, output_file_path, parameters (JSON), created_at, updated_at, completed_at, error_message.

- **Tool Category**: Enumeration of tool types: DOCUMENT, IMAGE, VIDEO, GPS, TEXT, CONVERSION. Used for organizing tools in UI and blob storage paths.

- **BlobStorageClient**: Service class managing Azure Blob Storage operations. Handles authentication (connection string vs Managed Identity), upload/download, path standardization, and cleanup.

- **AsyncTaskTrigger**: Service class responsible for triggering Azure Functions via HTTP POST. Constructs request payload with execution metadata and handles trigger failures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can add a new synchronous tool by creating a single Python file with a class inheriting from BaseTool, and the tool becomes available without modifying any routing or registration code
- **SC-002**: A developer can add a new asynchronous tool by creating a Python plugin file and an Azure Function handler, with the upload → process → poll → download workflow working automatically
- **SC-003**: Adding 10 new tools of varying types (sync and async) takes less than 2 hours on average per tool for an experienced developer
- **SC-004**: All tools maintain consistent page load times under 500ms for initial render (before any processing)
- **SC-005**: Async tool status polling completes within 3 seconds of actual status change in database
- **SC-006**: 95% of users can successfully use a new tool without reading documentation by following the consistent UI patterns
- **SC-007**: System successfully handles 50 concurrent async processing jobs without degradation
- **SC-008**: Failed async processing jobs are detected and marked as failed within 2 minutes of failure
- **SC-009**: Tool execution history is accessible within 200ms for queries returning up to 100 records
- **SC-010**: System startup with 20 registered tools completes within 10 seconds including all tool discovery and validation
- **SC-011**: Zero duplicate tool registrations or naming conflicts occur across development and production environments
- **SC-012**: All tool pages achieve 90+ Lighthouse accessibility score

## Assumptions *(mandatory)*

- **A-001**: Django 5.0+ is the web framework with Django REST Framework for APIs
- **A-002**: Bootstrap 5 is the frontend framework for consistent UI components
- **A-003**: Azure Container Apps is the deployment platform for the Django application
- **A-004**: Azure Functions (Python) with Flex Consumption plan is used for async processing
- **A-005**: Azure Blob Storage is available for file storage with three containers: uploads, processed, temp
- **A-006**: PostgreSQL (Azure Database for PostgreSQL Flexible Server) is the database
- **A-007**: Redis (Azure Cache for Redis) is available for session management and caching
- **A-008**: Authentication is Django's built-in session-based auth (user association is optional for tool execution)
- **A-009**: All file uploads are validated on both client (UX) and server (security) sides
- **A-010**: Network latency between Django app and Azure Functions is under 100ms
- **A-011**: Developers adding tools have basic Python, Django, and Azure Functions knowledge
- **A-012**: Browser support includes latest versions of Chrome, Firefox, Safari, Edge (ES6+ JavaScript)
- **A-013**: Tool plugins are Python modules, not dynamically loaded from database or external sources
- **A-014**: Each tool operates independently without dependencies on other tools
- **A-015**: Azure Function endpoints follow REST conventions and return JSON responses

## Out of Scope

- **Tool versioning**: Tools do not maintain multiple versions; updates replace existing tool implementation
- **Tool marketplace**: No public tool submission or approval workflow for third-party developers
- **Tool scheduling**: No cron-like scheduling of tool executions; all runs are user-initiated
- **Multi-step workflows**: Tools do not chain outputs; each tool is independent (user manually uses output of one tool as input to another)
- **Real-time collaboration**: No shared editing or live updates when multiple users work on same execution
- **Tool customization per user**: All users see the same tool interface; no per-user tool configuration or preferences
- **API rate limiting per tool**: Rate limiting is global per user, not specific to individual tools
- **Tool-specific billing**: No usage tracking or cost allocation per tool
- **Batch API operations**: API processes one item at a time; no batch endpoints for processing multiple items in single request
- **Tool dependencies**: System does not manage dependencies between tools or enforce execution order

## Implementation Notes

### For Developers Adding New Tools

**Synchronous Tool Example Structure**:
\`\`\`python
# apps/tools/plugins/my_tool.py
from apps.tools.base import BaseTool
from typing import Any, Dict, Tuple, Optional

class MyTool(BaseTool):
    name = "my-tool"
    display_name = "My Tool"
    description = "Brief description of what this tool does"
    category = "TEXT"  # DOCUMENT, IMAGE, VIDEO, GPS, TEXT, CONVERSION
    supported_formats = [".txt"]
    max_file_size = 10 * 1024 * 1024  # 10MB
    
    def validate(self, input_data: Dict[str, Any]) -> bool:
        # Validate input, raise ValidationError if invalid
        if not input_data.get("text"):
            raise ValidationError("Text input is required")
        return True
    
    def process(self, input_data: Dict[str, Any]) -> Tuple[Any, Optional[str]]:
        # Process synchronously, return (result, None)
        result = {"processed": input_data["text"].upper()}
        return result, None
\`\`\`

**Asynchronous Tool Example Structure**:
\`\`\`python
# apps/tools/plugins/my_async_tool.py
from apps.tools.base import BaseTool
import uuid

class MyAsyncTool(BaseTool):
    name = "my-async-tool"
    display_name = "My Async Tool"
    description = "Heavy processing tool"
    category = "VIDEO"
    supported_formats = [".mp4", ".avi"]
    max_file_size = 500 * 1024 * 1024  # 500MB
    is_async = True  # Indicates async processing
    
    def validate(self, input_file) -> bool:
        # Validate file, raise ValidationError if invalid
        return True
    
    def process(self, input_file, **params) -> Tuple[str, None]:
        # Upload to blob, return (execution_id, None)
        execution_id = str(uuid.uuid4())
        # Upload logic handled by base class
        # Trigger Azure Function handled by base class
        return execution_id, None
\`\`\`

### Frontend Template Structure

All tool templates should extend the base and follow this structure:
\`\`\`django
{% extends "base.html" %}
{% block content %}
<div class="row">
  <div class="col-md-8">
    <!-- Upload/Input Form -->
    <!-- Status Section (for async tools) -->
    <!-- Results Section -->
  </div>
  <div class="col-md-4">
    <!-- History Sidebar (for async tools) -->
    <!-- Instructions/Help -->
  </div>
</div>
{% endblock %}
\`\`\`

### Azure Function Handler Pattern

\`\`\`python
# function_app.py
@app.route(route="{category}/{action}", methods=["POST"])
def process_file(req: func.HttpRequest) -> func.HttpResponse:
    execution_id = req.get_json().get("execution_id")
    try:
        # 1. Update status to "processing"
        # 2. Download from uploads/{category}/{execution_id}
        # 3. Process file
        # 4. Upload to processed/{category}/{execution_id}
        # 5. Update status to "completed"
        # 6. Cleanup temp files
        return func.HttpResponse(json.dumps({"status": "success"}), status_code=200)
    except Exception as e:
        # Update status to "failed"
        # Cleanup temp files
        return func.HttpResponse(json.dumps({"status": "error"}), status_code=500)
\`\`\`

## Dependencies

- **D-001**: Azure Blob Storage must be provisioned with three containers: uploads, processed, temp
- **D-002**: Azure Functions app must be deployed and accessible via HTTPS
- **D-003**: Database schema must include ToolExecution table with required columns
- **D-004**: Environment variable \`AZURE_FUNCTION_BASE_URL\` must be configured
- **D-005**: Environment variables for blob storage authentication must be set (connection string for dev, Managed Identity for prod)
- **D-006**: Bootstrap 5 CSS/JS must be included in base template
- **D-007**: Django REST Framework must be installed and configured
- **D-008**: django-crispy-forms and crispy-bootstrap5 must be installed
