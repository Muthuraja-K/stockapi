# Static Files Directory

This directory contains the frontend build files that are served by the FastAPI backend.

## Current Contents

- `index.html` - Main landing page for the Stock Prediction API
- `README.md` - This file

## Purpose

The static folder serves as the web root for the frontend application. In production, this would typically contain:

1. **Built Angular Application** - After running `ng build` in the StockUI directory
2. **Static Assets** - CSS, JavaScript, images, and other static files
3. **Index File** - The main HTML file that loads the Angular application

## How It Works

1. **FastAPI StaticFiles Mount**: The `/static` endpoint serves files from this directory
2. **Root Route**: The `/` endpoint serves `index.html` directly
3. **API Endpoints**: All `/api/*` endpoints are handled by the FastAPI backend

## Development Workflow

1. **Frontend Development**: Work in the `StockUI/` directory
2. **Build Frontend**: Run `ng build --output-path ../StockWebApi/static` from StockUI
3. **Serve**: The FastAPI backend will serve the built frontend files

## File Structure (Production)

```
static/
├── index.html          # Main application entry point
├── assets/             # Built Angular assets
│   ├── css/           # Compiled CSS files
│   ├── js/            # Compiled JavaScript files
│   └── images/        # Static images
├── favicon.ico         # Browser favicon
└── README.md           # This file
```

## Notes

- The current `index.html` is a placeholder page
- In production, replace this with the actual built Angular application
- Ensure all static assets are properly referenced with relative paths
