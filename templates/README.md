# MagicToolbox Templates

This directory contains Django templates for the MagicToolbox application.

## Structure

- `base.html` - Base template with Bootstrap 5 layout, JSZip for bulk downloads
- `home.html` - Homepage with hero section and tool showcase
- `includes/` - Reusable template fragments (navbar, footer, messages)
- `tools/` - Tool-specific templates
  - `tool_list.html` - Browse all tools
  - `tool_detail.html` - Generic tool interface
  - `image_format_converter.html` - Image converter (15+ formats, bulk)
  - `gpx_kml_converter.html` - GPS file converter (bidirectional, bulk)
  - `gpx_speed_modifier.html` - GPX track analyzer and speed modifier (bulk)
- `authentication/` - Authentication templates (login, register, profile)
- `errors/` - Error page templates (404, 500)

## Template Inheritance

All templates extend `base.html` which provides:
- Bootstrap 5 CSS and JS
- Bootstrap Icons
- Custom CSS from `static/css/custom.css`
- Custom JS from `static/js/main.js`
- Common layout structure (navbar, main content, footer)

## Blocks

Available blocks for child templates:
- `title` - Page title
- `meta_description` - Meta description for SEO
- `extra_css` - Additional CSS files
- `content` - Main page content
- `extra_js` - Additional JavaScript files

## Django Crispy Forms

Forms use django-crispy-forms with Bootstrap 5 styling for consistent form rendering.

## Tool Template Patterns

All tool templates follow a standardized structure:
- File upload with multiple file support (`name="files[]" multiple`)
- Progress bar with percentage tracking
- Single file result section
- Bulk result section with table and ZIP download
- Sidebar with supported formats and features
- Consistent JavaScript patterns (handleSingleConversion, handleBulkConversion)

See `.github/copilot-tool-development-instructions.md` for complete guidelines.
