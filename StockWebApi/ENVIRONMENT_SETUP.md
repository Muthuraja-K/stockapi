# Environment Variables Setup

This document explains how to configure environment variables for the Stock Prediction API.

## Required Environment Variables

### 1. Finviz API Authentication
- **Variable**: `FINVIZ_AUTH_ID`
- **Description**: Your Finviz Elite API authentication token
- **Required**: Yes
- **Default**: `22a5d2df-8313-42f4-b2ab-cab5e0f26758` (fallback value)

## Setup Instructions

### Option 1: Create a .env file (Recommended for development)

1. Create a `.env` file in the `StockWebApi` directory
2. Add your environment variables:

```bash
# Finviz API Configuration
FINVIZ_AUTH_ID=your_actual_finviz_auth_id_here

# Optional: API Configuration
ALLOWED_ORIGINS=http://localhost:4200,http://localhost:3000

# Optional: Logging Configuration
LOG_LEVEL=INFO

# Optional: Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

### Option 2: Set system environment variables

#### Windows (PowerShell):
```powershell
$env:FINVIZ_AUTH_ID="your_actual_finviz_auth_id_here"
```

#### Windows (Command Prompt):
```cmd
set FINVIZ_AUTH_ID=your_actual_finviz_auth_id_here
```

#### Linux/Mac:
```bash
export FINVIZ_AUTH_ID="your_actual_finviz_auth_id_here"
```

## Security Notes

- **Never commit your actual `.env` file** to version control
- The `.env.example` file is provided as a template
- The application will fall back to default values if environment variables are not set
- For production, use proper environment variable management (e.g., Docker secrets, Kubernetes secrets)

## Configuration File

The application uses a centralized configuration system in `config.py` that:
- Loads environment variables from `.env` files
- Provides default values for missing variables
- Validates required configuration values
- Centralizes all configuration management

## Testing Configuration

To test if your environment variables are loaded correctly:

1. Start the application
2. Check the logs for any configuration validation errors
3. The Finviz API calls should use your configured auth_id

## Troubleshooting

If you encounter issues:

1. **Check if python-dotenv is installed**: `pip install python-dotenv`
2. **Verify .env file location**: Should be in the same directory as `main.py`
3. **Check file permissions**: Ensure the .env file is readable
4. **Restart the application**: Environment variables are loaded at startup
