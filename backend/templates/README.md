# MagicToolbox Templates

This directory contains Django templates for the MagicToolbox application.

## Structure

- `base.html` - Base template with Bootstrap 5 layout
- `home.html` - Homepage
- `includes/` - Reusable template fragments (navbar, footer, messages)
- `tools/` - Tool-specific templates
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
