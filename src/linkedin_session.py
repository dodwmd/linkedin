from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from shared_data import log


class LinkedInSession:


    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.driver = None
        log(f"LinkedInSession initialized with email: {email}")


    def start(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.login()


    def login(self):
        try:
            self.driver.get("https://www.linkedin.com/login")
            
            # Wait for the username field to be visible
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_field.send_keys(self.email)
            
            # Find and fill the password field
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.password)
            
            # Click the login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, ".btn__primary--large")
            login_button.click()
            
            # Wait for the login to complete (you might need to adjust this based on LinkedIn's behavior)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "global-nav"))
            )
            
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
