# Tasks: Async Tool Framework & Plugin System

**Input**: Design documents from `/specs/001-async-tool-framework/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Constitution Compliance**: This task list follows MagicToolbox Constitution v1.0.0 principles:
- **Test-First Development (Principle II)**: Tests written and failing BEFORE implementation (TDD workflow)
- **Code Quality (Principle I)**: Type hints, PEP 8 compliance, 80%+ coverage
- **UX Consistency (Principle III)**: Bootstrap 5, two-column layouts, WCAG 2.1 AA accessibility
- **Performance (Principle IV)**: Async patterns, caching, query optimization, indexed queries
- **Security (Principle V)**: Validation, Azure Key Vault, Managed Identity, rate limiting

**Tests**: Test tasks included per TDD requirement (Constitution Principle II)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create apps/tools/ Django app structure with __init__.py, apps.py, models.py, views.py, urls.py
- [X] T002 [P] Add apps.tools to INSTALLED_APPS in magictoolbox/settings/base.py
- [X] T003 [P] Create apps/tools/plugins/ directory with __init__.py for plugin auto-discovery
- [X] T004 [P] Create apps/tools/services/ directory for BlobStorageClient and AsyncTaskTrigger
- [X] T005 [P] Create templates/tools/ directory with subdirectories: includes/, and tool-specific templates
- [X] T006 [P] Create static/js/ files: status-poller.js and history-manager.js for async UI
- [X] T007 [P] Install Python dependencies: azure-storage-blob, azure-identity, django-crispy-forms, crispy-bootstrap5
- [X] T008 Configure Black formatter (line length 100) and isort in pyproject.toml
- [X] T009 [P] Setup pytest-django configuration in pytest.ini with test discovery paths

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T010 Create BaseTool abstract base class in apps/tools/base.py with metaclass for auto-registration
- [X] T011 Create ToolRegistry singleton in apps/tools/registry.py with register(), get_tool(), get_all_tools() methods
- [X] T012 Create ToolExecution model in apps/tools/models.py with UUID primary key, status choices, JSON parameters field
- [X] T013 Add database indexes to ToolExecution model: (tool_name, status, -created_at), (user, -created_at)
- [X] T014 Create and run Django migration for ToolExecution model: python manage.py makemigrations tools
- [X] T015 Create BlobStorageClient service in apps/tools/services/blob_storage.py with upload_file(), download_file(), delete_file() methods
- [X] T016 Create AsyncTaskTrigger service in apps/tools/services/async_task.py with trigger_function() method for HTTP POST to Azure Functions
- [X] T017 Add ToolExecution serializer in apps/tools/serializers.py using Django REST Framework ModelSerializer
- [X] T018 Create base template templates/base.html with Bootstrap 5 CDN, navbar, footer, messages includes
- [X] T019 [P] Create reusable template fragments in templates/tools/includes/: upload_form.html, status_section.html, history_sidebar.html, instructions.html
- [X] T020 Create URL patterns in apps/tools/urls.py with dynamic tool route generation from registry
- [X] T021 Register tools URLs in apps/api/v1/urls.py under /api/v1/tools/ prefix
- [X] T022 [P] Add AZURE_FUNCTION_BASE_URL and AZURE_STORAGE_ACCOUNT_NAME to settings with environment variable loading via python-decouple
- [X] T023 [P] Configure CORS settings in magictoolbox/settings/base.py for API access
- [X] T024 [P] Setup Azure Key Vault client in magictoolbox/settings/production.py using DefaultAzureCredential

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Developer Adds New Synchronous Tool (Priority: P1) 🎯 MVP

**Goal**: Enable developers to add synchronous tools (e.g., Base64 encoder, hash generator) with minimal code by creating a single plugin file that auto-registers

**Independent Test**: Create a test synchronous tool plugin, verify it appears in /api/v1/tools/ endpoint, access its web UI at /tools/{tool-name}/, submit input, receive immediate result

### Tests for User Story 1 (TDD - Write FIRST, ensure FAIL before implementation)

- [X] T025 [P] [US1] Unit test for BaseTool validation in tests/unit/tools/test_base_tool.py - test validate() raises ValidationError on invalid input
- [X] T026 [P] [US1] Unit test for BaseTool process() in tests/unit/tools/test_base_tool.py - test synchronous tools return (result, None)
- [X] T027 [P] [US1] Unit test for ToolRegistry.register() in tests/unit/tools/test_registry.py - test duplicate name raises error
- [X] T028 [P] [US1] Unit test for ToolRegistry.get_tool() in tests/unit/tools/test_registry.py - test retrieval by name
- [X] T029 [P] [US1] Integration test for tool API endpoint in tests/integration/test_tool_api.py - POST to /api/v1/tools/{name}/process/ returns 200 with result
- [X] T030 [P] [US1] Integration test for tool web UI in tests/integration/test_tool_views.py - GET /tools/{name}/ returns 200 with rendered template

### Implementation for User Story 1

- [X] T031 [P] [US1] Implement BaseTool.__init__() and property getters in apps/tools/base.py
- [X] T032 [P] [US1] Implement ToolMeta metaclass in apps/tools/base.py for automatic registration on class definition
- [X] T033 [US1] Implement BaseTool.validate() abstract method signature with type hints in apps/tools/base.py
- [X] T034 [US1] Implement BaseTool.process() abstract method signature with type hints returning Tuple[Any, Optional[str]] in apps/tools/base.py
- [X] T035 [US1] Implement ToolRegistry._instance singleton pattern in apps/tools/registry.py
- [X] T036 [US1] Implement ToolRegistry.register() with duplicate name checking in apps/tools/registry.py
- [X] T037 [P] [US1] Implement ToolRegistry.get_tool() with name lookup in apps/tools/registry.py
- [X] T038 [P] [US1] Implement ToolRegistry.get_all_tools() returning list in apps/tools/registry.py
- [X] T039 [P] [US1] Implement ToolRegistry.get_tools_by_category() with filtering in apps/tools/registry.py
- [X] T040 [US1] Create ToolListView in apps/tools/views.py to display all registered tools organized by category
- [X] T041 [US1] Create ToolDetailView in apps/tools/views.py for individual tool UI (generic template or tool-specific)
- [X] T042 [US1] Create ToolProcessView (DRF APIView) in apps/tools/views.py to handle POST requests for sync tools
- [X] T043 [US1] Add URL pattern generation function in apps/tools/urls.py that iterates ToolRegistry and creates routes
- [X] T044 [US1] Create templates/tools/tool_list.html with category cards and tool links
- [X] T045 [US1] Create templates/tools/tool_detail.html as generic template for sync tools with form submission
- [X] T046 [P] [US1] Add input validation in ToolProcessView calling tool.validate() before tool.process()
- [X] T047 [P] [US1] Add error handling in ToolProcessView to catch ValidationError and return 400 with details
- [X] T048 [US1] Create example synchronous tool: apps/tools/plugins/base64_encoder.py with name, display_name, category, validate(), process()
- [X] T049 [US1] Create templates/tools/base64_encoder.html with text input form and result display area
- [X] T050 [US1] Add structured logging with emoji prefixes in ToolProcessView for sync tool execution
- [X] T051 [US1] Update quickstart.md with verified synchronous tool example (Base64 encoder)

**Checkpoint**: At this point, User Story 1 should be fully functional - developers can add sync tools with single file creation

---

## Phase 4: User Story 2 - Developer Adds New Asynchronous Tool (Priority: P2)

**Goal**: Enable developers to add async tools (e.g., video rotation, PDF conversion) that upload to blob storage, trigger Azure Functions, and poll status until completion

**Independent Test**: Create a test async tool plugin, upload file, verify blob upload to uploads/ container, check status polling returns pending→processing→completed, download result from processed/ container

### Tests for User Story 2 (TDD - Write FIRST, ensure FAIL before implementation)

- [X] T052 [P] [US2] Unit test for BlobStorageClient.upload_file() in tests/unit/tools/test_blob_storage.py with mocked BlobServiceClient
- [X] T053 [P] [US2] Unit test for BlobStorageClient.download_file() in tests/unit/tools/test_blob_storage.py with mocked blob download
- [X] T054 [P] [US2] Unit test for AsyncTaskTrigger.trigger_function() in tests/unit/tools/test_async_task.py with mocked requests.post
- [X] T055 [P] [US2] Integration test for async tool execution in tests/integration/test_async_tools.py - POST creates ToolExecution with status=pending
- [X] T056 [P] [US2] Integration test for status polling in tests/integration/test_execution_status.py - GET /api/v1/executions/{id}/status/ returns current status
- [X] T057 [P] [US2] Contract test for Azure Function request in tests/contract/test_azure_function_contract.py - verify request JSON schema
- [X] T058 [P] [US2] E2E test for complete async workflow in tests/e2e/test_async_workflow.py with Azurite and local functions (marked @pytest.mark.e2e)

### Implementation for User Story 2

- [X] T059 [P] [US2] Implement BlobStorageClient.__init__() with DefaultAzureCredential or connection string in apps/tools/services/blob_storage.py
- [X] T060 [P] [US2] Implement BlobStorageClient.get_blob_service_client() factory method in apps/tools/services/blob_storage.py
- [X] T061 [US2] Implement BlobStorageClient.upload_file() with container/blob path, return blob URL in apps/tools/services/blob_storage.py
- [X] T062 [US2] Implement BlobStorageClient.download_file() with blob path, return local temp file path in apps/tools/services/blob_storage.py
- [X] T063 [P] [US2] Implement BlobStorageClient.delete_file() for cleanup in apps/tools/services/blob_storage.py
- [X] T064 [US2] Implement AsyncTaskTrigger.trigger_function() with HTTP POST to {base_url}/{category}/{action} in apps/tools/services/async_task.py
- [X] T065 [US2] Add retry logic with exponential backoff in AsyncTaskTrigger.trigger_function() using tenacity library
- [X] T066 [US2] Create ExecutionStatusView (DRF APIView) in apps/tools/views.py for GET /api/v1/executions/{id}/status/
- [X] T067 [US2] Create ExecutionDownloadView in apps/tools/views.py for GET /api/v1/executions/{id}/download/ with blob streaming
- [X] T068 [US2] Create ExecutionListView (DRF ListAPIView) in apps/tools/views.py for GET /api/v1/executions/?toolName={name}&limit=10
- [X] T069 [US2] Create ExecutionDeleteView (DRF DestroyAPIView) in apps/tools/views.py for DELETE /api/v1/executions/{id}/ with blob cleanup
- [X] T070 [US2] Add URL patterns in apps/api/v1/urls.py for execution endpoints: status, download, list, delete
- [X] T071 [US2] Update ToolProcessView to detect async tools (is_async=True) and branch to async workflow in apps/tools/views.py
- [X] T072 [US2] Implement async workflow in ToolProcessView: create execution record, upload to blob, trigger function, return execution_id
- [X] T073 [US2] Create JavaScript StatusPoller class in static/js/status-poller.js with exponential backoff (2s → 5s max)
- [X] T074 [P] [US2] Create JavaScript HistoryManager class in static/js/history-manager.js for loading/refreshing history sidebar
- [X] T075 [US2] Update templates/tools/includes/status_section.html with progress bar, elapsed time display, polling script integration
- [X] T076 [US2] Update templates/tools/includes/history_sidebar.html with last 10 executions, download buttons, delete buttons with confirmation modal
- [X] T077 [US2] Create example async tool: apps/tools/plugins/video_rotation.py with is_async=True, blob upload, function trigger
- [X] T078 [US2] Create templates/tools/video_rotation.html with file upload form, rotation selector, status section, history sidebar
- [X] T079 [US2] Create Azure Function handler in function_app/video/rotate.py with ffmpeg video rotation logic
- [X] T080 [US2] Implement Azure Function generic handler pattern in function_app/function_app.py with route="{category}/{action}"
- [X] T081 [US2] Add blob download logic in Azure Function: download from uploads/, process, upload to processed/ in function_app/video/rotate.py
- [X] T082 [US2] Add database status update logic in Azure Function via HTTP PATCH to Django API in function_app/shared/database_client.py
- [X] T083 [US2] Add temp file cleanup in Azure Function try/finally block in function_app/video/rotate.py
- [X] T084 [P] [US2] Add comprehensive logging with emoji prefixes in Azure Function (🚀📥⚙️📤✅❌🗑️) in function_app/video/rotate.py
- [X] T085 [US2] Configure function timeout in function_app/host.json: 15 minutes default, category-specific overrides
- [X] T086 [US2] Add Azure Function authentication: ANONYMOUS for local, FUNCTION level for production in function_app/function_app.py
- [X] T087 [US2] Update quickstart.md with verified asynchronous tool example (Video rotation)
- [X] T088 [P] [US2] Create Bicep template infra/bicep/storage.bicep for blob storage with 3 containers and lifecycle policies
- [X] T089 [P] [US2] Create Bicep template infra/bicep/functions.bicep for Azure Functions with Managed Identity and VNet integration

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - sync and async tools fully functional

---

## Phase 5: User Story 3 - User Discovers and Uses Tools Consistently (Priority: P3)

**Goal**: Provide users with intuitive tool discovery, consistent UI/UX across all tools, and responsive design for mobile/tablet/desktop

**Independent Test**: Navigate from homepage to any tool, verify consistent layout (navbar, 8/4 column split, sidebar), test on mobile viewport, verify all forms use Bootstrap styling, check accessibility with screen reader

### Tests for User Story 3 (TDD - Write FIRST, ensure FAIL before implementation)

- [ ] T090 [P] [US3] UI test for homepage tool listing in tests/ui/test_homepage.py - verify all categories and tools display
- [ ] T091 [P] [US3] UI test for consistent layout in tests/ui/test_tool_layouts.py - verify all tools have navbar, footer, 8/4 columns
- [ ] T092 [P] [US3] Accessibility test with axe-core in tests/accessibility/test_wcag_compliance.py - verify WCAG 2.1 AA compliance
- [ ] T093 [P] [US3] Responsive design test in tests/ui/test_responsive.py - verify mobile viewport stacks sidebar below form

### Implementation for User Story 3

- [X] T094 [P] [US3] Create templates/includes/navbar.html with Bootstrap navbar component, tool dropdown by category
- [X] T095 [P] [US3] Create templates/includes/footer.html with copyright, links, social icons
- [X] T096 [P] [US3] Create templates/includes/messages.html to display Django messages as Bootstrap alerts
- [X] T097 [US3] Update templates/base.html to include navbar, messages, footer, responsive meta tags
- [X] T098 [US3] Enhance templates/tools/tool_list.html with category tabs (Bootstrap nav-tabs), tool cards with icons
- [X] T099 [US3] Add search/filter functionality to tool_list.html with JavaScript filtering by name or category
- [X] T100 [US3] Update ToolListView in apps/tools/views.py to pass tools grouped by category to template
- [X] T101 [P] [US3] Create static/css/custom.css with project-specific styles maintaining Bootstrap theme
- [X] T102 [P] [US3] Add CSS custom properties for brand colors, spacing, responsive breakpoints in static/css/custom.css
- [X] T103 [US3] Implement responsive grid in templates/tools/tool_detail.html: .col-md-8 + .col-md-4 (stacks on mobile)
- [X] T104 [US3] Add ARIA labels to all form inputs in templates/tools/includes/upload_form.html
- [X] T105 [P] [US3] Add role="alert" aria-live="polite" to status section for screen reader announcements
- [ ] T106 [P] [US3] Test keyboard navigation: tab order, escape to close modals, enter to submit forms
- [ ] T107 [US3] Verify color contrast ratios ≥4.5:1 for all text using Chrome DevTools Accessibility panel
- [X] T108 [US3] Add loading spinners (Bootstrap spinner component) during file upload and status polling
- [ ] T109 [US3] Add toast notifications (Bootstrap toast) for success/error messages with auto-dismiss
- [ ] T110 [P] [US3] Optimize page load: lazy load history sidebar, defer non-critical JavaScript
- [ ] T111 [P] [US3] Add meta tags for SEO: description, keywords, Open Graph tags in templates/base.html
- [ ] T112 [US3] Create custom 404 page template in templates/errors/404.html with Bootstrap styling
- [ ] T113 [P] [US3] Create custom 500 page template in templates/errors/500.html with user-friendly message
- [ ] T114 [US3] Test all tools on Chrome, Firefox, Safari, Edge browsers for compatibility
- [ ] T115 [US3] Test all tools on iOS Safari and Android Chrome for mobile compatibility

**Checkpoint**: All user stories should now be independently functional with consistent, accessible UI

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T116 [P] Add rate limiting middleware in apps/core/middleware.py using Django cache framework (100 req/15min per IP)
- [ ] T117 [P] Configure DRF throttling in magictoolbox/settings/base.py: AnonRateThrottle and UserRateThrottle
- [ ] T118 [P] Add request logging middleware in apps/core/middleware.py capturing execution_id, tool_name, duration
- [ ] T119 Setup structlog in magictoolbox/settings/base.py for structured JSON logging in production
- [ ] T120 Configure Application Insights in magictoolbox/settings/production.py with OpenTelemetry integration
- [ ] T121 [P] Add Sentry integration for error tracking in magictoolbox/settings/production.py (optional)
- [ ] T122 Create management command python manage.py cleanup_executions for deleting old records and blobs
- [ ] T123 [P] Add Celery beat schedule for automatic cleanup job running daily
- [ ] T124 Create OpenAPI schema generation using drf-spectacular in apps/api/v1/urls.py
- [ ] T125 [P] Add Swagger UI endpoint at /api/v1/docs/ for interactive API documentation
- [ ] T126 [P] Create API versioning strategy: /api/v1/, /api/v2/ with deprecation notices
- [ ] T127 Update documentation/ASYNC_FILE_PROCESSING_GOLD_STANDARD.md with lessons learned
- [ ] T128 [P] Update documentation/FRONTEND_IMPLEMENTATION_GUIDE.md with two-column layout pattern
- [ ] T129 [P] Create documentation/PLUGIN_DEVELOPMENT_GUIDE.md consolidating quickstart.md content
- [ ] T130 Update README.md with feature overview, architecture diagram, getting started instructions
- [ ] T131 Run full test suite: pytest --cov=apps/tools --cov-report=html --cov-fail-under=80
- [ ] T132 [P] Run Black formatter on entire codebase: black apps/ function_app/ tests/
- [ ] T133 [P] Run isort on imports: isort apps/ function_app/ tests/
- [ ] T134 [P] Run pylint: pylint apps/tools/ --fail-under=8.0
- [ ] T135 Verify all migrations are up-to-date: python manage.py makemigrations --check --dry-run
- [ ] T136 Run security audit: bandit -r apps/ -ll
- [ ] T137 [P] Review all environment variables against .env.example completeness
- [ ] T138 Validate Bicep templates: az bicep build --file infra/bicep/*.bicep
- [ ] T139 [P] Create GitHub Actions workflow .github/workflows/ci.yml: lint, test, build on PR
- [ ] T140 [P] Create GitHub Actions workflow .github/workflows/cd.yml: deploy to staging on main merge
- [ ] T141 Run quickstart.md validation: Follow guide to create test tool, verify all steps work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational (Phase 2) completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - Builds on US1 foundation but independently testable
  - User Story 3 (P3): Can start after Foundational - Enhances US1 and US2 but independently testable
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Sync Tools**: Foundation only → Independently testable via sync tool creation
- **User Story 2 (P2) - Async Tools**: Foundation + leverages BaseTool/Registry from US1 → Independently testable via async tool creation
- **User Story 3 (P3) - Consistent UX**: Foundation + applies to tools from US1/US2 → Independently testable via UI navigation

### Within Each User Story

1. **Tests FIRST** (TDD): Write tests, verify they fail
2. **Models/Services**: Core infrastructure for the story
3. **Views/Endpoints**: Business logic and API
4. **Templates/Frontend**: User interface
5. **Integration**: Wire everything together
6. **Validation**: Story complete, independently testable

### Parallel Opportunities

**Phase 1 (Setup)**: T002-T009 can all run in parallel - different files, no dependencies

**Phase 2 (Foundational)**: Several parallel groups:
- Group A: T010, T011, T012, T015, T016, T017 (different Python files)
- Group B: T018, T019, T022, T023, T024 (different config/template files)
- Sequential: T013→T014 (model→migration)

**Phase 3 (User Story 1)**: 
- Tests: T025-T030 all parallel
- Models: T031-T034 parallel (different methods in same file - low conflict)
- Registry: T035-T039 parallel (different methods)
- Views: T040-T042 parallel (different view classes)
- Frontend: T044, T045, T049 parallel (different templates)
- Logging/Docs: T046, T047, T050, T051 parallel

**Phase 4 (User Story 2)**:
- Tests: T052-T058 all parallel
- Services: T059-T063 parallel (BlobStorageClient methods), T064-T065 parallel (AsyncTaskTrigger)
- Views: T066-T069 parallel (different view classes)
- Frontend: T073, T074, T075, T076 parallel (different JS/template files)
- Azure Functions: T079-T086 parallel (different function handlers)
- Docs/Infra: T087, T088, T089 parallel

**Phase 5 (User Story 3)**:
- Tests: T090-T093 all parallel
- Templates: T094-T096 parallel (different include files)
- CSS/Assets: T101, T102, T104, T105 parallel
- Testing: T106, T107, T112, T113 parallel (different concerns)

**Phase 6 (Polish)**: Most tasks parallel except T131 (test suite must wait for code completion)

### Critical Path (Minimum Time to MVP - User Story 1 Only)

1. Phase 1 Setup: 1-2 hours (parallelized)
2. Phase 2 Foundational: 4-6 hours (T010→T013→T014 sequential, others parallel)
3. Phase 3 User Story 1: 6-8 hours (T025-T030 → T031-T051 with parallel execution)
4. **Total MVP Time: 11-16 hours** with 2-3 developers working in parallel

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch tests in parallel:
Developer A: T025 (unit test base_tool validation)
Developer B: T026 (unit test base_tool process)
Developer C: T027 (unit test registry register)
Developer D: T028 (unit test registry get_tool)
Developer E: T029 (integration test API)
Developer F: T030 (integration test web UI)

# Once tests written and failing, launch implementation in parallel:
Developer A: T031-T034 (BaseTool methods)
Developer B: T035-T039 (ToolRegistry methods)
Developer C: T040-T042 (Views)
Developer D: T043 (URL patterns)
Developer E: T044-T045 (Generic templates)
Developer F: T046-T048 (Validation + example tool)
```

---

## Parallel Example: User Story 2

```bash
# After User Story 1 completes (or concurrently if separate team):
Developer A: T052-T054 (BlobStorage tests)
Developer B: T055-T057 (Execution tests)
Developer C: T059-T063 (BlobStorageClient implementation)
Developer D: T064-T065 (AsyncTaskTrigger implementation)
Developer E: T066-T069 (Execution views)
Developer F: T073-T076 (Frontend polling/history)
Developer G: T079-T086 (Azure Function handlers)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only) - Fastest Path to Value

1. **Week 1**: Complete Phase 1 (Setup) + Phase 2 (Foundational)
2. **Week 2**: Complete Phase 3 (User Story 1 - Sync Tools)
3. **STOP and VALIDATE**: Create 3 example sync tools (Base64 encoder, hash generator, JSON formatter)
4. **DEMO**: Show tool discovery, tool execution, consistent UI
5. **Decision Point**: Deploy MVP or continue to async tools?

### Incremental Delivery (All User Stories)

1. **Weeks 1-2**: Setup + Foundational → Foundation ready
2. **Weeks 3-4**: User Story 1 (Sync Tools) → Test independently → Deploy (MVP!)
3. **Weeks 5-7**: User Story 2 (Async Tools) → Test independently → Deploy
4. **Weeks 8-9**: User Story 3 (Consistent UX) → Test independently → Deploy
5. **Week 10**: Polish phase → Final deployment

### Parallel Team Strategy (3+ Developers)

With 3 developers after Foundational phase:

1. **Developer A**: User Story 1 (Sync Tools) - 2 weeks
2. **Developer B**: User Story 2 (Async Tools) - 3 weeks
3. **Developer C**: User Story 3 (Consistent UX) - 2 weeks (starts after A finishes)

**Result**: All stories complete in ~3 weeks (vs 6 weeks sequential)

---

## Notes

- **[P] tasks** = Different files, no dependencies, safe to parallelize
- **[Story] label** = Maps task to specific user story for traceability and independent testing
- **TDD Workflow**: Tests MUST be written first, fail, then implement to make them pass
- Each user story should be independently completable and testable
- Stop at any checkpoint to validate story independently before proceeding
- Constitution compliance verified: Type hints (Principle I), TDD (Principle II), Bootstrap 5 + accessibility (Principle III), async pattern + caching (Principle IV), validation + Key Vault (Principle V)
- **Total Task Count**: 141 tasks organized across 6 phases
- **Estimated Effort**: 8-12 weeks with 1 developer, 3-4 weeks with 3 developers (parallelized)
- **MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1) = ~40 tasks, 2 weeks for experienced developer
