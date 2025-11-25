# MagicToolbox Static Assets

This directory contains static assets for the MagicToolbox application.

## Structure

- `css/` - Custom CSS styles
- `js/` - Custom JavaScript files
- `images/` - Images and icons

## Development

In development, static files are served directly by Django.

## Production

In production, run `python manage.py collectstatic` to collect all static files into the `staticfiles/` directory for serving by a web server or CDN.
