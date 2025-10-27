# Use official Playwright Python image (includes Chromium)
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (already in image, but ensure)
RUN playwright install chromium

# Copy application code
COPY . .

# Create data directory for cache/user data
RUN mkdir -p /app/data/cache /app/data/user /app/data/reference

# Expose port (Render provides $PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health', timeout=5)"

# Start application
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
