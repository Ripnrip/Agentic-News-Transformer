FROM python:3.12-slim

WORKDIR /app

# Install system dependencies and Playwright requirements
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    # Additional Playwright dependencies
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install basic requirements
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install pydantic and its dependencies first
RUN pip install --no-cache-dir \
    pydantic==2.11.2 \
    pydantic-core==2.33.1 \
    typing-extensions>=4.6.1 \
    annotated-types>=0.4.0

# Install pydantic-ai and related packages
RUN pip install --no-cache-dir \
    pydantic-ai==0.0.52 \
    pydantic-ai-slim==0.0.52 \
    pydantic-evals==0.0.52 \
    pydantic-graph==0.0.52

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN playwright install --with-deps chromium
RUN playwright install-deps

# Copy the rest of the application
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 appuser
RUN chown -R appuser:appuser /app
USER appuser

# Set up virtual display for Playwright
ENV DISPLAY=:99
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Expose the Streamlit port
EXPOSE 8501

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Start Xvfb and run the application
CMD Xvfb :99 -screen 0 1024x768x16 & streamlit run app.py --server.port=8501 --server.address=0.0.0.0 