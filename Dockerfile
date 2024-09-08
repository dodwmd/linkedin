# Use an official Python runtime as a parent image
FROM python:3.12

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DISPLAY=:99

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    jq \
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
    fonts-liberation \
    libu2f-udev \
    libvulkan1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -qO /tmp/chrome-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/`wget -qO- https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.version'`/linux64/chrome-linux64.zip \
    && unzip /tmp/chrome-linux64.zip -d /opt/ \
    && ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome \
    && rm /tmp/chrome-linux64.zip

# Install ChromeDriver
RUN wget -qO /tmp/chromedriver-linux64.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/`wget -qO- https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.version'`/linux64/chromedriver-linux64.zip \
    && unzip -j /tmp/chromedriver-linux64.zip chromedriver-linux64/chromedriver -d /usr/bin/

# Set PATH to include ChromeDriver
ENV PATH="/usr/bin:${PATH}"

# Verify Chrome and ChromeDriver installation
RUN google-chrome --version && chromedriver --version

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the local linkedin_scraper package
COPY linkedin_scraper /app/linkedin_scraper

# Install the local linkedin_scraper package
RUN pip install -e /app/linkedin_scraper

# Expose ports for the web app and remote debugging
EXPOSE 8080 9222

# Copy the rest of the application code
COPY src /app/src

# Set the working directory to /app/src
WORKDIR /app/src

# Create a non-root user
RUN useradd -m myuser
USER myuser

# Update the CMD to use Gunicorn with eventlet worker
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:8080", "wsgi:app"]

