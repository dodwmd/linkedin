import os
import sys

# Add the linkedin_scraper directory to the Python path
linkedin_scraper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'linkedin_scraper'))
sys.path.insert(0, linkedin_scraper_path)

# Add the src directory to the Python path (assuming shared_data.py is there)
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, src_path)


from linkedin_scraper import Person, actions
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up the Chrome options
chrome_options = Options()
# Uncomment the next line if you want to run Chrome in headless mode
# chrome_options.add_argument("--headless")

# Set up the Chrome service with automatic ChromeDriver installation
service = Service(ChromeDriverManager().install())

# Set up the webdriver
driver = webdriver.Chrome(service=service, options=chrome_options)

# Get LinkedIn credentials from environment variables
email = os.getenv("LINKEDIN_EMAIL")
password = os.getenv("LINKEDIN_PASSWORD")

# Login to LinkedIn
actions.login(driver, email, password)

# Get the initial profile URL from environment variables
initial_profile_url = os.getenv("INITIAL_PROFILE_URL")

# Scrape the person's profile
person = Person(initial_profile_url, driver=driver)

# Print some information about the person
print(f"Name: {person.name}")
print(f"About: {person.about}")
print(f"Experience: {person.experiences}")
print(f"Education: {person.educations}")

# Close the browser
driver.quit()
