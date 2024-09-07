FROM python:3.12

WORKDIR /app

# Set Chrome and ChromeDriver version
ENV CHROMEDRIVER_VERSION=128.0.6613.119

# Install dependencies for Chrome
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

# Set PATH to include Chrome and ChromeDriver
ENV PATH="/opt/chrome-linux64:/opt/chromedriver-linux64:${PATH}"

# Verify Chrome and ChromeDriver installation
RUN chrome --version && chromedriver --version

# Set display port to avoid crash
ENV DISPLAY=:99

# Copy the local linkedin_scraper package
COPY linkedin_scraper /app/linkedin_scraper

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the local linkedin_scraper package
RUN pip install -e /app/linkedin_scraper

# Copy the rest of the application code
COPY src /app/src
COPY linkedin_scraper /app/linkedin_scraper

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the working directory
WORKDIR /app/src

# Update the CMD to use python directly
CMD ["python", "/app/src/app.py"]

# Debugging: List contents of important directories
RUN ls -la /opt/chrome-linux64 && \
    ls -la /opt/chromedriver-linux64 && \
    ls -la /usr/bin | grep chrome

# Expose port 8080 for the web app
EXPOSE 8080