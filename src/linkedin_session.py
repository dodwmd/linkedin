import os
import sys  # Add this import
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from shared_data import log
import selenium  # Add this import
import webdriver_manager  # Add this import
import requests  # Add this import
import json  # Add this import
from linkedin_scraper import actions
from webdriver_manager.chrome import ChromeDriverManager  # Add this import

class LinkedInSession:


    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.driver = None
        self.actions = None
        log(f"LinkedInSession initialized with email: {email}")


    def start(self):
        chrome_options = Options()
        chrome_options.add_argument("--verbose")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless=new")  # Use the new headless mode
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        
        log("Chrome options set")
        
        try:
            log("Attempting to start Chrome WebDriver")
            chrome_version = self.get_chrome_version()
            log(f"Detected Chrome version: {chrome_version}")
            
            # Get the latest ChromeDriver version
            latest_version, download_url = self.get_latest_chromedriver_info()
            log(f"Latest ChromeDriver version: {latest_version}")
            log(f"ChromeDriver download URL: {download_url}")
            
            # Download and install ChromeDriver
            chromedriver_path = self.download_chromedriver(download_url)
            log(f"ChromeDriver installed at: {chromedriver_path}")
            
            service = Service(chromedriver_path)
            log(f"ChromeDriver service created")
            
            # Add more debug information
            log(f"Chrome binary location: {chrome_options.binary_location}")
            log(f"Current working directory: {os.getcwd()}")
            log(f"PATH environment variable: {os.environ.get('PATH', 'Not set')}")
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            log("Chrome WebDriver started successfully")

            self.login()
        except Exception as e:
            log(f"Error starting Chrome WebDriver: {str(e)}", "error")
            self.log_system_info()
            raise

    def login(self):
        try:
            # Use the login method from linkedin_scraper
            actions.login(self.driver, self.email, self.password)
            log("Successfully logged in to LinkedIn")
        except Exception as e:
            log(f"Error during LinkedIn login: {str(e)}", "error")
            raise


    def get_driver(self):
        return self.driver


    def close(self):
        if self.driver:
            self.driver.quit()
            log("LinkedIn session closed")

    def get_chrome_version(self):
        try:
            chrome_path = "/usr/bin/google-chrome"
            result = subprocess.run([chrome_path, "--version"], capture_output=True, text=True)
            version = result.stdout.strip().split()[-1]  # Get the version number
            return version
        except Exception as e:
            return f"Error getting Chrome version: {str(e)}"

    def get_latest_chromedriver_info(self):
        url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
        response = requests.get(url)
        data = json.loads(response.text)
        latest_version = data['channels']['Stable']['version']
        download_url = next(item['url'] for item in data['channels']['Stable']['downloads']['chromedriver'] if item['platform'] == 'linux64')
        return latest_version, download_url

    def download_chromedriver(self, url):
        local_filename = '/tmp/chromedriver.zip'
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        
        # Unzip the file
        import zipfile
        with zipfile.ZipFile(local_filename, 'r') as zip_ref:
            zip_ref.extractall('/tmp')
        
        # Make the ChromeDriver executable
        chromedriver_path = '/tmp/chromedriver-linux64/chromedriver'
        os.chmod(chromedriver_path, 0o755)
        return chromedriver_path

    def log_system_info(self):
        log("System Information:")
        log(f"Operating System: {os.name}")
        log(f"Python version: {sys.version}")
        log(f"Selenium version: {webdriver.__version__}")
        log(f"Contents of /usr/bin: {os.listdir('/usr/bin')}")
        
        # Check if Chrome is installed and executable
        chrome_path = "/usr/bin/google-chrome"
        if os.path.exists(chrome_path):
            log(f"Chrome exists at {chrome_path}")
            if os.access(chrome_path, os.X_OK):
                log("Chrome is executable")
            else:
                log("Chrome is not executable")
        else:
            log("Chrome not found at /usr/bin/google-chrome")

        # Check ChromeDriver
        chromedriver_path = '/tmp/chromedriver-linux64/chromedriver'  # Use the path where you install ChromeDriver
        if os.path.exists(chromedriver_path):
            log(f"ChromeDriver exists at {chromedriver_path}")
            if os.access(chromedriver_path, os.X_OK):
                log("ChromeDriver is executable")
            else:
                log("ChromeDriver is not executable")
        else:
            log("ChromeDriver not found")
