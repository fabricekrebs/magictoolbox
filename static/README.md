# MagicToolbox Static Assets

This directory contains static assets for the MagicToolbox application.

## Structure

- `css/`
  - `custom.css` - Custom styles with hover effects, animations, transitions
- `js/`
  - `main.js` - Utility functions:
    - `formatFileSize()` - Human-readable file sizes
    - `showNotification()` - Toast notifications
    - Auto-hide alerts
    - Loading button states
    - File validation
    - Debounce utility
- `images/` - Images and icons (currently empty)

## Development

In development, static files are served directly by Django.

## Production

In production:
1. Run `python manage.py collectstatic` to collect all static files
2. Serve static files via web server (Nginx/Apache) or CDN
3. Set `STATIC_ROOT` in settings to the collection directory
