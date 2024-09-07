# Use an official Python runtime as a parent image
FROM python:3.12

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CHROMEDRIVER_VERSION=128.0.6613.119 \
    DISPLAY=:99

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libglib2.0-0 \
    libasound2 \
    libxrender1 \
    libxrandr2 \
    libxtst6 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libgbm1 \
    libjpeg62-turbo \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxss1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Testing
RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chrome-linux64.zip \
    && unzip chrome-linux64.zip -d /opt/ \
    && ln -s /opt/chrome-linux64/chrome /usr/bin/chrome \
    && rm chrome-linux64.zip

# Install ChromeDriver
RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip \
    && unzip chromedriver-linux64.zip -d /opt/ \
    && ln -s /opt/chromedriver-linux64/chromedriver /usr/bin/chromedriver \
    && rm chromedriver-linux64.zip \
    && chmod +x /usr/bin/chromedriver

# Set PATH to include Chrome, ChromeDriver, and pip install bin directory
ENV PATH="/opt/chrome-linux64:/root/.local/bin:${PATH}"

# Verify Chrome and ChromeDriver installation
RUN chrome --version && chromedriver --version

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the local linkedin_scraper package
COPY linkedin_scraper /app/linkedin_scraper

# Install the local linkedin_scraper package
RUN pip install -e /app/linkedin_scraper

# Expose port 8080 for the web app
EXPOSE 8080

# Copy the rest of the application code
COPY src /app/src

# Set the working directory to /app/src
WORKDIR /app/src

# Update the CMD to use Gunicorn with eventlet worker
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:8080", "wsgi:app"]

