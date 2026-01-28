# Dockerfile for Luminate Cookbook FastAPI App
# Supports Playwright browser automation on Google Cloud Run

# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=8000

# Install system dependencies required for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core system libraries
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libc6 \
    libcairo2 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    lsb-release \
    wget \
    xdg-utils \
    # Netscape/Network Security libraries
    libnspr4 \
    libnss3 \
    # Accessibility libraries
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    # Printing/IPC libraries
    libcups2 \
    libdbus-1-3 \
    # Graphics libraries
    libdrm2 \
    libgbm1 \
    # GTK+ library
    libgtk-3-0 \
    # Keyboard library
    libxkbcommon0 \
    # X11 libraries
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    # Audio library
    libasound2 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements file first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium)
RUN python -m playwright install chromium

# Install Playwright system dependencies for Chromium
RUN python -m playwright install-deps chromium || true

# Copy application files
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; r = requests.get('http://localhost:8000/health', timeout=5); exit(0 if r.status_code == 200 else 1)" || exit 1

# Run FastAPI app with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
