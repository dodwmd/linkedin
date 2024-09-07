from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from linkedin_scraper import actions
import pickle
import os


class LinkedInSession:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.driver = None
        self.cookies_file = 'linkedin_cookies.pkl'

    def _setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )

        service = Service(executable_path="/usr/bin/chromedriver")

        return webdriver.Chrome(service=service, options=chrome_options)

    def login(self):
        if os.path.exists(self.cookies_file):
            self.driver = self._setup_driver()
            self.driver.get("https://www.linkedin.com")
            cookies = pickle.load(open(self.cookies_file, "rb"))
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            self.driver.refresh()
        else:
            self.driver = self._setup_driver()
            actions.login(self.driver, self.email, self.password)
            pickle.dump(
                self.driver.get_cookies(),
                open(self.cookies_file, "wb")
            )

    def get_driver(self):
        if not self.driver:
            self.login()
        return self.driver

    def close(self):
        if self.driver:
            self.driver.quit()
